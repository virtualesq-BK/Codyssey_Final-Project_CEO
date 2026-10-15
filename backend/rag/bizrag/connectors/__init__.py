from .base import ApiError, CheckResult, Connector, Http, Job
from .bok import Bok
from .datagokr import DataGoKr, DataGoKrRest
from .inbox import Inbox
from .kipris import Kipris
from .kosis import Kosis
from .law import Law
from .lawgokr_precedent import LawPrecedent
from .naver import Naver
from .worldbank import WorldBank

REGISTRY = {c.name: c for c in (Naver, Kosis, Bok, Law, LawPrecedent, Kipris, WorldBank, DataGoKr, DataGoKrRest, Inbox)}

__all__ = ["REGISTRY", "ApiError", "CheckResult", "Connector", "Http", "Job"]
