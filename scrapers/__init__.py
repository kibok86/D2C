from .base              import BaseScraper
from .extra_com         import ExtraComScraper
from .news_rss          import NewsScraper
from .fx_rates          import FxRateScraper
from .freight           import load_freight_rates
from .freight_index     import FreightIndexScraper
from .port_status       import PortStatusScraper
from .carrier_schedule  import CarrierScheduleScraper
from .storage           import (
    save_fx_snapshot, get_fx_changes,
    save_freight_index, get_freight_index_history, get_freight_index_change,
)

__all__ = [
    "BaseScraper", "ExtraComScraper", "NewsScraper", "FxRateScraper",
    "load_freight_rates", "FreightIndexScraper",
    "PortStatusScraper", "CarrierScheduleScraper",
    "save_fx_snapshot", "get_fx_changes",
    "save_freight_index", "get_freight_index_history", "get_freight_index_change",
]
from .tv_market import TVMarketScraper
__all__ += ["TVMarketScraper"]
