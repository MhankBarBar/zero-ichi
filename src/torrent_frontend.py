from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from core.torrent_downloader import aria2rpc

app = FastAPI(title="Torrent Downloads")

PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8000").rstrip("/")


def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Torrent Downloads</title>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  :root{{color-scheme:dark;--bg:#111;--surface:#1a1a1a;--border:#2a2a2a;--ink:#e5e5e5;--muted:#888;--accent:#22c55e;--accent-dim:rgba(34,197,94,0.1);--radius:8px;--font:system-ui,-apple-system,sans-serif}}
  body{{font:14px/1.6 var(--font);background:var(--bg);color:var(--ink);min-height:100vh}}
  .wrap{{max-width:780px;margin:0 auto;padding:24px 16px}}
  h1{{font-size:22px;font-weight:700;margin-bottom:4px}}
  .sub{{color:var(--muted);font-size:13px;margin-bottom:24px}}
  a{{color:var(--accent);text-decoration:none}}
  a:hover{{text-decoration:underline}}
  .card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin-bottom:12px}}
  .card:hover{{border-color:#333}}
  .row{{display:flex;align-items:center;gap:12px;flex-wrap:wrap}}
  .row .main{{flex:1;min-width:0}}
  .name{{font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .meta{{font-size:12px;color:var(--muted);margin-top:2px}}
  .badge{{display:inline-flex;align-items:center;gap:4px;border-radius:999px;padding:2px 10px;font-size:11px;font-weight:600;border:1px solid transparent}}
  .badge.active{{background:rgba(59,130,246,0.1);color:#60a5fa;border-color:rgba(59,130,246,0.2)}}
  .badge.complete{{background:var(--accent-dim);color:var(--accent);border-color:rgba(34,197,94,0.2)}}
  .badge.error{{background:rgba(239,68,68,0.1);color:#f87171;border-color:rgba(239,68,68,0.2)}}
  .badge.waiting{{background:rgba(234,179,8,0.1);color:#eab308;border-color:rgba(234,179,8,0.2)}}
  .bar{{height:4px;background:#2a2a2a;border-radius:4px;margin-top:8px;overflow:hidden}}
  .bar-fill{{height:100%;background:var(--accent);border-radius:4px;transition:width 1s}}
  .file-list{{margin-top:12px}}
  .file-item{{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:6px;background:rgba(255,255,255,0.03);margin-bottom:4px;font-size:13px;transition:background .15s}}
  .file-item:hover{{background:rgba(255,255,255,0.06)}}
  .file-item .fn{{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .file-item .sz{{color:var(--muted);font-size:11px;white-space:nowrap}}
  .dl-btn{{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:6px;background:var(--accent);color:#000;font-size:13px;font-weight:600;text-decoration:none;transition:opacity .15s}}
  .dl-btn:hover{{opacity:.85;text-decoration:none}}
  .dl-btn-sm{{padding:3px 8px;font-size:11px}}
  .empty{{text-align:center;padding:48px 0;color:var(--muted)}}
  .empty svg{{margin-bottom:12px;opacity:.3}}
  .back{{display:inline-flex;align-items:center;gap:4px;margin-bottom:16px;font-size:13px}}
  .grid{{display:flex;flex-direction:column;gap:8px}}
  .ellipsis{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  @media(max-width:600px){{.wrap{{padding:16px 12px}}h1{{font-size:20px}}}}
</style>
</head>
<body>
<div class="wrap">
{body}
</div>
</body>
</html>"""


def _format_bytes(b: int) -> str:
    if b <= 0: return "~"
    if b >= 1_000_000_000: return f"{b/1_000_000_000:.1f}GB"
    if b >= 1_000_000: return f"{b/1_000_000:.1f}MB"
    if b >= 1_000: return f"{b/1_000:.0f}KB"
    return f"{b}B"


def _format_speed(s: int) -> str:
    if s <= 0: return "~"
    if s >= 1_000_000: return f"{s/1_000_000:.1f}MB/s"
    if s >= 1_000: return f"{s/1_000:.0f}KB/s"
    return f"{s}B/s"


def _truncate_uri(uri: str, n: int = 60) -> str:
    if len(uri) <= n: return uri
    if uri.startswith("magnet:"): return f"magnet:...{uri[-20:]}"
    return f"{uri[:n]}..."


def _status_badge(status: str) -> str:
    cls = status if status in ("active", "complete", "error", "waiting") else ""
    return f'<span class="badge {cls}">{status}</span>'


def _progress_bar(pct: float) -> str:
    p = min(pct, 100)
    return f'<div class="bar"><div class="bar-fill" style="width:{p:.0f}%"></div></div>'


@app.get("/", response_class=HTMLResponse)
async def list_torrents():
    jobs = list(aria2rpc._jobs.values())
    jobs.sort(key=lambda j: j.created_at, reverse=True)

    total = len(jobs)
    complete = sum(1 for j in jobs if j.status == "complete")
    active = sum(1 for j in jobs if j.status in ("active", "waiting"))

    items = []
    for j in jobs:
        is_active = j.status in ("active", "waiting")
        size = _format_bytes(j.total_length)
        speed = _format_speed(j.download_speed) if is_active else ""
        files = f"{len(j.files)} file{'s' if len(j.files) != 1 else ''}"
        bar = _progress_bar(j.progress) if is_active else ""

        items.append(f"""<a href="/{j.gid}" class="card" style="display:block;text-decoration:none;color:inherit">
  <div class="row">
    <div class="main">
      <div class="name">{_truncate_uri(j.uri)}</div>
      <div class="meta">{size} · {files}{f' · {speed}' if speed else ''}</div>
    </div>
    {_status_badge(j.status)}
  </div>
  {bar}
</a>""")

    content = f"""<h1>Torrent Downloads</h1>
<p class="sub">{total} total · {complete} complete{f' · {active} active' if active else ''}</p>
<div class="grid">
  {"".join(items) if items else f'<div class="empty"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg><p>No torrent downloads yet.</p><p style="margin-top:4px;font-size:12px">Use <code style="background:#222;padding:1px 6px;border-radius:4px">/mirror &lt;magnet&gt;</code> in chat to start one.</p></div>'}
</div>"""

    return _page("Torrents", content)


@app.get("/{gid}", response_class=HTMLResponse)
async def torrent_detail(gid: str):
    job = await aria2rpc.get_job(gid)
    if not job:
        raise HTTPException(status_code=404, detail="Torrent not found")

    is_active = job.status in ("active", "waiting")
    size = _format_bytes(job.total_length)
    speed = _format_speed(job.download_speed) if is_active else ""
    error = f"<p style='color:#f87171;margin-top:4px'>{job.error}</p>" if job.error else ""

    file_rows = []
    for f in job.files:
        url = f"{PUBLIC_URL}/api/torrents/files/{gid}/{f.name}"
        sz = _format_bytes(f.size)
        file_rows.append(f"""<div class="file-item">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="flex-shrink:0;color:var(--muted)"><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M17 18h-6"/><path d="M9 14h6"/><path d="M5 4h4l6 6v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2"/></svg>
  <span class="fn">{f.name}</span>
  <span class="sz">{sz}</span>
  <a href="{url}" class="dl-btn dl-btn-sm" target="_blank" rel="noopener">Download</a>
</div>""")

    files_section = ""
    if file_rows:
        files_section = f"""<div class="file-list">
  <div style="font-size:13px;font-weight:600;margin-bottom:8px;color:var(--muted)">{len(job.files)} file{'s' if len(job.files) != 1 else ''}</div>
  {"".join(file_rows)}
</div>"""

    back = '<a href="/" class="back">← Back to all torrents</a>'
    bar = _progress_bar(job.progress) if is_active else ""
    pct = f"<span style='color:var(--accent)'>{job.progress:.1f}%</span>" if is_active else ""

    content = f"""{back}
<h1 style="word-break:break-word">{_truncate_uri(job.uri, 80)}</h1>
<p class="sub" style="margin-bottom:16px">
  {_status_badge(job.status)}
  {f' {pct}' if pct else ''}
  · {size}
  {f' · {speed}' if speed else ''}
</p>
{bar}
{error}
{files_section}"""

    return _page(f"Torrent — {_truncate_uri(job.uri, 40)}", content)


def main():
    port = int(os.getenv("TORRENT_FRONTEND_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
