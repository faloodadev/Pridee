import discord
from discord.ext import commands
from utils.logger import log
from core.bot import Evict

class Information(commands.Cog):
    """Information commands for the bot."""
    
    def __init__(self, bot: Evict):
        self.bot = bot
        log.info(f"{self.__class__.__name__} cog loaded")

    @commands.hybrid_command(
        name="ping",
        description="Check the bot's latency"
    )
    async def ping(self, ctx: commands.Context):
        """Check the bot's latency."""
        latency = round(self.bot.latency * 1000)
        
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Gateway Latency: `{latency}ms`",
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed)

    async def cog_load(self) -> None:
        """Called when the cog is loaded."""
        log.info(f"Loaded {self.__class__.__name__} cog")

    async def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        log.info(f"Unloaded {self.__class__.__name__} cog") 