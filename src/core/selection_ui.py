"""
Shared button/list selection UI for downloader flows.

WhatsApp Web/Desktop can't render interactive button/list messages (shows
"This message couldn't load..."), so every call here checks
``msg.is_web_client`` and falls back to plain numbered text for those users.
Everyone else gets a native "selection" list message instead, with
pagination (8 items/page) and an optional "Download All" row.

Row ids are global 1-based indices matching the existing numbered-reply
convention (see ``core.middlewares.download_reply._parse_selection``), so a
tapped row and a typed reply resolve identically downstream.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.logger import log_warning

PAGE_SIZE = 8
ROW_TITLE_LIMIT = 24
ROW_DESC_LIMIT = 72


@dataclass
class SelectionItem:
    """A single selectable row. `id` is what comes back on tap (or as typed text)."""

    id: str
    title: str
    description: str = ""


@dataclass
class SelectionSection:
    """A named group of rows (e.g. "Video", "Audio")."""

    title: str
    items: list[SelectionItem]


def _truncate(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


async def send_selection(
    bot,
    msg,
    *,
    fallback_text: str,
    sections: list[SelectionSection],
    header: str,
    menu_title: str = "Choose",
    card_title: str = "",
    footer: str = "",
    thumbnail: str | bytes | None = None,
    page: int = 0,
    allow_all: bool = False,
):
    """
    Send a selection prompt, using buttons when the requester's client can
    render them and plain text otherwise (or if sending buttons fails).
    """
    if not msg.is_web_client:
        try:
            return await _send_button_page(
                bot,
                msg,
                sections=sections,
                header=header,
                menu_title=menu_title,
                card_title=card_title,
                footer=footer,
                thumbnail=thumbnail,
                page=page,
                allow_all=allow_all,
            )
        except Exception as e:
            log_warning(f"[DOWNLOADER] Failed to send button selection, falling back to text: {e}")

    return await _send_fallback(bot, msg, fallback_text, thumbnail)


async def _send_fallback(bot, msg, text: str, thumbnail: str | bytes | None):
    if thumbnail:
        try:
            return await bot.send_image(msg.chat_jid, thumbnail, caption=text, quoted=msg.event)
        except Exception:
            pass
    return await bot.reply(msg, text)


async def _send_button_page(
    bot,
    msg,
    *,
    sections: list[SelectionSection],
    header: str,
    menu_title: str,
    card_title: str,
    footer: str,
    thumbnail: str | bytes | None,
    page: int,
    allow_all: bool,
):
    flat: list[tuple[str, SelectionItem]] = [
        (section.title, item) for section in sections for item in section.items
    ]
    total = len(flat)
    start = page * PAGE_SIZE
    page_items = flat[start : start + PAGE_SIZE]
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    grouped: dict[str, list[SelectionItem]] = {}
    order: list[str] = []
    for section_title, item in page_items:
        if section_title not in grouped:
            grouped[section_title] = []
            order.append(section_title)
        grouped[section_title].append(item)

    rows_sections = []

    if allow_all and page == 0:
        rows_sections.append(
            {
                "title": "Actions",
                "rows": [
                    {
                        "title": "Download All",
                        "description": "Download every item in the list",
                        "id": "all",
                    }
                ],
            }
        )

    for section_title in order:
        rows_sections.append(
            {
                "title": section_title,
                "rows": [
                    {
                        "title": _truncate(item.title, ROW_TITLE_LIMIT),
                        "description": _truncate(item.description, ROW_DESC_LIMIT),
                        "id": item.id,
                    }
                    for item in grouped[section_title]
                ],
            }
        )

    nav_rows = []
    if page > 0:
        nav_rows.append({"title": "◀ Prev", "id": f"page:{page - 1}"})
    if start + PAGE_SIZE < total:
        nav_rows.append({"title": "▶ Next", "id": f"page:{page + 1}"})
    if nav_rows:
        rows_sections.append({"title": "Navigate", "rows": nav_rows})

    display_footer = footer
    if total_pages > 1:
        page_note = f"Page {page + 1}/{total_pages}"
        display_footer = f"{footer} • {page_note}" if footer else page_note

    return await bot.send_buttons(
        to=msg.chat_jid,
        text=header,
        title=card_title,
        footer=display_footer,
        image=thumbnail,
        quoted=msg,
        buttons=[
            {
                "type": "selection",
                "title": menu_title,
                "sections": rows_sections,
            }
        ],
    )
