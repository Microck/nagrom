from __future__ import annotations

import discord
from discord.ext import commands

from ..bot import AVABot


class MessageListener(commands.Cog):
    def __init__(self, bot: AVABot):
        self.bot = bot

    async def _queue_fact_check_for_message(
        self,
        *,
        trigger_message: discord.Message,
        statement_text: str,
        statement_author: discord.User | discord.Member,
        trigger_type: str,
        source_message: discord.Message | None,
    ) -> None:
        guild_id = trigger_message.guild.id if trigger_message.guild else None
        channel_id = trigger_message.channel.id

        allowed, reason = self.bot.rate_limiter.check(
            trigger_message.author.id, guild_id or 0
        )
        if not allowed:
            try:
                await trigger_message.reply(
                    f"Rate limit: {reason}", mention_author=False
                )
            except Exception:
                pass
            return

        ok, queue_reason = await self.bot.submit_fact_check(
            guild_id=guild_id,
            channel_id=channel_id,
            source_message_id=(source_message.id if source_message else trigger_message.id),
            requestor_id=trigger_message.author.id,
            statement_author_id=statement_author.id,
            input_text=statement_text,
            trigger_type=trigger_type,  # type: ignore[arg-type]
        )
        if not ok:
            try:
                await trigger_message.reply(
                    queue_reason, mention_author=False
                )
            except Exception:
                pass
            return

        try:
            await trigger_message.add_reaction("🧪")
        except Exception:
            return

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or (self.bot.user and message.author.id == self.bot.user.id):
            return

        if not self.bot.user:
            return

        mentioned = self.bot.user in message.mentions

        # Scenario A: Reply + mention
        if mentioned and message.reference:
            try:
                ref_msg = await message.channel.fetch_message(
                    message.reference.message_id  # type: ignore[arg-type]
                )
            except discord.NotFound:
                return

            if not ref_msg.content:
                return

            text_to_check = ref_msg.content[:500]
            await self._queue_fact_check_for_message(
                trigger_message=message,
                statement_text=text_to_check,
                statement_author=ref_msg.author,
                trigger_type="reply",
                source_message=ref_msg,
            )
            return

        # Scenario B: Direct mention with inline statement
        if mentioned and not message.reference:
            content = message.content.replace(
                f"<@{self.bot.user.id}>", ""
            ).replace(f"<@!{self.bot.user.id}>", "")
            content = content.strip()
            if not content:
                return

            text_to_check = content[:500]
            await self._queue_fact_check_for_message(
                trigger_message=message,
                statement_text=text_to_check,
                statement_author=message.author,
                trigger_type="mention",
                source_message=message,
            )


async def setup(bot: AVABot) -> None:
    await bot.add_cog(MessageListener(bot))