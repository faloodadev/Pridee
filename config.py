from typing import List, NamedTuple
from os import getenv
from dotenv import load_dotenv

load_dotenv()

class COLORS:
    """
    Changes the colors on context outputs.
    """
    NEUTRAL = 0xCCCCFF
    APPROVE = 0xCCCCFF
    WARN = 0xCCCCFF
    DENY = 0xCCCCFF
    SPOTIFY = 0x1DB954

class AUTHORIZATION:
    """
    API keys for various services.
    """
    FNBR: str = getenv("FNBR_API_KEY", "")
    CLEVER: str = getenv("CLEVER_API_KEY", "")
    WOLFRAM: str = getenv("WOLFRAM_API_KEY", "")
    WEATHER: str = getenv("WEATHER_API_KEY", "")
    OSU: str = getenv("OSU_API_KEY", "")
    LASTFM: list[str] = [
        key for key in getenv("LASTFM_API_KEYS", "").split(",") if key
    ] or []
    SOUNDCLOUD: str = getenv("SOUNDCLOUD_API_KEY", "")
    GEMINI: str = getenv("GEMINI_API_KEY", "")
    KRAKEN: str = getenv("KRAKEN_API_KEY", "")
    FERNET_KEY: str = getenv("FERNET_KEY", "")
    PIPED_API: str = getenv("PIPED_API", "pipedapi.adminforge.de")
    PUBSUB_KEY: str = getenv("PUBSUB_KEY", "")
    IPC_KEY: str = getenv("IPC_KEY", "")
    JEYY_API: str = getenv("JEYY_API_KEY", "")
    OPENAI: str = getenv("OPENAI_API_KEY", "")
    LOVENSE: str = getenv("LOVENSE_API_KEY", "")

