from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Pride


async def setup(bot: "Pride") -> None:
    from .config.extended.alias import Alias
    from .config.extended.info import Info
    from .config.extended.system import System
    from .config.extended.webhook import Webhook
    from .config.extended.vanity import Vanity
    from discord.ext.commands import Cog
    from utils.tools import CompositeMetaClass
    
    class UtilityCog(Alias, Info, System, Webhook, Vanity, Cog, metaclass=CompositeMetaClass):
        """
        Utility commands for server management and information.
        """
        
        def __init__(self, bot):
            self.bot = bot
            self.description = "Utility and server management tools"
    
    await bot.add_cog(UtilityCog(bot))
