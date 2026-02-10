"""
Roll command - Dice rolling.
"""

import random
import re

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t


class RollCommand(Command):
    name = "roll"
    aliases = ["dice", "d"]
    description = "Roll dice (e.g., 2d6, d20)"
    usage = "/roll [dice notation]"
    category = "fun"
    examples = ["/roll", "/roll d20", "/roll 2d6", "/roll 3d8+5"]

    async def execute(self, ctx: CommandContext) -> None:
        """Roll dice."""
        dice_str = ctx.raw_args.strip() if ctx.raw_args else "d6"

        pattern = r"^(\d*)d(\d+)([+-]\d+)?$"
        match = re.match(pattern, dice_str.lower())

        if not match:
            if dice_str.isdigit():
                count = 1
                sides = int(dice_str)
                modifier = 0
            else:
                await ctx.client.reply(
                    ctx.message,
                    f"{sym.INFO} *{t('roll.title')}*\n\n"
                    + t("roll.usage", prefix=ctx.prefix, bullet=sym.BULLET, arrow=sym.ARROW),
                )
                return
        else:
            count = int(match.group(1)) if match.group(1) else 1
            sides = int(match.group(2))
            modifier = int(match.group(3)) if match.group(3) else 0

        if count < 1 or count > 100:
            await ctx.client.reply(ctx.message, f"{sym.ERROR} {t('roll.invalid_count')}")
            return
        if sides < 2 or sides > 1000:
            await ctx.client.reply(ctx.message, f"{sym.ERROR} {t('roll.invalid_sides')}")
            return

        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + modifier

        rolls_str = ", ".join(str(r) for r in rolls)

        if len(rolls) == 1 and modifier == 0:
            result = f"*{total}*"
        elif modifier != 0:
            mod_str = f"+{modifier}" if modifier > 0 else str(modifier)
            result = f"[{rolls_str}] {mod_str} = *{total}*"
        else:
            result = f"[{rolls_str}] = *{total}*"

        mod_display = f"+{modifier}" if modifier > 0 else str(modifier) if modifier else ""
        await ctx.client.reply(
            ctx.message,
            f"{sym.SPARKLE} *{t('roll.title')} {count}d{sides}{mod_display}*\n\n"
            f"{sym.ARROW} {t('roll.result')}: {result}",
        )
