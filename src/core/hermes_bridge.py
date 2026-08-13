"""
Hermes Agent WhatsApp bridge — zero-ichi as the gateway transport.

Serves the same HTTP contract as Hermes' Node.js Baileys bridge
(``scripts/whatsapp-bridge/bridge.js``) so the *already-connected* neonize
client in zero-ichi can act as the WhatsApp transport for the Hermes gateway.
No second WhatsApp session, no QR scan, no Node.js bridge — the running
zero-ichi bot *is* the WhatsApp connection.

How the reuse trick works
-------------------------
Hermes' WhatsApp plugin adapter (``plugins/platforms/whatsapp/adapter.py``)
health-checks ``127.0.0.1:PORT/health`` before spawning its own Node bridge.
If a bridge is already listening, reports ``status: "connected"``, and its
``scriptHash`` matches the SHA-256 of the on-disk ``bridge.js``, the adapter
reuses it and never spawns Node. This module therefore:

* binds loopback-only on a configurable port (default 3000, same default the
  adapter uses);
* reports ``scriptHash`` computed *fresh on every health check* from the
  current on-disk ``bridge.js``, so a ``hermes update`` that changes the hash
  is picked up without a restart;
* reports ``sendReadReceipts: false`` (the adapter default) so the
  ``config_matches`` half of the reuse handshake passes.

Caveat: if this bridge is *not* reachable while the Hermes gateway starts
(e.g. zero-ichi down at boot), the adapter falls back to spawning its own
Node.js bridge, which would require its own QR pairing. Keep zero-ichi
running before (re)starting the gateway, or restart the gateway once
zero-ichi is back up.

Endpoints (mirror bridge.js):
  GET  /health          {status, queueLength, uptime, scriptHash, sendReadReceipts}
  GET  /messages        drain inbound event queue
  POST /send            {chatId, message, replyTo?}
  POST /edit            {chatId, messageId, message}
  POST /send-media      {chatId, filePath, mediaType?, caption?, fileName?}
  POST /send-poll       {chatId, question, options, selectableCount?}
  POST /send-location   {chatId, latitude, longitude, name?, address?}
  POST /typing          {chatId}
  POST /read            {key: {remoteJid, id, participant}}
  GET  /chat/:id        {name, isGroup, participants}
  GET  /media/:token    inbound media bytes (referenced from event mediaUrls)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, TYPE_CHECKING

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from google.protobuf.json_format import MessageToDict
from neonize.utils.enum import ChatPresence, ChatPresenceMedia, ReceiptType

from core.logger import log_error, log_info, log_warning
from core.session import session_state

if TYPE_CHECKING:
    from core.client import BotClient

logger = logging.getLogger(__name__)

_MAX_QUEUE_SIZE = 512

_MEDIA_EXT_MAP = {
    "image": ".jpg",
    "video": ".mp4",
    "gif": ".mp4",
    "audio": ".ogg",
    "ptt": ".ogg",
    "document": ".bin",
    "sticker": ".webp",
}

_MIME_EXT_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/x-matroska": ".mkv",
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "application/pdf": ".pdf",
}


def _normalize_jid(value: str) -> str:
    """Normalize a JID string the way bridge.js normalizeWhatsAppId does."""
    if not value:
        return ""
    return str(value).replace(":", "@")


def _script_hash() -> str:
    """First 16 hex chars of SHA-256 of the on-disk Hermes bridge.js.

    The WhatsApp adapter compares this against the hash of the bridge.js it
    would spawn; matching means "this running bridge is current" and it is
    reused instead of spawning Node. Recompute on every call so a `hermes
    update` that swaps bridge.js is reflected without a bridge restart.
    """
    candidates = [
        Path.home() / ".hermes" / "hermes-agent" / "scripts" / "whatsapp-bridge" / "bridge.js",
        Path.home() / ".hermes" / "scripts" / "whatsapp-bridge" / "bridge.js",
    ]
    hermes_home = Path.home() / ".hermes"
    for candidate in candidates:
        if candidate.is_file():
            try:
                return hashlib.sha256(candidate.read_bytes()).hexdigest()[:16]
            except OSError:
                continue
    # No bridge.js on disk — report a stable placeholder. The adapter will
    # treat us as stale and fall back to spawning its own Node bridge.
    log_warning(
        f"Hermes bridge.js not found under {hermes_home}/…; scriptHash handshake will fail."
    )
    return "0000000000000000"


def _hermes_creds_path() -> Path:
    """Path to the creds.json the Hermes WhatsApp adapter gates on.

    The adapter refuses to connect — "WhatsApp enabled but not paired" —
    unless ``<hermes>/platforms/whatsapp/session/creds.json`` exists, and it
    performs that check BEFORE the /health reuse handshake. Honoring
    ``$HERMES_HOME`` keeps profile installs working.
    """
    base = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
    return base / "platforms" / "whatsapp" / "session" / "creds.json"


def _ensure_hermes_creds_stub() -> None:
    """Create a placeholder creds.json so the Hermes adapter reaches our bridge.

    We never run Hermes' own Node bridge, so this file is never used for
    authentication — the live WhatsApp session lives in the neonize client.
    The adapter only needs the file to *exist* to pass its "not paired"
    pre-flight, after which the /health handshake reuses our bridge. Without
    it, every gateway boot dies with "WhatsApp enabled but not paired" before
    the reuse handshake is even attempted. Safe to run on every start: only
    writes when missing, and never overwrites a real paired session.
    """
    try:
        creds_path = _hermes_creds_path()
        if creds_path.exists():
            return
        creds_path.parent.mkdir(parents=True, exist_ok=True)
        creds_path.write_text(
            json.dumps(
                {
                    "registered": False,
                    "_note": "stub written by zero-ichi hermes_bridge: the live "
                    "WhatsApp session lives in the zero-ichi neonize client, "
                    "not here. Hermes reuses zero-ichi as its bridge "
                    "(see /health handshake).",
                }
            ),
            encoding="utf-8",
        )
        log_info(f"Hermes bridge: wrote creds.json stub at {creds_path}")
    except Exception as exc:
        log_warning(f"Hermes bridge: could not write creds.json stub: {exc}")


def _quoted_text(raw: dict) -> str:
    """Extract a readable text snippet from a quotedMessage dict."""
    quoted = raw.get("quotedMessage") or {}
    for key in ("conversation", "text"):
        val = quoted.get(key)
        if val:
            return str(val)
    for container in ("extendedTextMessage", "imageMessage", "videoMessage", "documentMessage"):
        sub = quoted.get(container)
        if isinstance(sub, dict):
            for key in ("text", "caption", "fileName"):
                val = sub.get(key)
                if val:
                    return str(val)
    return ""


class HermesBridge:
    """Expose a running zero-ichi neonize client as a Hermes WhatsApp bridge."""

    def __init__(self, bot: "BotClient", port: int = 3000, host: str = "127.0.0.1") -> None:
        self.bot = bot
        self.port = int(port)
        self.host = host
        self._queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
        self._media_dir = Path("data") / "hermes_bridge" / "media"
        self._media_dir.mkdir(parents=True, exist_ok=True)
        self._started_at = time.time()
        self._server_task: asyncio.Task | None = None
        # Hermes' adapter gates on creds.json existing before the reuse
        # handshake; make sure the stub is in place before we advertise /health.
        _ensure_hermes_creds_stub()
        self._app = self._build_app()

    # ------------------------------------------------------------------ #
    # Inbound                                                             #
    # ------------------------------------------------------------------ #
    def push_message(self, msg, event) -> None:
        """Enqueue a (MessageHelper, MessageEv) pair for async event building."""
        try:
            self._queue.put_nowait((msg, event))
        except asyncio.QueueFull:
            log_warning("Hermes bridge: inbound queue full, dropping message")
            try:
                self._queue.get_nowait()
                self._queue.put_nowait((msg, event))
            except Exception:
                pass

    async def _event_worker(self) -> None:
        """Background task: build bridge events (incl. media downloads)."""
        while True:
            msg, event = await self._queue.get()
            try:
                built = await self._build_event(msg, event)
                if built:
                    await self._emit(built)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log_error(f"Hermes bridge: event build failed: {exc}")

    async def _emit(self, event: dict) -> None:
        """Queue a fully-built event dict for the gateway to poll."""
        if self._gateway_queue.qsize() >= _MAX_QUEUE_SIZE:
            try:
                self._gateway_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        await self._gateway_queue.put(event)

    async def _build_event(self, msg, event) -> dict | None:
        """Transform a neonize message into the bridge.js event contract."""
        chat_jid = msg.chat_jid
        sender_jid = msg.sender_jid
        is_group = msg.is_group
        sender_number = msg.sender_number
        sender_name = msg.sender_name or sender_number

        try:
            raw = MessageToDict(event.Message)
        except Exception:
            raw = {}

        body = msg.text or ""

        # ---- media detection ---------------------------------------- #
        has_media = False
        media_type = ""
        mime = ""
        file_name = ""
        native_type = ""
        native_metadata: dict[str, Any] = {}
        media_urls: list[str] = []

        media_map = [
            ("imageMessage", "image", "imageMessage"),
            ("videoMessage", "video", "videoMessage"),
            ("pttMessage", "ptt", "pttMessage"),
            ("audioMessage", "audio", "audioMessage"),
            ("documentMessage", "document", "documentMessage"),
            ("stickerMessage", "sticker", "stickerMessage"),
            ("locationMessage", "location", "locationMessage"),
            ("liveLocationMessage", "live_location", "liveLocationMessage"),
            ("contactMessage", "contact", "contactMessage"),
            ("reactionMessage", "reaction", "reactionMessage"),
            ("pollCreationMessage", "poll", "pollCreationMessage"),
            ("pollCreationMessageV2", "poll", "pollCreationMessageV2"),
            ("pollCreationMessageV3", "poll", "pollCreationMessageV3"),
            ("pollUpdateMessage", "poll_update", "pollUpdateMessage"),
        ]

        for field_name, mtype, native in media_map:
            item = raw.get(field_name)
            if not item:
                continue
            has_media = True
            media_type = mtype
            native_type = native
            mime = str(item.get("mimetype") or "")
            if mtype in ("image", "video"):
                body = body or str(item.get("caption") or "")
            if mtype == "video" and item.get("gifPlayback"):
                media_type = "gif"
            if mtype == "document":
                file_name = str(item.get("fileName") or "document")
                body = body or ""
            if mtype == "location":
                body = _location_text(item)
                native_metadata["location"] = item
            if mtype == "live_location":
                body = _location_text(item, live=True)
                native_metadata["location"] = {**item, "isLive": True}
            if mtype == "contact":
                body = f"[Contact: {item.get('displayName') or 'unknown'}]"
            if mtype == "reaction":
                body = f"[Reaction: {item.get('text') or ''}]"
            if mtype == "poll":
                options = [o.get("optionName") or o.get("name") for o in item.get("options", [])]
                options = [o for o in options if o]
                body = f"[Poll: {item.get('name') or item.get('title') or 'poll'} Options: {', '.join(options)}]"
                native_metadata["poll"] = {
                    "question": item.get("name") or item.get("title") or "",
                    "options": options,
                    "selectableCount": item.get("selectableOptionsCount") or 1,
                }
            break

        if has_media and media_type not in ("location", "live_location", "contact", "reaction", "poll", "poll_update"):
            token = uuid.uuid4().hex
            ext = _MIME_EXT_MAP.get(str(mime).split(";")[0].strip().lower(), "")
            if not ext:
                ext = _MEDIA_EXT_MAP.get(media_type, ".bin")
            path = self._media_dir / f"{token}{ext}"
            try:
                data = await self.bot._client.download_any(event.Message)
                if data:
                    path.write_bytes(data)
                    media_urls.append(f"http://{self.host}:{self.port}/media/{path.name}")
                else:
                    body = f"[{media_type} received] (download failed)" if not body else body
            except Exception as exc:
                log_warning(f"Hermes bridge: media download failed: {exc}")
                body = f"[{media_type} could not be downloaded]" if not body else body

        if has_media and not body:
            body = f"[{media_type} received]"

        # ---- context (mentions / quotes) ----------------------------- #
        context = _find_context_info(raw)
        mentioned_ids = [
            _normalize_jid(jid) for jid in _ctx_get(context, "mentionedJid", "mentionedJID", "mentionedJids") or []
            if jid
        ]
        quoted_message_id = _ctx_get(context, "stanzaId", "stanzaID") or None
        quoted_participant = _normalize_jid((context or {}).get("participant") or "") or None
        quoted_remote_jid = _normalize_jid(
            _ctx_get(context, "remoteJid", "remoteJID") or ""
        ) or None
        has_quoted = bool((context or {}).get("quotedMessage"))
        quoted_text = _quoted_text(context or {}) if has_quoted else ""

        return {
            "messageId": msg.message_id,
            "chatId": chat_jid,
            "senderId": sender_jid,
            "senderName": sender_name,
            "chatName": chat_jid.split("@")[0] if is_group else sender_name,
            "isGroup": is_group,
            "body": body,
            "hasMedia": has_media,
            "mediaType": media_type,
            "mime": mime,
            "fileName": file_name,
            "nativeType": native_type,
            "nativeMetadata": native_metadata,
            "mediaUrls": media_urls,
            "mentionedIds": mentioned_ids,
            "quotedMessageId": quoted_message_id,
            "quotedParticipant": quoted_participant,
            "quotedRemoteJid": quoted_remote_jid,
            "quotedText": quoted_text,
            "hasQuotedMessage": has_quoted,
            "botIds": [],
            "readReceiptKey": {
                "remoteJid": chat_jid,
                "id": msg.message_id,
                "participant": sender_jid,
                "fromMe": False,
            },
            "timestamp": msg.timestamp,
        }

    # ------------------------------------------------------------------ #
    # HTTP app                                                           #
    # ------------------------------------------------------------------ #
    def _build_app(self) -> FastAPI:
        app = FastAPI(title="zero-ichi hermes bridge", docs_url=None, redoc_url=None)

        @app.get("/health")
        async def health() -> dict:
            status = "connected" if session_state.is_logged_in else "connecting"
            return {
                "status": status,
                "queueLength": self._gateway_queue.qsize(),
                "uptime": round(time.time() - self._started_at, 1),
                "scriptHash": _script_hash(),
                "sendReadReceipts": False,
            }

        @app.get("/messages")
        async def messages() -> list[dict]:
            out: list[dict] = []
            while True:
                try:
                    out.append(self._gateway_queue.get_nowait())
                except asyncio.QueueEmpty:
                    break
            return out

        @app.post("/send")
        async def send(req: Request) -> JSONResponse:
            data = await req.json()
            chat_id = data.get("chatId")
            text = data.get("message")
            if not chat_id or not text:
                return JSONResponse({"error": "chatId and message are required"}, status_code=400)
            try:
                sent = await self.bot.send(chat_id, str(text))
                return JSONResponse(
                    {"success": True, "messageId": sent.ID, "messageIds": [sent.ID]}
                )
            except Exception as exc:
                return JSONResponse({"error": str(exc)}, status_code=500)

        @app.post("/edit")
        async def edit(req: Request) -> JSONResponse:
            data = await req.json()
            chat_id = data.get("chatId")
            message_id = data.get("messageId")
            text = data.get("message")
            if not chat_id or not message_id or not text:
                return JSONResponse({"error": "chatId, messageId and message are required"}, status_code=400)
            try:
                from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message

                new_msg = Message()
                new_msg.extendedTextMessage.text = str(text)
                await self.bot._client.edit_message(
                    self.bot.to_jid(chat_id), str(message_id), new_msg
                )
                return JSONResponse({"success": True})
            except Exception as exc:
                return JSONResponse({"error": str(exc)}, status_code=500)

        @app.post("/send-media")
        async def send_media(req: Request) -> JSONResponse:
            data = await req.json()
            chat_id = data.get("chatId")
            file_path = data.get("filePath")
            if not chat_id or not file_path:
                return JSONResponse({"error": "chatId and filePath are required"}, status_code=400)
            path = Path(file_path)
            if not path.is_file():
                return JSONResponse({"error": f"file not found: {file_path}"}, status_code=400)
            caption = str(data.get("caption") or "")
            file_name = str(data.get("fileName") or path.name)
            media_type = str(data.get("mediaType") or "").lower()
            try:
                payload = path.read_bytes()
                if media_type == "image":
                    sent = await self.bot.send_image(chat_id, payload, caption=caption)
                elif media_type == "video" or media_type == "gif":
                    sent = await self.bot.send_video(chat_id, payload, caption=caption)
                elif media_type == "ptt":
                    try:
                        sent = await self.bot.send_audio(chat_id, payload, ptt=True)
                    except Exception:
                        sent = await self.bot.send_audio(chat_id, payload)
                elif media_type == "audio":
                    sent = await self.bot.send_audio(chat_id, payload)
                elif media_type == "sticker":
                    sent = await self.bot.send_sticker(chat_id, payload)
                else:  # document / unknown
                    sent = await self.bot.send_document(
                        chat_id, payload, caption=caption, filename=file_name
                    )
                return JSONResponse({"success": True, "messageId": sent.ID})
            except Exception as exc:
                return JSONResponse({"error": str(exc)}, status_code=500)

        @app.post("/send-poll")
        async def send_poll(req: Request) -> JSONResponse:
            data = await req.json()
            chat_id = data.get("chatId")
            question = data.get("question")
            options = data.get("options")
            if not chat_id or not question or not isinstance(options, list):
                return JSONResponse({"error": "chatId, question, and options are required"}, status_code=400)
            try:
                sent = await self.bot.send_poll(chat_id, str(question), [str(o) for o in options])
                return JSONResponse({"success": True, "messageId": sent.ID})
            except Exception as exc:
                return JSONResponse({"error": str(exc)}, status_code=400)

        @app.post("/send-location")
        async def send_location(req: Request) -> JSONResponse:
            data = await req.json()
            chat_id = data.get("chatId")
            lat = data.get("latitude")
            lon = data.get("longitude")
            if not chat_id or lat is None or lon is None:
                return JSONResponse({"error": "chatId, latitude, and longitude are required"}, status_code=400)
            try:
                from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message

                msg = Message()
                msg.locationMessage.degreesLatitude = float(lat)
                msg.locationMessage.degreesLongitude = float(lon)
                if data.get("name"):
                    msg.locationMessage.name = str(data["name"])
                if data.get("address"):
                    msg.locationMessage.address = str(data["address"])
                sent = await self.bot._client.send_message(self.bot.to_jid(chat_id), msg)
                return JSONResponse({"success": True, "messageId": getattr(sent, "ID", None)})
            except Exception as exc:
                return JSONResponse({"error": str(exc)}, status_code=400)

        @app.post("/typing")
        async def typing(req: Request) -> JSONResponse:
            data = await req.json()
            chat_id = data.get("chatId")
            if not chat_id:
                return JSONResponse({"error": "chatId required"}, status_code=400)
            try:
                await self.bot._client.send_chat_presence(
                    self.bot.to_jid(chat_id),
                    ChatPresence.CHAT_PRESENCE_COMPOSING,
                    ChatPresenceMedia.CHAT_PRESENCE_MEDIA_TEXT,
                )
                return JSONResponse({"success": True})
            except Exception:
                return JSONResponse({"success": False})

        @app.post("/read")
        async def read(req: Request) -> JSONResponse:
            data = await req.json()
            key = (data or {}).get("key") or {}
            remote_jid = key.get("remoteJid") or ""
            message_id = key.get("id") or ""
            if not remote_jid or not message_id:
                return JSONResponse({"success": True, "marked": False})
            try:
                chat = self.bot.to_jid(remote_jid)
                await self.bot._client.mark_read(
                    str(message_id),
                    chat=chat,
                    sender=chat,
                    receipt=ReceiptType.READ,
                )
                return JSONResponse({"success": True, "marked": True})
            except Exception as exc:
                return JSONResponse({"error": str(exc)}, status_code=500)

        @app.get("/chat/{chat_id:path}")
        async def chat_info(chat_id: str) -> dict:
            is_group = chat_id.endswith("@g.us")
            return {
                "name": chat_id.split("@")[0],
                "isGroup": is_group,
                "participants": [],
            }

        @app.get("/media/{token}")
        async def media(token: str):
            path = self._media_dir / token
            if not path.is_file():
                raise HTTPException(status_code=404, detail="media not found")
            return FileResponse(path)

        return app

    @property
    def _gateway_queue(self) -> asyncio.Queue[dict]:
        """Queue the gateway drains via GET /messages (created lazily on loop)."""
        if not hasattr(self, "_built_events"):
            self._built_events = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
        return self._built_events

    # ------------------------------------------------------------------ #
    # Lifecycle                                                          #
    # ------------------------------------------------------------------ #
    async def start(self) -> None:
        """Start the HTTP server + event worker on the current event loop."""
        import uvicorn

        self._gateway_queue  # ensure queue exists on the running loop
        self._worker_task = asyncio.create_task(self._event_worker())
        config = uvicorn.Config(
            self._app, host=self.host, port=self.port, log_level="warning"
        )
        server = uvicorn.Server(config)
        self._server_task = asyncio.create_task(server.serve())
        log_info(f"Hermes bridge listening on http://{self.host}:{self.port}")

    async def stop(self) -> None:
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except (asyncio.CancelledError, Exception):
                pass
            self._server_task = None
        if getattr(self, "_worker_task", None):
            self._worker_task.cancel()
            try:
                await self._worker_task
            except (asyncio.CancelledError, Exception):
                pass


# ---------------------------------------------------------------------- #
# Helpers                                                                #
# ---------------------------------------------------------------------- #
def _ctx_get(context: dict, *names: str):
    """First present value among case variants (protobuf JSON vs bridge.js)."""
    if not context:
        return None
    for name in names:
        if name in context:
            return context[name]
    return None


def _find_context_info(raw: dict) -> dict:
    """Locate contextInfo from any message container in a MessageToDict dict."""
    for value in raw.values():
        if isinstance(value, dict):
            ctx = value.get("contextInfo")
            if isinstance(ctx, dict):
                return ctx
    return {}


def _location_text(item: dict, live: bool = False) -> str:
    name = item.get("name") or item.get("address") or ""
    lat = item.get("degreesLatitude")
    lon = item.get("degreesLongitude")
    coords = f"{lat},{lon}" if lat is not None and lon is not None else ""
    kind = "Live location" if live else "Location"
    return f"[{kind}: {' '.join(x for x in [name, coords] if x)}]"
