from discord.ext import commands
from ..bot import AVABot

class AdminCommands(commands.Cog):
    def __init__(self, bot: AVABot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(name="reload")
    async def reload_cogs(self, ctx):
        """Reloads all extensions"""
        extensions = [
            "src.listeners.messages",
            "src.listeners.context_menu",
            "src.commands.setup"
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
                await ctx.send(f"Result: {len(rows)} rows returned.\n