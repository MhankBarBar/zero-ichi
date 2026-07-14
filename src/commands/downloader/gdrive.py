import asyncio
from pathlib import Path

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error
from core.logger import log_info
from core.runtime_config import runtime_config
from core.torrent_downloader import aria2rpc, format_eta, format_speed


class GDriveCommand(Command):
    name = "gdrive"
    aliases = ["gmirror", "gdrivemirror"]
    description = "Download torrent and upload to Google Drive"
    usage = "gdrive <magnet_link_or_torrent_url>"
    category = "downloader"
    cooldown = 60

    async def execute(self, ctx: CommandContext) -> None:
        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("errors.usage", usage=self.get_usage(ctx.prefix)))
            return

        uri = ctx.args[0].strip()

        magnet_prefixes = ("magnet:", "http://", "https://")
        if not any(uri.startswith(p) for p in magnet_prefixes):
            await ctx.client.reply(ctx.message, t_error("errors.usage", usage=self.get_usage(ctx.prefix)))
            return

        rclone_cfg = runtime_config.get_nested("rclone", default={})
        if not isinstance(rclone_cfg, dict):
            rclone_cfg = {}
        remote = str(rclone_cfg.get("remote", "gdrive:"))
        remote_path = str(rclone_cfg.get("remote_path", "ZeroIchi/Mirrors/"))

        if not remote.endswith(":"):
            remote = remote + ":"

        await ctx.client.send_reaction(ctx.message, "⏳")

        gid = await aria2rpc.add_download(
            uri=uri,
            sender_jid=ctx.message.sender_jid,
            chat_jid=ctx.message.chat_jid,
        )

        if not gid:
            await ctx.client.send_reaction(ctx.message, "❌")
            await ctx.client.reply(ctx.message, t_error("mirror.failed", error="Failed to start download"))
            return

        progress_msg = await ctx.client.reply(ctx.message, t("mirror.starting"))
        progress_msg_id = progress_msg.ID
        last_progress = -1

        try:
            while True:
                job = await aria2rpc.get_job(gid)
                if not job:
                    break

                if job.status == "complete":
                    await ctx.client.edit_message(
                        ctx.message.chat_jid,
                        progress_msg_id,
                        f"{sym.ARROW} {t('gdrive.uploading')}",
                    )

                    try:
                        from core.constants import TORRENTS_DIR
                        local_dir = TORRENTS_DIR / gid
                        remote_dest = f"{remote}{remote_path}{gid}/"
                        gdrive_links = await self._upload_to_rclone(local_dir, remote_dest)
                    except Exception as e:
                        await ctx.client.edit_message(
                            ctx.message.chat_jid,
                            progress_msg_id,
                            t_error("gdrive.upload_failed", error=str(e)),
                        )
                        await ctx.client.send_reaction(ctx.message, "❌")
                        return

                    file_lines = "\n".join(f"{sym.BULLET} {link}" for link in gdrive_links)

                    await ctx.client.send_reaction(ctx.message, "✅")
                    await ctx.client.edit_message(
                        ctx.message.chat_jid,
                        progress_msg_id,
                        f"{sym.SUCCESS} {t('gdrive.done')}\n\n{file_lines}",
                    )
                    log_info(f"[GDRIVE] Upload complete: {gid}")
                    return

                if job.status == "error":
                    await ctx.client.edit_message(
                        ctx.message.chat_jid,
                        progress_msg_id,
                        t_error("mirror.failed", error=job.error or "Unknown error"),
                    )
                    await ctx.client.send_reaction(ctx.message, "❌")
                    return

                if job.status in ("removed", "cancelled"):
                    await ctx.client.edit_message(
                        ctx.message.chat_jid,
                        progress_msg_id,
                        f"{sym.INFO} {t('mirror.cancelled')}",
                    )
                    await ctx.client.send_reaction(ctx.message, "🚫")
                    return

                current_progress = int(job.progress)
                if current_progress != last_progress:
                    speed_str = format_speed(job.download_speed)
                    eta_str = format_eta(job.total_length, job.completed_length, job.download_speed)
                    await ctx.client.edit_message(
                        ctx.message.chat_jid,
                        progress_msg_id,
                        f"{sym.ARROW} {t('mirror.progress', bullet=sym.BULLET, progress=job.progress, speed=speed_str, eta=eta_str)}",
                    )
                    last_progress = current_progress

                await asyncio.sleep(5)

        except asyncio.CancelledError:
            await aria2rpc.cancel(gid)
            raise

    async def _upload_to_rclone(self, local_path: Path, remote_dest: str) -> list[str]:
        proc = await asyncio.create_subprocess_exec(
            "rclone",
            "copy",
            str(local_path),
            remote_dest,
            "--progress",
            "--verbose",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_text = stderr.decode(errors="replace")[:200] if stderr else "rclone failed"
            raise RuntimeError(error_text)

        links = []
        out = (stdout or b"").decode(errors="replace")
        for line in out.splitlines():
            if "http" in line.lower() and "drive.google.com" in line:
                links.append(line.strip())

        return links


