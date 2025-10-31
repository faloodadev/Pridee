from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Pride


async def setup(bot: "Pride") -> None:
    from .config.extended.spotify import Spotify
    from discord.ext.commands import Cog
    from utils.tools import CompositeMetaClass
    
    class MusicCog(Spotify, Cog, metaclass=CompositeMetaClass):
        """
        Music and Spotify integration commands.
        """
        
        def __init__(self, bot):
            self.bot = bot
            self.description = "Spotify music integration and control"
    
    await bot.add_cog(MusicCog(bot))
