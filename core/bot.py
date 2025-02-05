import time
import asyncio
import psutil
from collections import defaultdict
from typing import Optional, Collection, Dict, Any, cast
from discord.ext import commands
from discord import (
    Intents, AllowedMentions, Activity, ActivityType, 
    Message, User, ClientUser, ChannelType, PartialMessageable,
    Member, Guild, Invite, HTTPException, NotFound, Forbidden, 
    NSFWChannelRequired, Interaction, CheckFailure
)
from datetime import datetime, timezone
from pathlib import Path
import json
from discord.ext.commands import Context
from aiohttp import ClientSession, TCPConnector
from redis.asyncio import Redis
from discord.ext.commands import CooldownMapping, BucketType
from asyncpraw import Reddit as RedditClient
from opentelemetry.trace import Tracer
from multiprocessing import Pool, cpu_count as logical_cpu_count
import os
import glob
import secrets
import importlib
from colorama import Fore
from discord.ext.commands import (
    CommandError, CommandNotFound, DisabledCommand, NotOwner,
    MissingRequiredArgument, MissingRequiredAttachment, BadLiteralArgument,
    FlagError, TooManyFlags, BadFlagArgument,
    MissingRequiredFlag, MissingFlagArgument,
    CommandInvokeError, MaxConcurrencyReached,
    CommandOnCooldown, MemberNotFound, UserNotFound,
    RoleNotFound, ChannelNotFound, BadInviteArgument,
    MessageNotFound, BadUnionArgument, RangeError,
    MissingPermissions
)
from core.database import Database, Settings
from core.cache import cache
from utils.computation import heavy_computation
from utils.monitoring import PerformanceMonitoring

from core.http import MonitoredHTTPClient
from utils.prefix import getprefix
from core.help import EvictHelp
from utils.monitoring import PerformanceMonitoring
from utils.optimization import setup_cpu_optimizations
from core.dask import DaskManager
from utils.tracing import tracer
from utils.logger import log
from core.ipc import ClusterIPC
from core.browser import BrowserHandler
import config
from processors.backup import run_pg_dump, process_bunny_upload
from processors.image_generator import process_image_effect
from processors.guild import (
    process_guild_data,
    process_jail_permissions,
    process_add_role
)
from utils.formatter import plural, format_timespan, human_join
from contextlib import suppress
from wavelink import NodePool
from core.backup import BackupManager

