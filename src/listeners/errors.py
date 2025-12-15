import discord
from discord.ext import commands
from ..bot import NagromBot

class ErrorHandler(commands.Cog):
    def __init__(self, bot: NagromBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if hasattr(ctx.command, 'on_error'):
            return

        error = getattr(error, 'original', error)

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Rate Limit: Please wait {error.retry_after:.1f}s.", delete_after=10)
        elif isinstance(error, commands.NotOwner):
            await ctx.send("You do not have permission to run this.", delete_after=5)
        elif isinstance(error, commands.CommandNotFound):
            pass
        else:
            print(f"Ignoring exception in command {ctx.command}: {error}")

async def setup(bot: NagromBot):
    await bot.add_cog(ErrorHandler(bot))