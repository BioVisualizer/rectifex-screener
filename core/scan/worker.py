import logging
from PySide6.QtCore import QObject, Signal, Slot
from typing import List

from core.data.loader import fetch_live_metadata

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ScanWorker(QObject):
    """
    Worker thread for running a full scan across a universe of tickers.
    """
    finished = Signal()
    progress = Signal(int, int, str)
    result_ready = Signal(dict)
    error = Signal(str)

    def __init__(self, tickers: List[str]):
        super().__init__()
        self.tickers = tickers
        self.is_stopped = False

    @Slot()
    def run(self):
        """
        Executes the scan across all tickers by fetching live metadata for each.
        """
        total = len(self.tickers)
        for i, ticker in enumerate(self.tickers):
            if self.is_stopped:
                break

            self.progress.emit(i + 1, total, ticker)

            try:
                # For the full scan, we fetch live metadata directly.
                metadata = fetch_live_metadata(ticker)

                # Perform some basic scoring based on available metadata
                score = 0

                # Score based on Trailing P/E
                pe = metadata.get('trailingPE')
                if pe and 0 < pe < 50:
                    if pe < 15:
                        score += 25
                    elif pe < 30:
                        score += 15
                    else:
                        score += 5

                # Score based on Forward P/E vs Trailing P/E
                forward_pe = metadata.get('forwardPE')
                if forward_pe and pe and 0 < forward_pe < pe:
                    score += 15 # Indicates expected earnings growth

                # Score based on Dividend Yield
                div_yield = metadata.get('dividendYield', 0)
                if div_yield > 0:
                    score += 10
                if div_yield > 0.02: # > 2%
                    score += 15

                market_cap = metadata.get('marketCap', 0)
                # Score based on Market Cap
                if market_cap > 500e9: # > $500B
                    score += 10
                if market_cap > 1e12: # > $1T
                    score += 15

                self.result_ready.emit({
                    'Ticker': ticker,
                    'Name': metadata.get('longName', 'N/A'),
                    'Score': score,
                    'Market Cap': f"${market_cap/1e9:.1f}B" if market_cap else "N/A"
                })

            except Exception as e:
                logging.error(f"Failed to process ticker {ticker} in full scan: {e}")
                self.error.emit(f"Error on {ticker}: {e}")

        self.finished.emit()

    def stop(self):
        self.is_stopped = True