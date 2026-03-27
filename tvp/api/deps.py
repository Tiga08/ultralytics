from functools import lru_cache
from core.engine import TvpEngine


@lru_cache(maxsize=1)
def get_engine() -> TvpEngine:
    return TvpEngine()
