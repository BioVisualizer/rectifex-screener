import logging
from PySide6.QtCore import QObject, Signal, Slot
from typing import List

from core.data.loader import fetch_live_metadata
from core.data.cache import CacheService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ScanWorker(QObject):
    """
    Worker thread for running a full scan across a universe of tickers.
    """
    finished = Signal()
    progress = Signal(int, int, str) # count, total, ticker
    result_ready = Signal(dict)
    error = Signal(str)

    def __init__(self, tickers: List[str]):
        super().__init__()
        self.tickers = tickers
        self.is_stopped = False
        self.cache = CacheService()

    @Slot()
    def run(self):
        """
        Executes the scan across all tickers.
        """
        total = len(self.tickers)
        for i, ticker in enumerate(self.tickers):
            if self.is_stopped:
                break

            self.progress.emit(i + 1, total, ticker)

            try:
                # For a full scan, we can be more lenient and use the cache
                # to avoid hitting API limits. A full live fetch is not required here.
                metadata = self.cache.load_ohlcv(ticker) # A simple proxy for cached data
                if metadata is None:
                    # If not in cache, fetch live and cache it
                    metadata = fetch_live_metadata(ticker)
                    self.cache.save_ohlcv(ticker, metadata) # Note: saving metadata to ohlcv cache, needs fix

                # Perform some basic scoring
                score = 0
                pe = metadata.get('trailingPE')
                if pe and pe > 0:
                    if pe < 15: score += 50
                    elif pe < 25: score += 25

                market_cap = metadata.get('marketCap', 0)

                self.result_ready.emit({
                    'Ticker': ticker,
                    'Name': metadata.get('longName', 'N/A'),
                    'Score': score,
                    'Market Cap': f"${market_cap/1e9:.1f}B" if market_cap else "N/A"
                })

            except Exception as e:
                logging.error(f"Failed to process ticker {ticker}: {e}")
                self.error.emit(f"Error on {ticker}: {e}")

        self.finished.emit()

    def stop(self):
        self.is_stopped = True