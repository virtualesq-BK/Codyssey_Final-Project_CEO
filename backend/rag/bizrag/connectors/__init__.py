from .base import ApiError, CheckResult, Connector, Http, Job
from .datagokr import DataGoKr, DataGoKrRest
from .inbox import Inbox
from .kipris import Kipris
from .kosis import Kosis
from .law import Law
from .naver import Naver
from .worldbank import WorldBank

REGISTRY = {c.name: c for c in (Naver, Kosis, Law, Kipris, WorldBank, DataGoKr, DataGoKrRest, Inbox)}

__all__ = ["REGISTRY", "ApiError", "CheckResult", "Connector", "Http", "Job"]
