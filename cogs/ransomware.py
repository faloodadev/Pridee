from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Pride


async def setup(bot: "Pride") -> None:
    from .config.extended.recording import Recording
    from discord.ext.commands import Cog, hybrid_command, has_permissions, Group
    from discord import Message, Member, TextChannel
    from utils.tools import CompositeMetaClass, MixinMeta
    from core import Context
    
    class RansomwareCog(Recording, Cog, metaclass=CompositeMetaClass):
        """
        Dangerous and destructive commands - use with caution!
        """
        
        def __init__(self, bot):
            self.bot = bot
            self.description = "Dangerous server management commands"
        
        @hybrid_command(name="nuke")
        @has_permissions(manage_channels=True, manage_guild=True)
        async def nuke_command(self, ctx: Context) -> Message:
            """
            Nuke (delete and recreate) the current channel.
            """
            from discord import Embed
            
            if not isinstance(ctx.channel, TextChannel):
                return await ctx.warn("This command only works in text channels!")
            
            embed = Embed(
                title="⚠️ Channel Nuke Confirmation",
                description="Are you sure you want to nuke this channel? This will delete and recreate it.",
                color=0xFF0000
            )
            
            confirmed = await ctx.confirm(
                embed=embed,
                reason=f"Nuked by {ctx.author} ({ctx.author.id})",
            )
            
            if not confirmed:
                return await ctx.warn("Channel nuke cancelled!")
            
            channel = ctx.channel
            position = channel.position
            category = channel.category
            
            new_channel = await channel.clone(
                reason=f"Nuked by {ctx.author} ({ctx.author.id})"
            )
            await new_channel.edit(position=position, category=category)
            await channel.delete(reason=f"Nuked by {ctx.author} ({ctx.author.id})")
            
            embed = Embed(
                title="💥 Channel Nuked",
                description=f"Channel has been successfully nuked and recreated!",
                color=0x00FF00
            )
            embed.add_field(
                name="Reconfigured",
                value=f"Position: {position}\nCategory: {category.name if category else 'None'}",
                inline=False
            )
            
            return await new_channel.send(embed=embed)
        
        @hybrid_command(name="strip")
        @has_permissions(manage_roles=True)
        async def strip_command(self, ctx: Context, user: Member) -> Message:
            """
            Strip a member of all dangerous permissions.
            """
            from discord import Embed
            
            dangerous_permissions = [
                'administrator', 'kick_members', 'ban_members',
                'manage_guild', 'manage_roles', 'manage_channels',
                'manage_webhooks', 'manage_nicknames', 'mention_everyone'
            ]
            
            stripped_count = 0
            for role in user.roles:
                if role.is_default():
                    continue
                    
                perms_dict = dict(role.permissions)
                needs_update = False
                
                for perm in dangerous_permissions:
                    if perms_dict.get(perm, False):
                        perms_dict[perm] = False
                        needs_update = True
                
                if needs_update:
                    await role.edit(permissions=perms_dict.Permissions(**perms_dict))
                    stripped_count += 1
            
            if stripped_count == 0:
                return await ctx.warn(f"{user.mention} has no dangerous permissions to strip!")
            
            embed = Embed(
                title="✅ Permissions Stripped",
                description=f"Removed dangerous permissions from {stripped_count} role(s) for {user.mention}",
                color=0x00FF00
            )
            
            return await ctx.send(embed=embed)
    
    await bot.add_cog(RansomwareCog(bot))
