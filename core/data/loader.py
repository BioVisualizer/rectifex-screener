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
            df = ticker.history(period=period, interval=interval, auto_adjust=True)
            if df.empty:
                raise ValueError(f"No data found for symbol {symbol}")
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
    Fetches live metadata for a symbol, prioritizing fast_info and falling back to info.

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
            # yfinance fast_info is often quicker and has key financial data
            info = ticker.fast_info
            # If fast_info is limited, supplement with the full `info` dict
            full_info = ticker.info

            metadata = {
                'symbol': symbol,
                'longName': full_info.get('longName', info.get('longName')),
                'shortName': full_info.get('shortName'),
                'exchange': full_info.get('exchange'),
                'marketCap': full_info.get('marketCap'),
                'trailingPE': full_info.get('trailingPE'),
                'forwardPE': full_info.get('forwardPE'),
                'dividendYield': full_info.get('dividendYield'),
                'debtToEquity': full_info.get('debtToEquity'),
                'currency': info.get('currency'),
                'lastPrice': info.get('lastPrice')
            }
            # Filter out None values
            metadata = {k: v for k, v in metadata.items() if v is not None}

            if not metadata.get('longName') and not metadata.get('shortName'):
                 raise ValueError(f"Could not resolve a name for symbol {symbol}")

            return metadata
        except Exception as e:
            wait_time = backoff_factor * (2 ** i)
            logging.warning(f"Error fetching metadata for {symbol}: {e}. Retrying in {wait_time:.2f}s...")
            time.sleep(wait_time)
    raise IOError(f"Failed to fetch metadata for {symbol} after {retries} retries.")