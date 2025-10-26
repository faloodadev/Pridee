import config

from discord.ui import Select, View
from discord import Interaction, SelectOption
from discord.ext.commands import Group, MinimalHelpCommand
from discord.ext.commands.cog import Cog
from discord.ext.commands.flags import FlagConverter
from discord.ext.commands.flags import FlagsMeta
from discord.ext.commands.cog import Cog
from discord.ext.commands import Command
from discord.utils import MISSING
from discord.ext.commands import Context

from utils.conversions import Status
from managers.paginator import Paginator

from typing import List, Mapping, Union, Any, Callable, Coroutine
from core.context import Embed


class PrideHelp(MinimalHelpCommand):
    context: "Context"

    def __init__(self, **options):

        super().__init__(
            command_attrs={
                "help": "Shows help about the bot, a command, or a category of commands.",
                "aliases": ["h"],
                "example": "lastfm",
            },
            **options,
        )

        self.bot_user = None

    async def initialize_bot_user(self):

        if not self.bot_user:
            self.bot_user = self.context.bot.user

    async def create_main_help_embed(self, ctx):
        embed = Embed(
            description=await ctx.bot.get_text("system.help.INFORMATION_DESC", ctx),
        )

        embed.add_field(
            name="Invite",
            value="**[invite](https://discord.com/oauth2/authorize?client_id=1203514684326805524)**  • "
            "**[support](https://discord.gg/evict)**  • "
            "**[view on web](https://evict.bot)**",
            inline=False,
        )

        embed.set_author(
            name=f"{ctx.bot.user.name}",
            icon_url=ctx.bot.user.display_avatar.url,
            url=config.CLIENT.SUPPORT_URL,
        )
        embed.set_footer(text=await ctx.bot.get_text("system.help.SELECT_CATEGORY", ctx))

        return embed

    async def send_default_help_message(self, command: Command):
        await self.initialize_bot_user()

        try:
            syntax = f"{self.context.clean_prefix}{command.qualified_name} {' '.join([f'({parameter.name})' if not parameter.optional else f'[{parameter.name}]' for parameter in command.arguments])}"

        except AttributeError:
            syntax = f"{self.context.clean_prefix}{command.qualified_name}"

        embed = Embed(
            title=f"Command: {command.qualified_name}",
            description="Get help on a command",
        )

        embed.add_field(
            name="",
            value=f"```Ruby\nSyntax: {syntax}\nExample: {self.context.clean_prefix}{command.qualified_name} {command.example or ''}```",
            inline=False,
        )

        await self.context.reply(embed=embed)

    async def send_bot_help(
        self, mapping: Mapping[Union[Cog, None], List[Command[Any, Callable[..., Any], Any]]]  # type: ignore
    ) -> Coroutine[Any, Any, None]:  # type: ignore

        await self.initialize_bot_user()
        bot = self.context.bot

        embed = await self.create_main_help_embed(self.context)
        embed.set_thumbnail(url=bot.user.display_avatar.url)

        categories = sorted(
            [
                (cog.qualified_name, cog.description)
                for cog in mapping.keys()
                if cog
                and cog.qualified_name
                not in [
                    "Jishaku",
                    "Network",
                    "API",
                    "Owner",
                    "Status",
                    "Listeners",
                    "Hog",
                ]
                and "cogs" in cog.__module__
            ]
        )

        if not categories:
            return

        select = Select(
            placeholder=await self.context.bot.get_text("system.help.DROPDOWN_PLACEHOLDER", self.context),
            options=[
                SelectOption(
                    label=category[0], value=category[0], description=category[1]
                )
                for category in categories
            ],
        )

        async def select_callback(interaction: Interaction):
            if interaction.user.id != self.context.author.id:
                await interaction.warn(await self.context.bot.get_text("system.help.CANNOT_INTERACT", self.context))
                return

            selected_category = interaction.data["values"][0]  # type: ignore
            selected_cog = next(
                (
                    cog
                    for cog in mapping.keys()
                    if (cog and cog.qualified_name == selected_category)
                    or (not cog and selected_category == "No Category")
                ),
                None,
            )

            commands = mapping[selected_cog]
            command_list = ", ".join(
                [
                    (
                        f"{command.name}*"
                        if isinstance(command, Group)
                        else f"{command.name}"
                    )
                    for command in commands
                ]
            )

            embed = Embed(
                title=await self.context.bot.get_text("system.help.CATEGORY.TITLE", self.context, category_name=selected_category),
                description=f"```\n{command_list}\n```",
            )

            embed.set_author(
                name=f"{bot.user.name}", icon_url=bot.user.display_avatar.url
            )

            embed.set_footer(
                text=await self.context.bot.get_text("system.help.CATEGORY.FOOTER", self.context,
                    count=len(commands),
                    plural="s" if len(commands) != 1 else ""
                )
            )

            await interaction.response.edit_message(embed=embed, view=view)

        select.callback = select_callback

        view = View(timeout=180)
        view.add_item(select)

        await self.context.reply(embed=embed, view=view)

    async def send_group_help(self, group: Group):
        await self.initialize_bot_user()
        bot = self.context.bot
        embeds = []

        if group.help or group.description:
            try:
                syntax = f"{self.context.clean_prefix}{group.qualified_name} {' '.join([f'({parameter.name})' if not parameter.optional else f'[{parameter.name}]' for parameter in group.arguments])}"
            except AttributeError:
                syntax = f"{self.context.clean_prefix}{group.qualified_name}"

            try:
                permissions = ", ".join(
                    [
                        permission.lower().replace("n/a", "None").replace("_", " ")
                        for permission in group.permissions
                    ]
                )
            except AttributeError:
                permissions = "None"

            brief = group.brief or ""

            if permissions != "None" and brief:
                permissions = f"{permissions}\n{brief}"
            elif brief:
                permissions = brief

            embed = Embed(
                title=await self.context.bot.get_text("system.help.COMMAND.title.GROUP", self.context,
                    command_name=group.qualified_name,
                    module_name=group.cog_name
                ),
                description=f"> {group.description.capitalize() if group.description else (group.help.capitalize() if group.help else None)}",
            )
            
            embed.set_author(
                name=f"{bot.user.name} help", icon_url=bot.user.display_avatar.url
            )

            embed.add_field(
                name="",
                value=f"```Ruby\nSyntax: {syntax}\nExample: {self.context.clean_prefix}{group.qualified_name} {group.example or ''}```",
                inline=False,
            )

            embed.add_field(
                name="Permissions",
                value=f"{permissions}",
                inline=True,
            )

            embeds.append(embed)

        for command in group.commands:
            try:
                syntax = f"{self.context.clean_prefix}{command.qualified_name} {' '.join([f'({parameter.name})' if not parameter.optional else f'[{parameter.name}]' for parameter in command.arguments])}"
            except AttributeError:
                syntax = f"{self.context.clean_prefix}{command.qualified_name}"

            try:
                permissions = ", ".join(
                    [
                        permission.lower().replace("n/a", "None").replace("_", " ")
                        for permission in command.permissions
                    ]
                )
            except AttributeError:
                permissions = "None"

            brief = command.brief or ""

            if permissions != "None" and brief:
                permissions = f"{permissions}\n{brief}"
            elif brief:
                permissions = brief

            embed = Embed(
                title=f"{command.qualified_name} • {command.cog_name}",
                description=f"> {command.description.capitalize() if command.description else (command.help.capitalize() if command.help else None)}",
            )

            embed.add_field(
                name="",
                value=f"```Ruby\nSyntax: {syntax}\nExample: {self.context.clean_prefix}{command.qualified_name} {command.example or ''}```",
                inline=False,
            )

            embed.add_field(
                name="Permissions",
                value=f"{permissions}",
                inline=True,
            )

            for param in command.clean_params.values():
                if isinstance(param.annotation, FlagsMeta):
                    await self._add_flag_formatting(param.annotation, embed)

            embed.set_footer(
                text=f"Aliases: {', '.join(a for a in command.aliases) if len(command.aliases) > 0 else 'none'} ",
                icon_url=self.context.author.display_avatar.url,
            )

            embeds.append(embed)

        if embeds:
            paginator_instance = Paginator(ctx=self.context, entries=embeds)
            await paginator_instance.start()
        else:
            await self.context.reply("No commands available in this group.")

    async def send_command_help(self, command: Command):

        await self.initialize_bot_user()

        if command.cog is None or "cogs" not in getattr(command.cog, "__module__", ""):
            await self.send_default_help_message(command)
            return

        bot = self.context.bot

        try:
            syntax = f"{self.context.clean_prefix}{command.qualified_name} {' '.join([f'({parameter.name})' if not parameter.optional else f'[{parameter.name}]' for parameter in command.arguments])}"

        except AttributeError:
            syntax = f"{self.context.clean_prefix}{command.qualified_name}"

        try:
            permissions = ", ".join(
                [
                    permission.lower().replace("n/a", "None").replace("_", " ")
                    for permission in command.permissions
                ]
            )

        except AttributeError:
            permissions = "None"

        brief = command.brief or ""

        if permissions != "None" and brief:
            permissions = f"{permissions}\n{brief}"

        elif brief:
            permissions = brief

        embed = Embed(
            title=await self.context.bot.get_text("system.help.COMMAND.title.NORMAL", self.context,
                command_name=command.qualified_name,
                module_name=command.cog_name),
            description=f"> {command.description.capitalize() if command.description else (command.help.capitalize() if command.help else None)}",
        )

        embed.add_field(
            name="",
            value=await self.context.bot.get_text("system.help.COMMAND.SYNTAX", self.context,
                syntax=syntax,
                prefix=self.context.clean_prefix,
                command_name=command.qualified_name,
                example=command.example or ''
            ),
            inline=False,
        )

        embed.add_field(
            name=await self.context.bot.get_text("system.help.COMMAND.PERMISSIONS", self.context),
            value=f"{permissions}",
            inline=True,
        )

        for param in command.clean_params.values():
            if isinstance(param.annotation, FlagsMeta):
                await self._add_flag_formatting(param.annotation, embed)

        embed.set_footer(
            text=await self.context.bot.get_text("system.help.COMMAND.ALIASES", self.context,
                aliases=', '.join(a for a in command.aliases) if len(command.aliases) > 0 else 'none'
            ),
            icon_url=self.context.author.display_avatar.url,
        )

        embed.set_author(
            name=f"{bot.user.name} help", 
            icon_url=bot.user.display_avatar.url
        )

        await self.context.reply(embed=embed)

    async def send_error_message(self, error: str):

        if not error or not error.strip():
            return

        embed = Embed(
            title="Error",
            description=error,
        )

        await self.context.send(embed=embed)

    async def command_not_found(self, string: str):
        if not string:
            return

        error_message = await self.context.bot.get_text("system.help.ERRORS.COMMAND_NOT_FOUND", self.context,
            emoji=config.EMOJIS.CONTEXT.WARN,
            user=self.context.author.mention,
            command=string
        )
        
        embed = Embed(description=error_message, color=config.COLORS.WARN)
        await self.context.send(embed=embed)

    async def subcommand_not_found(self, command: str, subcommand: str):
        if not command or not subcommand:
            return

        error_message = await self.context.bot.get_text("system.help.ERRORS.SUBCOMMAND_NOT_FOUND", self.context,
            emoji=config.EMOJIS.CONTEXT.WARN,
            user=self.context.author.mention,
            command=command,
            subcommand=subcommand
        )
        
        embed = Embed(description=error_message, color=config.COLORS.WARN)
        await self.context.send(embed=embed)

    async def _add_flag_formatting(self, annotation: FlagConverter, embed: Embed):
        optional: List[str] = [
            f"`--{name}{' on/off' if isinstance(flag.annotation, Status) else ''}`: {flag.description}"
            for name, flag in annotation.get_flags().items()
            if flag.default is not MISSING
        ]

        required: List[str] = [
            f"`--{name}{' on/off' if isinstance(flag.annotation, Status) else ''}`: {flag.description}"
            for name, flag in annotation.get_flags().items()
            if flag.default is MISSING
        ]

        if required:
            embed.add_field(
                name=await self.context.bot.get_text("system.help.COMMAND.FLAGS.REQUIRED", self.context), 
                value="\n".join(required), 
                inline=True
            )

        if optional:
            embed.add_field(
                name=await self.context.bot.get_text("system.help.COMMAND.FLAGS.OPTIONAL", self.context), 
                value="\n".join(optional), 
                inline=True
            )