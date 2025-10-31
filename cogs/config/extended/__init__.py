from utils.tools import CompositeMetaClass

from .backup import Backup
from .boosterrole import BoosterRole
from .command import CommandManagement
from .disboard import Disboard
from .gallery import Gallery
from .logging import Logging
from .publisher import Publisher
from .roles import Roles
from .statistics import Statistics
from .sticky import Sticky
from .thread import Thread
from .ticket import Ticket
from .timer import Timer
from .confess import Confess
from .level import Level
from .whitelist import Whitelist
from .suggest import Suggest
from .invites import Invites
from .joindm import JoinDM
from .lovense import Lovense
from .appeal import Appeal
from .porn import Porn
from .verification import Verification

class Extended(
    Verification,
    Appeal,
    Lovense,
    Suggest,
    Roles,
    Timer,
    Ticket,
    Level,
    Backup,
    Sticky,
    Thread,
    Gallery,
    Logging,
    Disboard,
    Publisher,
    Whitelist,
    Statistics,
    BoosterRole,
    CommandManagement,
    Invites,
    JoinDM,
    Porn,
    Confess,
    metaclass=CompositeMetaClass,
):
    """
    Join all extended config cogs into one.
    """
