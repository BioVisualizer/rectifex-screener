import os
from pathlib import Path

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

# Default list of tickers for the universe (can be expanded later)
DEFAULT_UNIVERSE = [
    "AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "JPM", "V"
]