class Evict(commands.AutoShardedBot):
    session: ClientSession
    uptime: datetime
    traceback: Dict[str, Exception]
    global_cooldown: CooldownMapping
    owner_ids: Collection[int]
    database: Database
    redis: Redis
    user: ClientUser
    reddit: RedditClient
    version: str = "b4.0"
    user_agent: str = f"Evict (DISCORD BOT/{version})"
    browser: BrowserHandler
    voice_join_times = {}
    voice_update_task = None
    start_time: float
    system_stats: defaultdict
    process: psutil.Process
    _last_system_check: float
    _is_ready: asyncio.Event
    monitoring: PerformanceMonitoring
    translations: dict
    tracer: Tracer
    api_stats: dict
    _last_stats_cleanup: float
    ipc: ClusterIPC
    dask: DaskManager
    _cleanup_event: asyncio.Event

    def __init__(self, *args, **kwargs):
        self.monitoring = PerformanceMonitoring()
        self.dask = DaskManager()
        self.tracer = tracer.get_tracer(__name__)
        self.translations = {}
        self._load_translations()
        
        super().__init__(
            *args,
            **kwargs,
            intents=Intents(
                guilds=True,
                members=True,
                messages=True,
                reactions=True,
                presences=True,
                moderation=True,
                voice_states=True,
                message_content=True,
                emojis_and_stickers=True,
            ),
            allowed_mentions=AllowedMentions(
                replied_user=False,
                everyone=False,
                roles=False,
                users=True,
            ),
            shard_count=6,
            command_prefix=getprefix,
            help_command=EvictHelp(),
            case_insensitive=True,
            max_messages=1500,
            activity=Activity(
                type=ActivityType.streaming,
                name="🔗 evict.bot/beta",
                url=f"{config.CLIENT.TWITCH_URL}",
            ),
        )
        
        self._init_attributes()
        self._setup_cooldowns()
        self._setup_process_pool()
        
        self.api_stats = defaultdict(lambda: {
            'calls': 0,
            'errors': 0,
            'total_time': 0,
            'rate_limits': 0
        })
        self._last_stats_cleanup = time.time()

        self.help_command.cog = self

        self.browser = BrowserHandler()

    def _init_attributes(self):
        self.traceback = {}
        self.uptime2 = time.time()
        self.embed_build = EmbedScript()
        self.cache = cache(self)
        self.start_time = time.time()
        self.system_stats = defaultdict(list)
        self.process = psutil.Process()
        self._last_system_check = 0
        self.command_stats = defaultdict(lambda: {'calls': 0, 'total_time': 0})
        self._is_ready = asyncio.Event()
        self._cleanup_event = asyncio.Event()

    def _setup_cooldowns(self):
        """Setup advanced cooldown and rate-limit system."""
        self.global_cooldown = CooldownMapping.from_cooldown(2, 3, BucketType.user)
        self.add_check(self.check_global_cooldown)
        
        self.guild_ratelimits = {
            '10s': CooldownMapping.from_cooldown(
                config.RATELIMITS.PER_10S, 
                10, 
                BucketType.guild
            ),
            '30s': CooldownMapping.from_cooldown(
                config.RATELIMITS.PER_30S, 
                30, 
                BucketType.guild
            ),
            '1m': CooldownMapping.from_cooldown(
                config.RATELIMITS.PER_1M, 
                60, 
                BucketType.guild
            )
        }
        
        self.channel_ratelimit = CooldownMapping.from_cooldown(
            config.RATELIMITS.PER_CHANNEL, 
            5, 
            BucketType.channel
        )
        
        self.heavy_command_cooldown = CooldownMapping.from_cooldown(
            1, 30, BucketType.user
        )
        
        self.violation_tracker = defaultdict(lambda: {
            'count': 0,
            'last_violation': 0,
            'cooldown_multiplier': 1
        })
        
        self.loop.create_task(self._cleanup_violations())

    def _setup_process_pool(self):
        self.process_pool = Pool(
            processes=min(4, logical_cpu_count),
            maxtasksperchild=100  
        )

    @property
    def db(self) -> Database:
        return self.database

    @property
    def owner(self) -> User:
        return self.get_user(self.owner_ids[0])

    def get_message(self, message_id: int) -> Optional[Message]:
        return self._connection._get_message(message_id)

    async def get_or_fetch_user(self, user_id: int) -> User:
        return self.get_user(user_id) or await self.fetch_user(user_id)

    async def setup_hook(self) -> None:
        """Initialize bot services and connections."""
        log.info("Starting setup hook...")
        try:
            setup_cpu_optimizations()
            
            self.monitoring.setup("http://localhost:4317")
            
            await self.dask.setup()
            
            await self._init_services()
            await self._init_monitoring()
            await self._init_voice_system()
            
            self.ipc = ClusterIPC(self, self.cluster_id)
            await self.ipc.start()
            
            self.loop.create_task(self._heartbeat_task())
            
            self.ipc.add_handler("reload_cog", self._handle_reload_cog)
            
            await self.browser.init()
            
            log.info("Setup complete!")
        except Exception as e:
            log.error(f"Error in setup_hook: {e}", exc_info=True)
            raise

    PerformanceMonitoring().trace_method
    async def _init_services(self) -> None:
        """Initialize core services."""
        self.session = ClientSession(
            headers={"User-Agent": self.user_agent},
            connector=TCPConnector(ssl=False),
        )
        self._http = MonitoredHTTPClient(self.http._HTTPClient__session, bot=self)
        
        # self.add_dynamic_items(DynamicRoleButton)
        # self.add_view(DeleteTicket())
        
        self.database = await Database.connect()
        self.redis = await Redis.from_url()
        
        await self.browser.init()

    PerformanceMonitoring().trace_method
    async def on_command(self, ctx: Context) -> None:
        """Custom on_command method that logs command usage."""
        if not (ctx.guild and ctx.command):
            if not ctx.guild:
                return

            custom_command = await self.db.fetchrow(
                """
                SELECT word 
                FROM stats.custom_commands 
                WHERE guild_id = $1 AND command = $2
                """,
                ctx.guild.id,
                ctx.invoked_with.lower()
            )
            
            if not custom_command:
                return
                
            ctx.command = type('CustomCommand', (), {
                'qualified_name': f"wordstats_{ctx.invoked_with}",
                'cog_name': "Utility"
            })

        await self._track_command_usage(ctx)
        
    async def _track_command_usage(self, ctx: Context) -> None:
        """Track command usage statistics."""
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await asyncio.gather(
                    conn.execute(
                        """
                        INSERT INTO statistics.daily 
                            (guild_id, date, member_id, messages_sent)
                        VALUES 
                            ($1, CURRENT_DATE, $2, 0)
                        ON CONFLICT (guild_id, date, member_id) DO UPDATE SET 
                            messages_sent = statistics.daily.messages_sent
                        """,
                        ctx.guild.id,
                        ctx.author.id
                    ),
                    conn.execute(
                        """
                        INSERT INTO invoke_history.commands 
                        (guild_id, user_id, command_name, category, timestamp)
                        VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                        """,
                        ctx.guild.id,
                        ctx.author.id,
                        ctx.command.qualified_name,
                        ctx.command.cog_name or "No Category",
                    )
                )

        start_time = time.time()
        command_name = ctx.command.qualified_name
        
        try:
            log.info(
                "Command execution: %s",
                {
                    "user": ctx.author.name,
                    "user_id": ctx.author.id,
                    "command": command_name,
                    "guild": ctx.guild.name,
                    "guild_id": ctx.guild.id
                }
            )
        finally:
            elapsed = time.time() - start_time
            self.command_stats[command_name]['calls'] += 1
            self.command_stats[command_name]['total_time'] += elapsed

    async def on_shard_ready(self, shard_id: int) -> None:
        """Handle shard ready event."""
        log.info(f"Shard {shard_id} is ready, starting post-connection setup...")
        try:
            log.info(
                f"Shard ID {Fore.LIGHTGREEN_EX}{shard_id}{Fore.RESET} has {Fore.LIGHTGREEN_EX}spawned{Fore.RESET}."
            )
            
            if shard_id == self.shard_count - 1:
                log.info("All shards connected, waiting for full ready state...")
                await self._post_shards_ready()
                
        except Exception as e:
            log.error(f"Error in on_shard_ready for shard {shard_id}: {e}", exc_info=True)

    async def _post_shards_ready(self) -> None:
        """Initialize services after all shards are ready."""
        await self.connect_nodes()
        await self.load_extensions()
        await self.load_patches()

    async def on_shard_resumed(self, shard_id: int) -> None:
        """Handle shard resume event."""
        log.info(
            f"Shard ID {Fore.LIGHTGREEN_EX}{shard_id}{Fore.RESET} has {Fore.LIGHTYELLOW_EX}resumed{Fore.RESET}."
        )

    async def _init_monitoring(self) -> None:
        """Initialize monitoring systems."""
        self.start_time = time.time()
        self.system_stats = defaultdict(list)
        self.process = psutil.Process()
        self._last_system_check = 0
        self.command_stats = defaultdict(lambda: {
            'calls': 0,
            'total_time': 0.0,
            'last_reset': time.time()
        })

    async def _init_voice_system(self) -> None:
        """Initialize voice system and backup manager."""
        self.voice_update_task = self.loop.create_task(
            self.update_voice_times(),
            name="voice_update_task"
        )
        self.backup_manager = BackupManager(self)
        self.backup_task = self.loop.create_task(
            self._backup_task(),
            name="backup_task"
        )
        
        self.voice_join_times.update({
            member.id: time.time()
            for guild in self.guilds
            for vc in guild.voice_channels
            for member in vc.members
            if not member.bot
        })

    async def connect_nodes(self) -> None:
        """Connect to Lavalink nodes."""
        for _ in range(config.LAVALINK.NODE_COUNT):
            identifier = "evict"
            try:
                await NodePool().create_node(
                    bot=self,
                    host="127.0.0.1",
                    port=config.LAVALINK.PORT,
                    password=config.LAVALINK.PASSWORD,
                    secure=False,
                    identifier=identifier,
                    spotify_client_id=config.AUTHORIZATION.SPOTIFY.CLIENT_ID,
                    spotify_client_secret=config.AUTHORIZATION.SPOTIFY.CLIENT_SECRET,
                )
                log.info(f"Successfully connected to node {identifier}")
            except Exception as e:
                log.error(f"Failed to connect to node {identifier}: {e}")

    async def load_extensions(self) -> None:
        """Load all extensions."""
        await self.load_extension("jishaku")
        for feature in Path("cogs").iterdir():
            if feature.is_dir() and (feature / "__init__.py").is_file():
                try:
                    await self.load_extension(".".join(feature.parts))
                except Exception as exc:
                    log.exception(f"Failed to load extension {feature.name}.", exc_info=exc)

    async def load_patches(self) -> None:
        """Load all patches."""
        for module in glob.glob("managers/patches/**/*.py", recursive=True):
            if module.endswith("__init__.py"):
                continue
            module_name = (
                module.replace(os.path.sep, ".").replace("/", ".").replace(".py", "")
            )
            try:
                importlib.import_module(module_name)
                log.info(f"Patched: {module}")
            except (ModuleNotFoundError, ImportError) as e:
                log.error(f"Error importing {module_name}: {e}")

    async def process_heavy_task(self, *args):
        """Process a heavy computation task"""
        with self.monitoring.tracer.start_as_current_span("heavy_task") as span:
            start_time = time.time()
            try:
                result = await self.dask.submit_task(heavy_computation, *args)
                self.monitoring.record_operation("heavy_task", time.time() - start_time)
                return result
            except Exception as e:
                self.monitoring.record_operation("heavy_task", time.time() - start_time, error=True)
                span.record_exception(e)
                raise

    async def close(self) -> None:
        """Cleanup and close all resources."""
        try:
            await self.monitoring.shutdown()
            
            await self.db.close()
            
            await self.redis.close()
            
            if hasattr(self, 'session'):
                await self.session.close()
            
            if hasattr(self, 'dask_client'):
                await self.dask_client.close()
            
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            [task.cancel() for task in tasks]
            await asyncio.gather(*tasks, return_exceptions=True)
            
        finally:
            await super().close()

    async def log_traceback(self, ctx: Context, exc: Exception) -> Message:
        """Store an Exception in memory for future reference."""
        with self.monitoring.tracer.start_as_current_span("log_traceback") as span:
            span.set_attribute("command", ctx.command.qualified_name)
            span.record_exception(exc)
            
            log.exception(
                "Unexpected exception occurred in %s.",
                ctx.command.qualified_name,
                exc_info=exc,
            )

            key = secrets.token_urlsafe(54)
            self.traceback[key] = exc
            
            self.monitoring.record_operation(
                f"error_{ctx.command.qualified_name}",
                0,
                error=True
            )

            return await ctx.warn(
                self.get_text("system.errors.COMMAND.EXCEPTION", 
                    command=ctx.command.qualified_name),
                content=f"`{key}`",
            )

    async def on_command_error(self, ctx: Context, exc: CommandError) -> Any:
        """Handle command errors with detailed error tracking."""
        with self.monitoring.tracer.start_as_current_span("command_error") as span:
            span.set_attribute("command", ctx.command.qualified_name if ctx.command else "unknown")
            span.set_attribute("error_type", exc.__class__.__name__)
            
            if not ctx.channel:
                return
                
            if not ctx.guild:
                can_send = True
            else:
                can_send = (
                    ctx.channel.permissions_for(ctx.guild.me).send_messages
                    and ctx.channel.permissions_for(ctx.guild.me).embed_links
                )

            if not can_send:
                return

            if isinstance(exc, (CommandNotFound, DisabledCommand, NotOwner)):
                return

            elif isinstance(exc, (MissingRequiredArgument, MissingRequiredAttachment, BadLiteralArgument)):
                return await ctx.send_help(ctx.command)

            elif isinstance(exc, TagScriptError):
                if isinstance(exc, EmbedParseError):
                    return await ctx.warn(
                        self.get_text("system.errors.COMMAND.SCRIPT_ERROR"),
                        *exc.args,
                    )

            elif isinstance(exc, FlagError):
                if isinstance(exc, TooManyFlags):
                    return await ctx.warn(
                        self.get_text("system.errors.COMMAND.FLAG.DUPLICATE",
                            flag_name=exc.flag.name)
                    )

                elif isinstance(exc, BadFlagArgument):
                    try:
                        annotation = exc.flag.annotation.__name__
                    except AttributeError:
                        annotation = exc.flag.annotation.__class__.__name__

                    msg = self.get_text("system.errors.COMMAND.FLAG.CAST_ERROR",
                        flag_name=exc.flag.name,
                        annotation=annotation)
                    
                    if annotation == "Status":
                        msg = [msg, self.get_text("system.errors.COMMAND.FLAG.STATUS_HINT")]
                    
                    return await ctx.warn(*msg)

                elif isinstance(exc, MissingRequiredFlag):
                    return await ctx.warn(
                        self.bot.get_text("system.errors.COMMAND.FLAG.MISSING_REQUIRED",
                            flag_name=exc.flag.name)
                    )

                elif isinstance(exc, MissingFlagArgument):
                    return await ctx.warn(
                        self.get_text("system.errors.COMMAND.FLAG.MISSING_VALUE",
                            flag_name=exc.flag.name)
                    )

            elif isinstance(exc, CommandInvokeError):
                return await ctx.warn(exc.original)

            elif isinstance(exc, MaxConcurrencyReached):
                if ctx.command.qualified_name in ("lastfm set", "lastfm index"):
                    return

                return await ctx.warn(
                    self.get_text("system.errors.CONCURRENCY.MAX_CONCURRENT",
                        number=plural(exc.number),
                        time="time",
                        per=exc.per.name),
                    delete_after=5,
                )

            elif isinstance(exc, CommandOnCooldown):
                if exc.retry_after > 30:
                    return await ctx.warn(
                        self.get_text("system.errors.CONCURRENCY.COOLDOWN.MESSAGE"),
                        self.get_text("system.errors.CONCURRENCY.COOLDOWN.RETRY",
                            time=format_timespan(exc.retry_after))
                    )

                return await ctx.message.add_reaction("⏰")

            elif isinstance(exc, BadUnionArgument):
                if exc.converters == (Member, User):
                    return await ctx.warn(
                        self.get_text("system.errors.SEARCH.MEMBER_USER",
                            param=exc.param.name,
                            argument=ctx.current_argument),
                        self.get_text("system.errors.SEARCH.USER_ID_HINT")
                    )

                elif exc.converters == (Guild, Invite):
                    return await ctx.warn(
                        self.get_text("system.errors.SEARCH.SERVER",
                            argument=ctx.current_argument)
                    )

                else:
                    return await ctx.warn(
                        self.get_text("system.errors.SEARCH.CASTING",
                            param=exc.param.name,
                            converters=human_join([f'`{c.__name__}`' for c in exc.converters]))
                    )

            elif isinstance(exc, (MemberNotFound, UserNotFound, RoleNotFound, 
                               ChannelNotFound, BadInviteArgument, MessageNotFound)):
                error_types = {
                    MemberNotFound: "MEMBER",
                    UserNotFound: "USER",
                    RoleNotFound: "ROLE",
                    ChannelNotFound: "CHANNEL",
                    BadInviteArgument: "INVITE",
                    MessageNotFound: "MESSAGE"
                }
                return await ctx.warn(
                    self.get_text(f"system.errors.SEARCH.NOT_FOUND.{error_types[type(exc)]}",
                        argument=getattr(exc, 'argument', ''))
                )

            elif isinstance(exc, RangeError):
                label = ""
                if exc.minimum is None and exc.maximum is not None:
                    label = f"no more than `{exc.maximum}`"
                elif exc.minimum is not None and exc.maximum is None:
                    label = f"no less than `{exc.minimum}`"
                elif exc.maximum is not None and exc.minimum is not None:
                    label = f"between `{exc.minimum}` and `{exc.maximum}`"

                translation_key = "RANGE_CHARS" if label and isinstance(exc.value, str) else "RANGE"
                return await ctx.warn(
                    self.get_text(f"system.errors.VALIDATION.{translation_key}",
                        label=label)
                )

            elif isinstance(exc, MissingPermissions):
                permissions = human_join(
                    [f"`{permission}`" for permission in exc.missing_permissions],
                    final="and"
                )
                return await ctx.warn(
                    self.get_text("system.errors.PERMISSIONS.USER_MISSING",
                        permissions=permissions,
                        plural="s" if len(exc.missing_permissions) > 1 else "")
                )
            
            elif isinstance(exc, NSFWChannelRequired):
                return await ctx.warn(
                    self.get_text("system.errors.PERMISSIONS.NSFW_REQUIRED")
                )

            elif isinstance(exc, CommandError):
                if isinstance(exc, (HTTPException, NotFound)) and not isinstance(exc, (CheckFailure, Forbidden)):
                    if "Unknown Channel" in exc.text:
                        return
                    return await ctx.warn(exc.text.capitalize())
                
                if isinstance(exc, (Forbidden, CommandInvokeError)):
                    error = exc.original if isinstance(exc, CommandInvokeError) else exc
                    
                    if isinstance(error, Forbidden):
                        perms = ctx.guild.me.guild_permissions
                        missing_perms = []
                        
                        if not perms.manage_channels:
                            missing_perms.append('`manage_channels`')
                        if not perms.manage_roles:
                            missing_perms.append('`manage_roles`')
                            
                        if missing_perms:
                            error_msg = self.get_text("system.errors.PERMISSIONS.BOT_MISSING",
                                permissions=', '.join(missing_perms))
                        else:
                            error_msg = self.get_text("system.errors.PERMISSIONS.BOT_MISSING_GENERIC")
                        
                        return await ctx.warn(
                            error_msg,
                            f"Error: {str(error)}"
                        )
                        
                    return await ctx.warn(str(error))

                origin = getattr(exc, "original", exc)
                with suppress(TypeError):
                    if any(
                        forbidden in origin.args[-1]
                        for forbidden in (
                            "global check",
                            "check functions",
                            "Unknown Channel",
                        )
                    ):
                        return

                return await ctx.warn(*origin.args)

            else:
                return await ctx.send_help(ctx.command)

    async def get_context(self, origin: Message | Interaction, /, *, cls=Context) -> Context:
        """Get context with additional attributes."""
        with self.monitoring.tracer.start_as_current_span("get_context") as span:
            context = await super().get_context(origin, cls=cls)
            if context.guild:
                context.settings = await Settings.fetch(self, context.guild)
                span.set_attribute("guild_id", str(context.guild.id))
            else:
                context.settings = None
            return context

    async def check_global_cooldown(self, ctx: Context) -> bool:
        """Check global cooldown with monitoring."""
        with self.monitoring.tracer.start_as_current_span("check_global_cooldown") as span:
            span.set_attribute("user_id", str(ctx.author.id))
            
            if ctx.author.id in self.owner_ids:
                return True

            bucket = self.global_cooldown.get_bucket(ctx.message)
            if bucket:
                retry_after = bucket.update_rate_limit()
                if retry_after:
                    span.set_attribute("cooldown_retry_after", retry_after)
                    raise CommandOnCooldown(bucket, retry_after, BucketType.user)

            return True

    async def process_commands(self, message: Message) -> None:
        """Process commands with monitoring."""
        with self.monitoring.tracer.start_as_current_span("process_commands") as span:
            if message.author.bot:
                return

            blacklisted = await self._check_blacklist(message.author.id)
            if blacklisted:
                return

            if not await self._check_channel_permissions(message):
                return

            ctx = await self.get_context(message)
            span.set_attribute("command", ctx.command.qualified_name if ctx.command else "unknown")

            if not ctx.valid and message.content.startswith(ctx.clean_prefix):
                if await self._process_custom_command(ctx):
                    return

            if self._should_discard_command(ctx, message):
                log.warning(
                    "Discarded command message (ID: %s) with PartialMessageable channel: %r.",
                    message.id,
                    message.channel,
                )
                return

            await self.invoke(ctx)

            if not ctx.valid:
                self.dispatch("message_without_command", ctx)

    async def on_message(self, message: Message) -> None:
        """Handle messages with statistics tracking."""
        with self.monitoring.tracer.start_as_current_span("on_message") as span:
            if message.guild and not message.author.bot:
                span.set_attribute("guild_id", str(message.guild.id))
                
                if not await self.check_guild_ratelimit(message):
                    return
                
                await self._update_message_statistics(message)

            if self._should_dispatch_boost(message):
                self.dispatch("member_boost", message.author)

            return await super().on_message(message)

    async def on_message_edit(self, before: Message, after: Message) -> None:
        """Handle message edits with monitoring."""
        with self.monitoring.tracer.start_as_current_span("on_message_edit"):
            self.dispatch("member_activity", after.channel, after.author)
            if before.content == after.content:
                return

            if after.guild and not after.author.bot:
                if not await self.check_guild_ratelimit(after):
                    return

            return await self.process_commands(after)

    async def update_voice_times(self):
        """Update voice statistics with monitoring."""
        await self.wait_until_ready()
        while not self.is_closed():
            with self.monitoring.tracer.start_as_current_span("update_voice_times"):
                try:
                    current_time = time.time()
                    stats = await self._collect_voice_statistics(current_time)
                    if stats:
                        await self._update_voice_database(stats)
                except Exception as e:
                    log.error(f"Error updating voice times: {e}")
                finally:
                    await asyncio.sleep(30)

    async def update_system_stats(self):
        """Update system statistics with monitoring."""
        with self.monitoring.tracer.start_as_current_span("update_system_stats"):
            current_time = time.time()
            if current_time - self._last_system_check < 60:
                return

            try:
                stats = await self._collect_system_stats(current_time)
                self._update_system_metrics(stats)
                self._last_system_check = current_time
            except Exception as e:
                log.error(f"Failed to update system stats: {e}")

    async def _backup_task(self) -> None:
        """Run periodic backups with monitoring."""
        await self.wait_until_ready()
        while not self.is_closed():
            with self.monitoring.tracer.start_as_current_span("backup_task"):
                try:
                    next_run = self._calculate_next_backup_time()
                    await asyncio.sleep((next_run - datetime.now(timezone.utc)).total_seconds())
                    
                    success = await self.dask.submit_task(
                        self.backup_manager.run_backup
                    )
                    
                    if success:
                        log.info("8-hour backup completed successfully")
                    else:
                        log.error("8-hour backup failed")
                        
                except Exception as e:
                    log.error(f"Error in backup task: {e}")
                    await asyncio.sleep(300)

    async def _check_blacklist(self, user_id: int) -> bool:
        """Check if user is blacklisted."""
        return cast(
            bool,
            await self.db.fetchval(
                "SELECT EXISTS(SELECT 1 FROM blacklist WHERE user_id = $1)",
                user_id,
            ),
        )

    async def _check_channel_permissions(self, message: Message) -> bool:
        """Check channel permissions."""
        if not message.guild:
            return True
            
        channel = message.channel
        permissions = channel.permissions_for(message.guild.me)
        return (
            permissions.send_messages
            and permissions.embed_links
            and permissions.attach_files
        )

    def _should_discard_command(self, ctx: Context, message: Message) -> bool:
        """Check if command should be discarded."""
        return (
            ctx.invoked_with
            and isinstance(message.channel, PartialMessageable)
            and message.channel.type != ChannelType.private
        )

    async def _collect_system_stats(self, current_time: float) -> dict:
        """Collect system statistics."""
        return {
            'timestamp': current_time,
            'cpu_percent': self.process.cpu_percent(),
            'memory_percent': self.process.memory_percent(),
            'memory_rss': self.process.memory_info().rss,
            'threads': self.process.num_threads(),
            'handles': self.process.num_handles() if hasattr(self.process, 'num_handles') else 0,
            'commands_rate': len(self._connection._commands) / (current_time - self.start_time)
        }

    def _update_system_metrics(self, stats: dict):
        """Update system metrics."""
        self.system_stats['metrics'].append(stats)
        while len(self.system_stats['metrics']) > 60:
            self.system_stats['metrics'].pop(0)

    def _load_translations(self):
        """Load all translation files."""
        with self.monitoring.tracer.start_as_current_span("load_translations") as span:
            langs_dir = Path("langs")
            for lang_dir in langs_dir.iterdir():
                if not lang_dir.is_dir():
                    continue
                    
                lang_code = lang_dir.name
                self.translations[lang_code] = {}
                
                for category_dir in lang_dir.iterdir():
                    if not category_dir.is_dir():
                        continue
                        
                    category = category_dir.name
                    self.translations[lang_code][category] = {}
                    
                    for json_file in category_dir.glob("*.json"):
                        try:
                            with json_file.open(encoding='utf-8') as f:
                                self.translations[lang_code][category].update(json.load(f))
                        except Exception as e:
                            log.error(f"Error loading translation file {json_file}: {e}")
                            
            span.set_attribute("loaded_languages", len(self.translations))

    def get_text(self, lang_code: str, category: str, key: str, **kwargs) -> str:
        """Get translated text with parameter substitution."""
        try:
            text = self.translations[lang_code][category][key]
            return text.format(**kwargs) if kwargs else text
        except KeyError:
            log.warning(f"Missing translation: {lang_code}/{category}/{key}")
            return f"Missing translation: {key}"

    async def process_image(self, buffer: bytes, effect_type: str, **kwargs) -> Any:
        """Process image effects using process pool."""
        with self.monitoring.tracer.start_as_current_span("process_image") as span:
            span.set_attribute("effect_type", effect_type)
            try:
                return await self.dask.submit_pool_task(
                    process_image_effect,
                    buffer,
                    effect_type,
                    **kwargs
                )
            except Exception as e:
                log.error(f"Image processing error: {e}")
                span.record_exception(e)
                raise

    async def process_data(self, process_type: str, *args, **kwargs) -> Any:
        """Process data tasks using process pool."""
        with self.monitoring.tracer.start_as_current_span("process_data") as span:
            span.set_attribute("process_type", process_type)
            
            processors_map = {
                'guild_data': process_guild_data,
                'jail_permissions': process_jail_permissions,
                'add_role': process_add_role,
                'upload_bunny': process_bunny_upload
            }
            
            try:
                processor = processors_map[process_type]
                return await self.dask.submit_pool_task(
                    processor,
                    *args,
                    **kwargs
                )
            except Exception as e:
                log.error(f"Data processing error: {e}")
                span.record_exception(e)
                raise

    async def process_backup(self, command: str) -> Any:
        """Process backup tasks using process pool."""
        with self.monitoring.tracer.start_as_current_span("process_backup") as span:
            try:
                result = await self.dask.submit_pool_task(
                    run_pg_dump,
                    command
                )
                return result
            except Exception as e:
                log.error(f"Backup processing error: {e}")
                span.record_exception(e)
                raise
            finally:
                if hasattr(self, 'process_pool'):
                    self.process_pool._maintain_pool()

    async def _heartbeat_task(self):
        while True:
            await self.ipc.heartbeat()
            await asyncio.sleep(20)

    PerformanceMonitoring().trace_method
    async def check_ratelimit(self, ctx: Context) -> bool:
        """
        Check all rate limits and update violation tracking.
        Returns True if allowed, False if rate limited.
        """
        current_time = time.time()
        
        for duration, cooldown in self.guild_ratelimits.items():
            bucket = cooldown.get_bucket(ctx.message)
            if bucket and bucket.update_rate_limit(current_time):
                guild_violations = self.violation_tracker[ctx.guild.id]
                guild_violations['count'] += 1
                guild_violations['last_violation'] = current_time
                
                if guild_violations['count'] > 5:
                    guild_violations['cooldown_multiplier'] = min(
                        guild_violations['cooldown_multiplier'] * 2,
                        10 
                    )
                    
                await ctx.send(
                    f"This guild is being rate limited. Try again in {duration}.",
                    delete_after=5
                )
                return False
        
        if bucket := self.channel_ratelimit.get_bucket(ctx.message):
            if bucket.update_rate_limit(current_time):
                await ctx.send("This channel is being rate limited.", delete_after=5)
                return False
                
        if ctx.command.qualified_name in config.HEAVY_COMMANDS:
            if bucket := self.heavy_command_cooldown.get_bucket(ctx.message):
                if bucket.update_rate_limit(current_time):
                    await ctx.send(
                        f"This command has a 30s cooldown. Please wait.",
                        delete_after=5
                    )
                    return False
        
        return True

    async def _cleanup_violations(self):
        """Periodically clean up old violation records."""
        while not self.is_closed():
            try:
                current_time = time.time()
                async with self.monitoring.tracer.start_as_current_span("cleanup_violations"):
                    for guild_id, data in list(self.violation_tracker.items()):
                        if current_time - data['last_violation'] > 3600:
                            data['count'] = max(0, data['count'] - 1)
                            data['cooldown_multiplier'] = max(1, data['cooldown_multiplier'] / 2)
                            
                        if data['count'] == 0:
                            del self.violation_tracker[guild_id]
                
                try:
                    await asyncio.wait_for(
                        self._cleanup_event.wait(),
                        timeout=300
                    )
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                log.error(f"Error in violation cleanup: {e}")
                await asyncio.sleep(60)  