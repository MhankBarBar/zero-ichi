import asyncio
import os

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error
from core.logger import log_info
from core.torrent_downloader import aria2rpc, format_eta, format_speed


class MirrorCommand(Command):
    name = "mirror"
    aliases = ["torrent"]
    description = "Download torrent/magnet and host files on dashboard"
    usage = "mirror <magnet_link_or_torrent_url>"
    category = "downloader"
    cooldown = 30

    async def execute(self, ctx: CommandContext) -> None:
        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("errors.usage", usage=self.get_usage(ctx.prefix)))
            return

        uri = ctx.args[0].strip()

        magnet_prefixes = ("magnet:", "http://", "https://")
        if not any(uri.startswith(p) for p in magnet_prefixes):
            await ctx.client.reply(ctx.message, t_error("errors.usage", usage=self.get_usage(ctx.prefix)))
            return

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
                    public_url = str(os.getenv("PUBLIC_URL", "http://localhost:8000")).rstrip("/")
                    file_count = len(job.files)
                    dl_url = f"{public_url}/api/torrents/files/{gid}/"

                    await ctx.client.edit_message(
                        ctx.message.chat_jid,
                        progress_msg_id,
                        t("mirror.complete", count=file_count),
                    )

                    buttons = [
                        {"type": "url", "text": "📥 Download Files", "url": dl_url},
                    ]

                    await ctx.client.send_buttons(
                        ctx.message.chat_jid,
                        t("mirror.complete", count=file_count),
                        buttons,
                        quoted=ctx.message.event,
                    )
                    await ctx.client.send_reaction(ctx.message, "✅")
                    log_info(f"[MIRROR] Download complete: {gid}")
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