class EMOJIS:
    """
    Controls the emojis throughout the bot.
    """

    class STAFF:
        """
        Changes the emojis on staff commands.
        """
        DEVELOPER: str = "<:developer:1325012518006947861>"
        OWNER: str = "<:owner:1325012419587866666>"
        SUPPORT: str = "<:support:1325012723922370601>"
        TRIAL: str = "<:trial:1323255897656397824>"
        MODERATOR: str = "<:mod:1325081613238931457>"
        DONOR: str = "<:donor1:1320054420616249396>"
        INSTANCE: str = "<:donor4:1320428908406902936>"
        STAFF: str = "<:staff:1325012421819236443>"

    class INTERFACE:
        """
        Changes the emojis on the VoiceMaster Panel.
        """
        LOCK: str = "<:lock:1263727069095919698>"
        UNLOCK: str = "<:unlock:1263730907680870435>"
        GHOST: str = "<:hide:1263731781157392396>"
        REVEAL: str = "<:reveal:1263731670121709568>"
        CLAIM: str = "<:claim:1263731873167708232>"
        DISCONNECT: str = "<:hammer:1292838404597354637>"
        ACTIVITY: str = "<:activity:1292838226125656097>"
        INFORMATION: str = "<:information:1263727043967717428>"
        INCREASE: str = "<:increase:1263731093845315654>"
        DECREASE: str = "<:decrease:1263731510239035442>"

    class PAGINATOR:
        """
        Changes the emojis on the paginator.
        """
        NEXT: str = "<:right:1263727130370637995>"
        NAVIGATE: str = "<:filter:1263727034798968893>"
        PREVIOUS: str = "<:left:1263727060078035066>"
        CANCEL: str = "<:deny:1263727013433184347>"

    class AUDIO:
        """
        Changes the emojis on the audio panel.
        """
        SKIP: str = "<:skip:1243011308333564006>"
        RESUME: str = "<:resume:1243011309449252864>"
        REPEAT: str = "<:repeat:1243011309843382285>"
        PREVIOUS: str = "<:previous:1243011310942162990>"
        PAUSE: str = "<:pause:1243011311860842627>"
        QUEUE: str = "<:queue:1243011313006022698>"
        REPEAT_TRACK: str = "<:repeat_track:1243011313660334101>"

    class ANTINUKE:
        """
        Changes the emojis on the Antinuke-Config command.
        """
        ENABLE = "<:enable:1263758811429343232>"
        DISABLE = "<:disable:1263758691858120766>"

    class BADGES:
        """
        Changes the emojis that show on badges.
        """
        HYPESQUAD_BRILLIANCE: str = "<:hypesquad_brillance:1289500479117590548>"
        BOOST: str = "<:booster:1263727083310415885>"
        STAFF: str = "<:staff:1263729127199084645>"
        VERIFIED_BOT_DEVELOPER: str = "<:earlydev:1263727027022860330>"
        SERVER_OWNER: str = "<:owner:1329251274440310834>"
        HYPESQUAD_BRAVERY: str = "<:hypesquad_bravery:1289500873830961279>"
        PARTNER: str = "<:partner:1263727124066340978>"
        HYPESQUAD_BALANCE: str = "<:hypesquad_balance:1289500688052785222>"
        EARLY_SUPPORTER: str = "<:early:1263727021318602783>"
        HYPESQUAD: str = "<:hypesquad:1289501069449236572>"
        BUG_HUNTER_LEVEL_2: str = "<:buggold:1263726960882876456>"
        CERTIFIED_MODERATOR: str = "<:certified_moderator:1289501261640765462>"
        NITRO: str = "<:nitro:1289499927117828106>"
        BUG_HUNTER: str = "<:bugreg:1263726968377966642>"
        ACTIVE_DEVELOPER: str = "<:activedev:1263726943048695828>"

    class CONTEXT:
        """
        Changes the emojis on context.
        """
        APPROVE = "<:approve:1271155661451034666>"
        DENY = "<:deny:1263727013433184347>"
        WARN = "<:warn:1263727178802004021>"
        FILTER = "<:filter:1263727034798968893>"
        LEFT = "<:left:1263727060078035066>"
        RIGHT = "<:right:1263727130370637995>"
        JUUL = "<:juul:1300217541909545000>"
        NO_JUUL = "<:no_juul:1300217551699181588>"
        PING = "<:connection:1300775066933530755>"

    class SOCIAL:
        """
        Changes the emojis on social commands.
        """
        DISCORD = "<:discord:1290120978306695281>"
        GITHUB = "<:github:1289507143887884383>"
        WEBSITE = "<:link:1290119682103316520>"

    class TICKETS:
        """
        Changes the emojis on tickets.
        """
        TRASH = "<:trash:1263727144832602164>"
    
    class ECONOMY:
        """
        Changes the emojis on the economy commands.
        """
        PURPLE_DEVIL = "<:purple_devil:1309072250107854911>"
        WHITE_POWEDER = "<:white_powder:1309072260551675904>"
        OXY = "<:oxy:1309072269565235200>"
        METH = "<:meth:1309072276683100183>"
        SHROOMS = "<:shroom:1309072285264646194>"
        HEROIN = "<:heroin:1309072311047159818>"
        ACID = "<:acid:1309072318684729356>"
        UP = "<:econ_up:1309071103397859398>"
        DOWN = "<:econ_down:1309071092681408553>"

    class SPOTIFY:
        """
        Changes the emojis on the Spotify commands.
        """
        LEFT: str = "<:left_spot:1322093955449487433>"
        RIGHT: str = "<:right_spot:1322094031551070219>"
        BLACK: str = "<:black:1322093844967456769>"
        BLACK_RIGHT: str = "<:blackright:1322093837992333404>"
        WHITE: str = "<:white_spot:1322094107044089877>"
        ICON: str = "<:spotify_cmd:1322094318890254359>"
        LISTENING: str = "<:listening:1322093224688488458>"
        SHUFFLE: str = "<:shuffle:1322093133449789481>"
        REPEAT: str = "<:repeat:1322093145789562902>"
        DEVICE: str = "<:devices:1322093261636108321>"
        NEXT: str = "<:next:1322093204492783657>"
        PREVIOUS: str = "<:previous:1322093173371174987>"
        PAUSE: str = "<:pause:1322093187883466803>"
        VOLUME: str = "<:volume:1322093120053055568>"
        FAVORITE: str = "<:fav:1322094614596947999>"
        REMOVE: str = "<:remove:1322094634163241021>"
        EXPLCIT: str = "<:explicit:1322093240941412386>"
    
    class LOVENSE:
        """
        Changes the emojis on the Lovense commands.
        """
        LOVENSE: str = "<:lovense:1321525243549974539>"
        KEY: str = getenv("LOVENSE_KEY", "")
        IV: str = getenv("LOVENSE_IV", "")

