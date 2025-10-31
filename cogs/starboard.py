from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Pride


async def setup(bot: "Pride") -> None:
    from .config.extended.starboard import Starboard
    
    await bot.add_cog(Starboard(bot))
