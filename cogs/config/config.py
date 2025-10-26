from discord.ext.commands import Cog
from .extended import Extended


class Config(Extended, Cog):
    """
    Configuration and server management commands.
    """

    def __init__(self, bot):
        self.bot = bot
        self.description = "Configuration and server management"
