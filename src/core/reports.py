"""Report center helpers for per-group moderation reports."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from core.constants import DATA_DIR
from core.storage import GroupData


def _default_payload() -> dict[str, Any]:
    return {"counter": 0, "items": []}


def load_reports(group_jid: str) -> dict[str, Any]:
    """Load report payload for a group."""
    data = GroupData(group_jid).load("reports", _default_payload())
    if not isinstance(data, dict):
        return _default_payload()

    counter = int(data.get("counter", 0) or 0)
    items = data.get("items", [])
    if not isinstance(items, list):
        items = []
    return {"counter": counter, "items": items}


def save_reports(group_jid: str, payload: dict[str, Any]) -> None:
    """Persist report payload for a group."""
    GroupData(group_jid).save("reports", payload)


def create_report(
    group_jid: str,
    *,
    reporter_jid: str,
    reporter_name: str,
    reporter_number: str = "",
    reporter_pn: str = "",
    reporter_lid: str = "",
    target_jid: str,
    target_name: str = "",
    target_number: str = "",
    target_pn: str = "",
    target_lid: str = "",
    reason: str,
    evidence_text: str = "",
    evidence_message_id: str = "",
    evidence_sender_jid: str = "",
    evidence_chat_jid: str = "",
    evidence_media_type: str = "",
    evidence_caption: str = "",
) -> dict[str, Any]:
    """Create and persist a new report entry."""
    payload = load_reports(group_jid)
    payload["counter"] += 1
    report_id = f"R{payload['counter']:04d}"

    report = {
        "id": report_id,
        "status": "open",
        "group_jid": group_jid,
        "reporter_jid": reporter_jid,
        "reporter_name": reporter_name,
        "reporter_number": reporter_number,
        "reporter_pn": reporter_pn,
        "reporter_lid": reporter_lid,
        "target_jid": target_jid,
        "target_name": target_name,
        "target_number": target_number,
        "target_pn": target_pn,
        "target_lid": target_lid,
        "reason": reason,
        "evidence_text": evidence_text,
        "evidence_message_id": evidence_message_id,
        "evidence_sender_jid": evidence_sender_jid,
        "evidence_chat_jid": evidence_chat_jid,
        "evidence_media_type": evidence_media_type,
        "evidence_caption": evidence_caption,
        "created_at": datetime.utcnow().isoformat(),
        "resolved_at": None,
        "resolved_by": None,
        "resolution": None,
    }
    payload["items"].append(report)
    save_reports(group_jid, payload)
    return report


def list_reports(group_jid: str, status: str = "") -> list[dict[str, Any]]:
    """List reports, optionally filtered by status."""
    items = load_reports(group_jid)["items"]
    if status:
        status = status.lower().strip()
        items = [r for r in items if str(r.get("status", "")).lower() == status]
    return sorted(items, key=lambda r: r.get("created_at", ""), reverse=True)


def get_report(group_jid: str, report_id: str) -> dict[str, Any] | None:
    """Get one report by id."""
    rid = report_id.strip().upper()
    for item in load_reports(group_jid)["items"]:
        if str(item.get("id", "")).upper() == rid:
            return item
    return None


def find_reports_by_id(report_id: str) -> list[tuple[str, dict[str, Any]]]:
    """Find reports by ID across all groups.

    Returns a list because legacy IDs may collide between groups.
    """
    rid = report_id.strip().upper()
    if not rid:
        return []

    matches: list[tuple[str, dict[str, Any]]] = []
    if not DATA_DIR.exists():
        return matches

    for entry in DATA_DIR.iterdir():
        if not entry.is_dir():
            continue

        report_file = entry / "reports.json"
        if not report_file.exists():
            continue

        try:
            with open(report_file, encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            continue

        items = payload.get("items", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            continue

        for report in items:
            if not isinstance(report, dict):
                continue
            if str(report.get("id", "")).upper() != rid:
                continue

            group_jid = str(report.get("group_jid", "")).strip()
            if not group_jid:
                continue
            matches.append((group_jid, report))

    return matches


def update_report_status(
    group_jid: str,
    report_id: str,
    *,
    status: str,
    resolved_by: str,
    resolution: str,
) -> dict[str, Any] | None:
    """Update report status and resolution metadata."""
    payload = load_reports(group_jid)
    rid = report_id.strip().upper()

    for item in payload["items"]:
        if str(item.get("id", "")).upper() != rid:
            continue

        item["status"] = status
        item["resolved_by"] = resolved_by
        item["resolution"] = resolution
        item["resolved_at"] = datetime.utcnow().isoformat()
        save_reports(group_jid, payload)
        return item

    return None
