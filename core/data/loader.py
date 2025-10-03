import yfinance as yf
import pandas as pd
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_live_ohlcv(symbol: str, period: str = "max", interval: str = "1d", retries: int = 3, backoff_factor: float = 0.8) -> pd.DataFrame:
    """
    Fetches live OHLCV data from yfinance with a robust retry mechanism.

    Args:
        symbol: The stock ticker symbol.
        period: The period of data to fetch (e.g., "1d", "5d", "1mo", "1y", "max").
        interval: The data interval (e.g., "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo").
        retries: The number of times to retry on failure.
        backoff_factor: The factor by which to increase the wait time between retries.

    Returns:
        A pandas DataFrame with the OHLCV data.

    Raises:
        IOError: If fetching fails after all retries.
    """
    ticker = yf.Ticker(symbol)
    for i in range(retries):
        try:
            # Set auto_adjust=False to prevent column names from being lowercased.
            # This ensures 'Open', 'High', 'Low', 'Close' are preserved for mplfinance.
            df = ticker.history(period=period, interval=interval, auto_adjust=False)
            if df.empty:
                raise ValueError(f"No data found for symbol {symbol}")

            # Keep only the essential columns
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

            # Ensure the index is a DatetimeIndex
            df.index = pd.to_datetime(df.index)
            return df
        except Exception as e:
            wait_time = backoff_factor * (2 ** i)
            logging.warning(f"Error fetching OHLCV for {symbol}: {e}. Retrying in {wait_time:.2f}s...")
            time.sleep(wait_time)
    raise IOError(f"Failed to fetch OHLCV data for {symbol} after {retries} retries.")


def fetch_live_metadata(symbol: str, retries: int = 3, backoff_factor: float = 0.8) -> dict:
    """
    Fetches live metadata for a symbol using the main `info` endpoint.

    Args:
        symbol: The stock ticker symbol.
        retries: The number of times to retry on failure.
        backoff_factor: The factor by which to increase the wait time between retries.

    Returns:
        A dictionary containing the stock's metadata.

    Raises:
        IOError: If fetching fails after all retries.
    """
    ticker = yf.Ticker(symbol)
    for i in range(retries):
        try:
            # The .info dictionary contains all the necessary metadata.
            # This is simpler and more robust than merging fast_info and info.
            info = ticker.info

            # Ensure essential keys exist, even if their values are None.
            # The UI layer is responsible for handling None and displaying "N/A".
            required_keys = [
                'longName', 'shortName', 'exchange', 'marketCap', 'trailingPE',
                'forwardPE', 'dividendYield', 'debtToEquity', 'currency'
            ]
            metadata = {'symbol': symbol}
            for key in required_keys:
                metadata[key] = info.get(key)

            if not metadata.get('longName') and not metadata.get('shortName'):
                 raise ValueError(f"Could not resolve a name for symbol {symbol}")

            return metadata
        except Exception as e:
            wait_time = backoff_factor * (2 ** i)
            logging.warning(f"Error fetching metadata for {symbol}: {e}. Retrying in {wait_time:.2f}s...")
            time.sleep(wait_time)
    raise IOError(f"Failed to fetch metadata for {symbol} after {retries} retries.")