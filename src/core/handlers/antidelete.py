from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message
from neonize.utils.jid import Jid2String, JIDToNonAD, jid_is_lid

from config.settings import features
from core import symbols as sym
from core.cache import message_cache
from core.client import BotClient
from core.i18n import t
from core.logger import log_debug, log_error, log_info, log_warning
from core.runtime_config import runtime_config


async def handle_anti_delete_cache(bot: BotClient, event: any, msg: any):
    """Cache messages for anti-delete feature."""
    if not features.anti_delete or not msg.is_group:
        return

    log_debug(f"Caching msg ID: {event.Info.ID} from {msg.sender_name}")

    group_name = await bot.get_group_name(msg.chat_jid)

    source = event.Info.MessageSource
    sender = source.Sender
    if jid_is_lid(sender):
        senderalt = source.SenderAlt
        sender = senderalt if senderalt.ListFields() else sender
    participant_str = Jid2String(JIDToNonAD(sender))

    chat_str = Jid2String(JIDToNonAD(source.Chat))

    cache_data = {
        "chat": chat_str,
        "chat_name": group_name,
        "sender": participant_str,
        "sender_name": msg.sender_name,
        "text": msg.text,
        "timestamp": event.Info.Timestamp,
        "message_bytes": event.Message.SerializeToString(),
    }

    message_cache.store(event.Info.ID, cache_data)


async def handle_anti_revoke(bot: BotClient, event: any, msg: any):
    """
    Handle message revocation events (Anti-Delete).

    When someone deletes a message:
    - Forwards the original message
    - Sends context message that quotes the forwarded message
    """
    if not features.anti_delete or not msg.is_group:
        return

    try:
        if not event.Message.HasField("protocolMessage"):
            return

        proto_msg = event.Message.protocolMessage
        if proto_msg.type != proto_msg.Type.REVOKE:
            return

        revoked_msg_id = proto_msg.key.ID
        log_info(f"[ANTI-DELETE] Message {revoked_msg_id} was deleted by {msg.sender_name}")

        cached = message_cache.get(revoked_msg_id)
        if not cached:
            log_warning(
                f"[ANTI-DELETE] Could not find message {revoked_msg_id} in cache (may be too old)"
            )
            return

        original_sender = cached.get("sender_name", "Unknown")
        original_chat_name = cached.get("chat_name", "Unknown Group")
        original_text = cached.get("text", "")

        forward_to = runtime_config.get_nested("anti_delete", "forward_to", default="")
        target_chat = forward_to if forward_to else msg.chat_jid

        deleter_jid = msg.sender_jid
        deleter_mention = f"@{deleter_jid.split('@')[0]}" if deleter_jid else msg.sender_name

        if cached.get("message_bytes"):
            try:
                original_msg = Message.FromString(cached["message_bytes"])
                original_sender_jid = cached.get("sender", "")
                original_chat_jid = cached.get("chat", "")

                is_cross_chat = forward_to and forward_to != msg.chat_jid

                forward_response = await bot.forward_message_with_quote(
                    to=target_chat,
                    message=original_msg,
                    quoted_id=revoked_msg_id,
                    quoted_message=original_msg,
                    quoted_participant=original_sender_jid,
                    remote_jid=original_chat_jid if is_cross_chat else None,
                )

                context_text = f"{sym.TRASH} *{t('antidelete.deleted_message')}*\n\n*{t('antidelete.deleted_by')}* {deleter_mention}\n*{t('antidelete.original_sender')}* {original_sender}\n*{t('antidelete.group')}* {original_chat_name}"

                if forward_response and forward_response.ID:
                    await bot.send_reply_to_message(
                        to=target_chat,
                        text=context_text,
                        quoted_id=forward_response.ID,
                        quoted_message=forward_response.Message
                        if forward_response.Message
                        else original_msg,
                    )
                else:
                    await bot.send(target_chat, context_text)

                log_info(f"[ANTI-DELETE] Forwarded deleted message from {original_sender}")
            except Exception as e:
                log_error(f"[ANTI-DELETE] Failed to forward with quote: {e}")
                context_text = f"{sym.TRASH} *{t('antidelete.deleted_message')}*\n\n*{t('antidelete.deleted_by')}* {deleter_mention}\n*{t('antidelete.original_sender')}* {original_sender}\n*{t('antidelete.group')}* {original_chat_name}"
                try:
                    await bot.forward_message(target_chat, original_msg)
                    await bot.send(target_chat, context_text)
                except Exception as e2:
                    log_error(f"[ANTI-DELETE] Fallback forward failed: {e2}")
                    if original_text:
                        await bot.send(target_chat, f"{context_text}\n\n{original_text}")
                    else:
                        await bot.send(
                            target_chat, f"{context_text}\n\n[Failed to recover content]"
                        )
        elif original_text:
            context_text = f"{sym.TRASH} *{t('antidelete.deleted_message')}*\n\n*{t('antidelete.deleted_by')}* {deleter_mention}\n*{t('antidelete.original_sender')}* {original_sender}\n*{t('antidelete.group')}* {original_chat_name}"
            await bot.send(target_chat, f"{context_text}\n\n{original_text}")
        else:
            await bot.send(target_chat, f"{context_text}\n\n[{t('antidelete.unknown_content')}]")

    except Exception as e:
        log_error(f"Error in anti-revoke handler: {e}")
