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
                pe = metadata.get('trailingPE')
                if pe and pe > 0:
                    if pe < 15:
                        score += 50
                    elif pe < 25:
                        score += 25

                market_cap = metadata.get('marketCap', 0)

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