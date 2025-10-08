import os
from pathlib import Path

from core.data.ticker_fetcher import get_default_tickers

# Base directory for application data in user's cache
APP_NAME = "com.rectifex.GlobalScreener"
CACHE_DIR = Path(os.path.expanduser("~/.cache")) / APP_NAME
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Path for the SQLite database that stores the symbol index
DB_PATH = CACHE_DIR / "symbol_index.sqlite"

# Path for Parquet files caching OHLCV data
PARQUET_CACHE_DIR = CACHE_DIR / "parquet_cache"
PARQUET_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Path for snapshots
SNAPSHOT_DIR = CACHE_DIR / "snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Default list of tickers for the universe sourced from yfinance's comprehensive list
DEFAULT_UNIVERSE = get_default_tickers()
