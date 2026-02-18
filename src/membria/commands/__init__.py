"""Commands module."""

from membria.commands.daemon import daemon_app
from membria.commands.config import config_app
from membria.commands.decisions import decisions_app
from membria.commands.engrams import engrams_app
from membria.commands.stats import stats_app
from membria.commands.calibration import calibration_app
from membria.commands.extractor import extractor_app
from membria.commands.safety import safety_app
from membria.commands.db import app as db_app
from membria.commands.antipattern import app as antipattern_app
from membria.commands.outcomes import app as outcomes_app
from membria.commands.webhook import app as webhook_app
from membria.commands.graph_agents import app as graph_agents_app
from membria.commands.kb import app as kb_app
from membria.commands.squad import app as squad_app
from membria.commands.session import session_app

__all__ = [
    "daemon_app",
    "config_app",
    "decisions_app",
    "engrams_app",
    "stats_app",
    "calibration_app",
    "extractor_app",
    "safety_app",
    "db_app",
    "antipattern_app",
    "outcomes_app",
    "webhook_app",
    "graph_agents_app",
    "kb_app",
    "squad_app",
    "session_app",
]
