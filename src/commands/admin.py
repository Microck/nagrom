import os
from discord.ext import commands
from ..bot import NagromBot


class AdminCommands(commands.Cog):
    def __init__(self, bot: NagromBot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(name="reload")
    async def reload_cogs(self, ctx):
        """Reloads all extensions"""
        extensions = [
            "src.listeners.messages",
            "src.listeners.context_menu",
            "src.commands.setup",
            "src.commands.config",
            "src.commands.admin",
            "src.commands.stats",
            "src.commands.help",
        ]
        msg = await ctx.send("Reloading...")
        try:
            for ext in extensions:
                await self.bot.reload_extension(ext)
            await msg.edit(content="All extensions reloaded.")
        except Exception as e:
            await msg.edit(content=f"Error: {e}")

    @commands.command(name="sql")
    async def run_sql(self, ctx, *, query: str):
        """Raw SQL execution (Dangerous)"""
        async with self.bot.db.engine.begin() as conn:
            try:
                result = await conn.execute(discord.utils.text(query))
                rows = result.fetchall()
                await ctx.send(f"Result: {len(rows)} rows returned.")
            except Exception as e:
                await ctx.send(f"SQL Error: {e}")

    @commands.command(name="logs")
    async def view_logs(self, ctx, lines: int = 20):
        """View recent log entries (Owner Only)"""
        log_file = "nagrom.log"
        if not os.path.exists(log_file):
            if os.path.exists("logs/nagrom.log"):
                log_file = "logs/nagrom.log"
            else:
                await ctx.send("Log file not found.")
                return
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.readlines()
                last_lines = "".join(content[-lines:])
                if len(last_lines) > 1900:
                    last_lines = last_lines[-1900:]
                
                await ctx.send(f"```log\n{last_lines}\n```")
        except Exception as e:
            await ctx.send(f"Error reading logs: {e}")

    @commands.command(name="retry")
    async def retry_check(self, ctx, message_id: int):
        """Retry a failed fact check by Message ID (Owner Only)"""
        async with self.bot.db.session_maker() as session:
            from sqlalchemy import select
            from ..models.database import FactCheck
            
            stmt = select(FactCheck).where(
                (FactCheck.response_message_id == message_id) | 
                (FactCheck.source_message_id == message_id)
            )
            fc = await session.scalar(stmt)
            
            if not fc:
                await ctx.send("Fact check record not found.")
                return
            
            await ctx.send(f"Retrying check for claim: {fc.input_text[:50]}...")
            
            success, reason = await self.bot.submit_fact_check(
                guild_id=fc.guild_id,
                channel_id=fc.channel_id,
                source_message_id=fc.source_message_id,
                requestor_id=ctx.author.id,
                statement_author_id=fc.user_id,
                input_text=fc.input_text,
                trigger_type="slash",
                placeholder_message_id=None
            )
            
            if not success:
                await ctx.send(f"Failed to queue retry: {reason}")


async def setup(bot: NagromBot):
    await bot.add_cog(AdminCommands(bot))
