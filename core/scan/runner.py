from PySide6.QtCore import QThread, Signal
import screener_engine

class ScanWorker(QThread):
    progress = Signal(tuple)
    finished = Signal(object)

    def __init__(self, strategy, tickers, api_key):
        super().__init__()
        self.strategy = strategy
        self.tickers = tickers
        self.api_key = api_key
        self._stopped = False

    def run(self):
        """Executes the screener engine in a background thread."""
        self.finished.emit(screener_engine.run_complete_screener(self.strategy, self.tickers, self.api_key, self.progress, worker=self))

    def stop(self):
        """Signals the thread to stop its operation."""
        self._stopped = True

    def is_stopped(self):
        """Checks if the stop signal has been sent."""
        return self._stopped
