"""
Shared text/section builders for downloader selection screens.

Used by the initial /dl, /am, and playlist command entry points
(src/commands/downloader/) as well as the reply/pagination middleware
(src/core/middlewares/download_reply.py) so both sides render identical
content from the same pending data.
"""

from __future__ import annotations

from core import symbols as sym
from core.i18n import t
from core.selection_ui import SelectionItem, SelectionSection


def build_search_text(query: str, results) -> str:
    """Build the numbered search results display text."""
    lines = [f"{sym.SEARCH} *{t('downloader.search_results', query=query)}*", ""]

    for idx, r in enumerate(results, 1):
        lines.append(f" `{idx}.` *{r.title}*")
        lines.append(f"     {sym.ARROW} {r.uploader} {sym.BULLET} {r.duration}")
        lines.append(f"     {sym.BULLET} {r.url}")
        lines.append("")

    lines.append(f"{sym.INFO} {t('downloader.choose_result_hint')}")
    return "\n".join(lines)


def build_search_header(query: str) -> str:
    """Build the short search-results header (no numbered list)."""
    return f"{sym.SEARCH} {t('downloader.search_results', query=query)}"


def build_search_sections(results) -> list[SelectionSection]:
    """Build the SelectionSection for search results."""
    return [
        SelectionSection(
            title="Results",
            items=[
                SelectionItem(
                    id=str(idx), title=r.title, description=f"{r.uploader} • {r.duration}"
                )
                for idx, r in enumerate(results, 1)
            ],
        )
    ]


def build_options_text(info) -> str:
    """Build the numbered format options text."""
    lines = [
        f"{sym.SPARKLE} *{info.title}*",
        "",
        f"{sym.ARROW} {info.uploader}",
        f"{sym.BULLET} {info.platform} {sym.BULLET} {info.duration_str}",
    ]

    if info.filesize_approx:
        lines[-1] += f" {sym.BULLET} ~{info.filesize_str}"

    lines.append("")

    video_formats = [f for f in info.formats if f.type == "video"]
    audio_formats = [f for f in info.formats if f.type == "audio"]

    idx = 1

    if video_formats:
        lines.append(f"*{sym.VIDEO} {t('downloader.video_options')}*")
        for fmt in video_formats:
            size = f" ({fmt.filesize_str})" if fmt.filesize else ""
            lines.append(f" {sym.BULLET} `{idx}.` {fmt.quality} {fmt.ext.upper()}{size}")
            idx += 1
        lines.append("")

    if audio_formats:
        lines.append(f"*{sym.AUDIO} {t('downloader.audio_options')}*")
        for fmt in audio_formats:
            size = f" ({fmt.filesize_str})" if fmt.filesize else ""
            lines.append(f" {sym.BULLET} `{idx}.` {fmt.quality} {fmt.ext.upper()}{size}")
            idx += 1
        lines.append("")

    lines.append(f"{sym.INFO} {t('downloader.choose_hint')}")
    return "\n".join(lines)


def build_options_header(info) -> str:
    """Build the short media info header (no numbered format list)."""
    lines = [
        f"{sym.SPARKLE} *{info.title}*",
        f"{sym.ARROW} {info.uploader}",
        f"{sym.BULLET} {info.platform} {sym.BULLET} {info.duration_str}",
    ]
    if info.filesize_approx:
        lines[-1] += f" {sym.BULLET} ~{info.filesize_str}"
    return "\n".join(lines)


def build_format_sections(info) -> list[SelectionSection]:
    """Build video/audio SelectionSections from format options."""
    sections = []
    idx = 1

    video_formats = [f for f in info.formats if f.type == "video"]
    audio_formats = [f for f in info.formats if f.type == "audio"]

    if video_formats:
        items = []
        for fmt in video_formats:
            size = f" ({fmt.filesize_str})" if fmt.filesize else ""
            items.append(SelectionItem(id=str(idx), title=f"{fmt.quality} {fmt.ext.upper()}{size}"))
            idx += 1
        sections.append(SelectionSection(title=f"{sym.VIDEO} Video", items=items))

    if audio_formats:
        items = []
        for fmt in audio_formats:
            size = f" ({fmt.filesize_str})" if fmt.filesize else ""
            items.append(SelectionItem(id=str(idx), title=f"{fmt.quality} {fmt.ext.upper()}{size}"))
            idx += 1
        sections.append(SelectionSection(title=f"{sym.AUDIO} Audio", items=items))

    return sections


def build_playlist_text(playlist) -> str:
    """Build the numbered playlist track list."""
    showing = len(playlist.entries)
    total = playlist.count

    lines = [
        f"{sym.SPARKLE} *{playlist.title}*",
        f"{sym.BULLET} {t('downloader.playlist_tracks', showing=showing, total=total)}",
        "",
    ]

    for entry in playlist.entries:
        lines.append(f" `{entry.index}.` *{entry.title}*")
        detail = f"     {sym.BULLET} {entry.duration}"
        if entry.uploader:
            detail += f" {sym.BULLET} {entry.uploader}"
        lines.append(detail)
        lines.append("")

    lines.append(f"{sym.INFO} {t('downloader.choose_result_hint')}")
    return "\n".join(lines)


def build_playlist_header(playlist) -> str:
    """Build the short playlist header (no numbered track list)."""
    return (
        f"{sym.SPARKLE} {playlist.title}\n"
        f"{sym.BULLET} "
        f"{t('downloader.playlist_tracks', showing=len(playlist.entries), total=playlist.count)}"
    )


def build_playlist_sections(entries) -> list[SelectionSection]:
    """Build the SelectionSection for playlist tracks."""
    return [
        SelectionSection(
            title="Tracks",
            items=[
                SelectionItem(
                    id=str(entry.index),
                    title=entry.title,
                    description=f"{entry.uploader} • {entry.duration}"
                    if entry.uploader
                    else entry.duration,
                )
                for entry in entries
            ],
        )
    ]


def build_album_text(info) -> str:
    """Build the numbered Apple Music album track list display text."""
    lines = [
        f"{sym.MUSIC} *{info.album}*",
        f"{sym.ARROW} {info.artist} {sym.BULLET} {info.count} tracks",
        "",
    ]

    for idx, track in enumerate(info.tracks, 1):
        lines.append(f" `{idx}.` *{track.name}*")
        detail = f"     {sym.ARROW} {track.artist}"
        if track.duration:
            detail += f" {sym.BULLET} {track.duration}"
        lines.append(detail)

    lines.append("")
    lines.append(f"{sym.INFO} {t('applemusic.choose_hint')}")
    return "\n".join(lines)


def build_album_header(info) -> str:
    """Build the short Apple Music album header (no numbered track list)."""
    return f"{sym.MUSIC} *{info.album}*\n{sym.ARROW} {info.artist} {sym.BULLET} {info.count} tracks"


def build_track_sections(tracks) -> list[SelectionSection]:
    """Build the SelectionSection for Apple Music album tracks."""
    return [
        SelectionSection(
            title="Tracks",
            items=[
                SelectionItem(
                    id=str(idx),
                    title=track.name,
                    description=f"{track.artist} • {track.duration}"
                    if track.duration
                    else track.artist,
                )
                for idx, track in enumerate(tracks, 1)
            ],
        )
    ]
