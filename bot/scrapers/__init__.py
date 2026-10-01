from .immoscout24 import ImmoScout24
from .immowelt import Immowelt
from .kleinanzeigen import Kleinanzeigen
from .volksheimstaette import Volksheimstaette
from .vonovia import Vonovia
from .wg_eg import WgEg
from .wg_gesucht import WgGesucht

ALL_SCRAPERS = {cls.name: cls for cls in [
    Kleinanzeigen,
    ImmoScout24,
    Immowelt,
    WgGesucht,
    Volksheimstaette,
    WgEg,
    Vonovia,
]}
