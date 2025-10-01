import pandas as pd
import os
import logging
from pathlib import Path

from core.config import PARQUET_CACHE_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CacheService:
    """Manages reading from and writing to the Parquet cache for OHLCV data."""

    def __init__(self, cache_dir: Path = PARQUET_CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_filepath(self, symbol: str) -> Path:
        """Constructs the cache file path for a given symbol."""
        return self.cache_dir / f"{symbol.lower()}.parquet"

    def save_ohlcv(self, symbol: str, df: pd.DataFrame):
        """
        Saves a DataFrame of OHLCV data to a Parquet file atomically.

        Args:
            symbol: The stock ticker symbol.
            df: The pandas DataFrame to save.
        """
        if not isinstance(df, pd.DataFrame) or df.empty:
            logging.warning(f"Attempted to save empty or invalid data for {symbol}. Skipping.")
            return

        filepath = self._get_cache_filepath(symbol)
        temp_filepath = filepath.with_suffix('.tmp')

        try:
            # Write to a temporary file first
            df.to_parquet(temp_filepath, engine='pyarrow')
            # Atomically move/rename the file to its final destination
            os.rename(temp_filepath, filepath)
            logging.info(f"Successfully cached OHLCV data for {symbol} at {filepath}")
        except Exception as e:
            logging.error(f"Failed to save cache for {symbol}: {e}")
            # Clean up the temporary file if it exists
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)

    def load_ohlcv(self, symbol: str) -> pd.DataFrame | None:
        """
        Loads OHLCV data from the Parquet cache for a given symbol.

        Args:
            symbol: The stock ticker symbol.

        Returns:
            A pandas DataFrame with the cached data, or None if not found.
        """
        filepath = self._get_cache_filepath(symbol)
        if not filepath.exists():
            logging.info(f"No cache found for {symbol} at {filepath}")
            return None

        try:
            df = pd.read_parquet(filepath, engine='pyarrow')
            logging.info(f"Loaded OHLCV data for {symbol} from cache.")
            return df
        except Exception as e:
            logging.error(f"Failed to load cache for {symbol}: {e}")
            return None

    def get_cache_age_days(self, symbol: str) -> float | None:
        """
        Calculates the age of the cache file for a symbol in days.

        Returns:
            The age in days, or None if the cache does not exist.
        """
        filepath = self._get_cache_filepath(symbol)
        if not filepath.exists():
            return None

        last_modified_time = filepath.stat().st_mtime
        return (pd.Timestamp.now().timestamp() - last_modified_time) / (24 * 3600)