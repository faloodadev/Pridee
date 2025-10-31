from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Pride


async def setup(bot: "Pride") -> None:
    from .config.extended.security import AntiNuke, AntiRaid
    from discord.ext.commands import Cog
    from utils.tools import CompositeMetaClass
    
    class AntiNukeCog(AntiNuke, AntiRaid, Cog, metaclass=CompositeMetaClass):
        """
        Anti-Nuke and Anti-Raid security features to protect your server.
        """
        
        def __init__(self, bot):
            self.bot = bot
            self.description = "Server security and anti-nuke protection"
    
    await bot.add_cog(AntiNukeCog(bot))
