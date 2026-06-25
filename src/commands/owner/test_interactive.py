"""
Owner commands to test interactive messages.
"""

from core.command import Command, CommandContext


class TestInteractiveCommand(Command):
    name = "testui"
    description = "Test interactive message features (buttons/carousel)"
    usage = "testui <buttons|carousel|legacy|ai>"
    aliases = ["tui"]
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        if not ctx.args:
            await ctx.client.reply(
                ctx.message,
                f"Usage: `{ctx.prefix}testui <buttons|carousel|legacy|ai>`",
            )
            return

        action = ctx.args[0].lower()

        if action == "buttons":
            await self._test_buttons(ctx)
        elif action == "carousel":
            await self._test_carousel(ctx)
        elif action == "legacy":
            await self._test_legacy(ctx)
        elif action == "ai":
            await self._test_ai(ctx)
        else:
            await ctx.client.reply(
                ctx.message,
                f"Unknown action: `{action}`. Available: buttons, carousel, legacy, ai",
            )

    async def _test_buttons(self, ctx: CommandContext) -> None:
        await ctx.client.send_buttons(
            to=ctx.message.chat_jid,
            title="Modern Native Flow",
            text="This is a test of the modern ButtonMessage builder API.",
            footer="Zero Ichi Bot",
            buttons=[
                {"type": "reply", "text": "Quick Reply", "id": "test_btn_1"},
                {
                    "type": "url",
                    "text": "Open GitHub",
                    "url": "https://github.com/mhankbarbar/zero-ichi",
                },
                {"type": "copy", "text": "Copy Promo", "code": "ZeRo-IcHi"},
                {"type": "call", "text": "Call Support", "phone": "+1234567890"},
                {"type": "reminder", "text": "Set Reminder", "id": "remind_1"},
                {"type": "location"},
                {
                    "type": "selection",
                    "title": "More Options",
                    "sections": [
                        {
                            "title": "Main Menu",
                            "highlight": "Start Here",
                            "rows": [
                                {
                                    "title": "Profile",
                                    "description": "View your profile",
                                    "id": "profile_id",
                                    "header": "User",
                                },
                                {
                                    "title": "Settings",
                                    "description": "Change preferences",
                                    "id": "settings_id",
                                    "header": "System",
                                },
                            ],
                        }
                    ],
                },
            ],
        )

    async def _test_carousel(self, ctx: CommandContext) -> None:
        sample_img = (
            "https://raw.githubusercontent.com/krypton-byte/neonize/master/docs/assets/neonize.png"
        )

        cards = [
            {
                "title": "🍕 Pizza",
                "body": "Delicious cheese pizza, very tasty.",
                "footer": "$5.99",
                "image": sample_img,
                "buttons": [
                    {"type": "reply", "text": "Buy Pizza", "id": f"{ctx.prefix}ping"},
                    {"type": "url", "text": "View Info", "url": "https://example.com/pizza"},
                ],
            },
            {
                "title": "🍔 Burger",
                "body": "A juicy double cheeseburger with fries.",
                "footer": "$8.99",
                "image": sample_img,
                "buttons": [
                    {"type": "reply", "text": "Buy Burger", "id": f"{ctx.prefix}status"},
                    {"type": "url", "text": "View Info", "url": "https://example.com/burger"},
                ],
            },
        ]

        await ctx.client.send_carousel(
            to=ctx.message.chat_jid,
            text="🛒 Check out our menu items below:",
            footer="Swipe horizontally to view more",
            cards=cards,
        )

    async def _test_legacy(self, ctx: CommandContext) -> None:
        await ctx.client.send_legacy_buttons(
            to=ctx.message.chat_jid,
            title="Legacy V2 Buttons",
            subtitle="Location Hack",
            thumbnail="https://raw.githubusercontent.com/krypton-byte/neonize/master/docs/assets/neonize.png",
            text="This uses the older ButtonsMessage protobuf via a Location header. It usually bypasses some client-side native flow restrictions.",
            footer="Zero Ichi Bot",
            buttons=[
                {"text": "Ping", "id": f"{ctx.prefix}ping"},
                {"text": "Status", "id": f"{ctx.prefix}status"},
            ],
        )

    async def _test_ai(self, ctx: CommandContext) -> None:
        await ctx.client.send_ai_rich(
            to=ctx.message.chat_jid,
            title="🤖 AI Rich Response Test",
            footer="Zero Ichi Bot",
            elements=[
                {
                    "type": "text",
                    "text": "Here is a code snippet [example](https://github.com/krypton-byte/neonize):",
                },
                {
                    "type": "code",
                    "language": "python",
                    "code": "def hello():\n    print('Hello World!')",
                },
                {"type": "text", "text": "And here is a data table:"},
                {
                    "type": "table",
                    "table": [
                        ["Model", "Speed", "Quality"],
                        ["GPT-3.5", "Fast", "Good"],
                        ["GPT-4", "Slow", "Excellent"],
                    ],
                },
                {"type": "text", "text": "Sources [1](https://google.com):"},
                {
                    "type": "source",
                    "sources": [
                        {
                            "display_name": "Google",
                            "url": "https://google.com",
                            "favicon_url": "https://www.google.com/favicon.ico",
                        }
                    ],
                },
            ],
        )
