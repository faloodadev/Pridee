from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Pride


async def setup(bot: "Pride") -> None:
    from discord.ext.commands import Cog, hybrid_command, has_permissions
    from discord import Message, Member, TextChannel, Embed, Permissions
    from utils.tools import CompositeMetaClass, MixinMeta
    from core import Context
    
    class RansomwareCog(MixinMeta, Cog, metaclass=CompositeMetaClass):
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
            if not isinstance(ctx.channel, TextChannel):
                return await ctx.warn("This command only works in text channels!")
            
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
            dangerous_permissions = [
                'administrator', 'kick_members', 'ban_members',
                'manage_guild', 'manage_roles', 'manage_channels',
                'manage_webhooks', 'manage_nicknames', 'mention_everyone'
            ]
            
            stripped_count = 0
            for role in user.roles:
                if role.is_default():
                    continue
                    
                perms = role.permissions
                needs_update = False
                new_perms = {}
                
                for perm_name, perm_value in perms:
                    if perm_name in dangerous_permissions and perm_value:
                        new_perms[perm_name] = False
                        needs_update = True
                    else:
                        new_perms[perm_name] = perm_value
                
                if needs_update:
                    await role.edit(permissions=Permissions(**new_perms))
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