class Database(NamedTuple):
    """PostgreSQL database configuration."""
    DSN: str = getenv("DATABASE_URL", "postgresql://postgres:admin@localhost/evict")
    MIN_SIZE: int = 10
    MAX_SIZE: int = 20
    MAX_QUERIES: int = 50000
    TIMEOUT: float = 60.0
    COMMAND_TIMEOUT: float = 60.0

class REDIS(NamedTuple):
    """Redis configuration."""
    HOST: str = getenv("REDIS_HOST", "localhost")
    PORT: int = int(getenv("REDIS_PORT", "6379"))
    DB: int = int(getenv("REDIS_DB", "0"))
    DSN: str = f"redis://{HOST}:{PORT}/{DB}"

class Monitoring(NamedTuple):
    """OpenTelemetry monitoring configuration."""
    OTLP_ENDPOINT: str = getenv("OTLP_ENDPOINT", "http://localhost:4317")
    SERVICE_NAME: str = getenv("SERVICE_NAME", "evict-bot")
    ENVIRONMENT: str = getenv("ENVIRONMENT", "development")

class Logging(NamedTuple):
    """Logging configuration."""
    LEVEL: str = getenv("LOG_LEVEL", "INFO")
    FORMAT: str = "\x1b[30;46m{process}\033[0m:{levelname:<9} (\x1b[35m{asctime}\033[0m) \x1b[37;3m@\033[0m \x1b[31m{module:<9}\033[0m -> {message}"
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    IGNORED_MODULES: List[str] = [
        "pomice",
        "client",
        "web_log",
        "gateway",
        "launcher",
        "pyppeteer",
        "__init__",
        "_client"
    ]

class Client(NamedTuple):
    """Discord bot client configuration."""
    TOKEN: str = getenv("DISCORD_TOKEN", "")
    PREFIX: str = getenv("BOT_PREFIX", "!")
    DESCRIPTION: str = "Pride Discord Bot"
    OWNER_IDS: List[int] = [
        int(id_) for id_ in getenv("OWNER_IDS", "").split(",") if id_
    ]

class Sharding(NamedTuple):
    """Sharding configuration."""
    CLUSTER_COUNT: int = int(getenv("CLUSTER_COUNT", "2"))
    TOTAL_SHARDS: int = int(getenv("TOTAL_SHARDS", "6"))

class Dask(NamedTuple):
    """Dask configuration."""
    HOST: str = getenv("DASK_HOST", "localhost")
    PORT: int = int(getenv("DASK_PORT", "8787")) 
    ALLOW_ANONYMOUS: bool = getenv("DASK_ALLOW_ANONYMOUS", "false").lower() == "true"
    USERNAME: str = getenv("DASK_USERNAME", "admin")
    PASSWORD: str = getenv("DASK_PASSWORD", "changeme")

DASK = Dask()

class Cache(NamedTuple):
    """Cache configuration."""
    TTL: int = 300  
    MAX_SIZE: int = 10000

COLORS = COLORS()
EMOJIS = EMOJIS()
DATABASE = Database()
REDIS = REDIS()
MONITORING = Monitoring()
LOGGING = Logging()
CLIENT = Client()
SHARDING = Sharding()
CACHE = Cache()

def validate_config():
    if not CLIENT.TOKEN:
        raise ValueError("Discord token not configured!")
    
    if not CLIENT.OWNER_IDS:
        raise ValueError("No owner IDs configured!")
    
    if not DATABASE.DSN:
        raise ValueError("Database URL not configured!")

validate_config() 