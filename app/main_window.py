import sys
import logging
import os
from pathlib import Path

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QSplitter, QStatusBar, QLabel, QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt

# --- Local Imports for New Architecture ---
from app.widgets.search_bar import SearchBar
from app.widgets.chart_panel import ChartPanel
from app.theming.palette import get_dark_palette

# --- Core Service Imports ---
from core.config import DEFAULT_UNIVERSE
from core.data.universe import build_or_refresh_universe, resolve_symbol
from core.data.loader import fetch_live_ohlcv, fetch_live_metadata
from core.data.cache import CacheService
from core.indicators.engine import IndicatorEngine
from core.indicators.fib import auto_fib_levels
from core.signals.engine import SignalsEngine
from core.chart.service import ChartService
from core.export import export_single_stock_to_excel
from core.scan.worker import ScanWorker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SymbolResolverWorker(QObject):
    """
    Resolves a search query to a ticker symbol in a background thread.
    """
    finished = Signal()
    resolved = Signal(str)
    error = Signal(str)

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    @Slot()
    def run(self):
        try:
            logging.info(f"Resolving query: {self.query}")
            result = resolve_symbol(self.query) # This function handles its own DB connection
            if result and result.get('symbol'):
                logging.info(f"Resolved '{self.query}' to '{result['symbol']}'")
                self.resolved.emit(result['symbol'])
            else:
                self.error.emit(f"Could not resolve ticker for '{self.query}'")
        except Exception as e:
            logging.error(f"Error in symbol resolver for {self.query}: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class DataWorker(QObject):
    """
    Handles all long-running data operations in a separate thread.
    Crucially, it does NOT perform any UI operations like charting.
    """
    finished = Signal()
    results_ready = Signal(dict)
    error = Signal(str)

    def __init__(self, symbol: str):
        super().__init__()
        self.symbol = symbol.strip().upper()
        self.cache = CacheService()
        self.indicator_engine = IndicatorEngine()
        self.fib_engine = auto_fib_levels
        self.signal_engine = SignalsEngine()

    @Slot()
    def run(self):
        try:
            logging.info(f"DataWorker starting for symbol: {self.symbol}")

            ohlcv_df = fetch_live_ohlcv(self.symbol)
            if ohlcv_df.empty:
                raise ValueError(f"No OHLCV data found for symbol '{self.symbol}'")

            metadata = fetch_live_metadata(self.symbol)
            self.cache.save_ohlcv(self.symbol, ohlcv_df)

            indicators = self.indicator_engine.compute(ohlcv_df)
            fib_data = self.fib_engine(ohlcv_df['High'], ohlcv_df['Low'], ohlcv_df['Close'])
            signals = self.signal_engine.generate(ohlcv_df, indicators)

            self.results_ready.emit({
                "symbol": self.symbol, "ohlcv": ohlcv_df, "metadata": metadata,
                "indicators": indicators, "signals": signals, "fib_data": fib_data,
                "is_stale": False
            })

        except Exception as e:
            logging.error(f"Error in data worker for {self.symbol}: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rectifex Global Screener")
        self.setGeometry(100, 100, 1600, 900)

        self.apply_theme()
        self.latest_analysis_results = None
        self.current_symbol = None
        self.chart_service = ChartService() # Chart service now lives on the main thread

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        toolbar_layout = QHBoxLayout()
        self.search_bar = SearchBar()
        self.scan_button = QPushButton("Run Full Scan")
        toolbar_layout.addWidget(QLabel("Single-Stock Quick Search:"))
        toolbar_layout.addWidget(self.search_bar, 1)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.scan_button)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Ticker", "Name", "Score", "Market Cap"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.results_table.setSortingEnabled(True)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)

        self.chart_panel = ChartPanel()

        main_splitter.addWidget(self.results_table)
        main_splitter.addWidget(self.chart_panel)
        main_splitter.setStretchFactor(1, 1) # Allow the chart panel to expand
        main_splitter.setSizes([600, 1000])

        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(main_splitter)

        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Ready. Use the search bar or run a full scan.")

        self.search_bar.symbolSelected.connect(self.start_symbol_resolution)
        self.chart_panel.export_button.clicked.connect(self.export_analysis_to_excel)
        self.chart_panel.chartOptionsChanged.connect(self.on_chart_options_changed)
        self.chart_panel.reloadRequested.connect(self.on_chart_reload_requested)
        self.scan_button.clicked.connect(self.start_full_scan)
        self.results_table.cellDoubleClicked.connect(self.on_table_double_click)

        self.init_universe()

    def apply_theme(self):
        self.setPalette(get_dark_palette())
        try:
            style_path = Path(__file__).parent / "theming" / "style.qss"
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())
            logging.info("Modern dark theme applied.")
        except FileNotFoundError:
            logging.error(f"Stylesheet not found at {style_path}")

    def init_universe(self):
        self.statusBar().showMessage("Initializing symbol universe...")
        try:
            build_or_refresh_universe()
            self.statusBar().showMessage("Symbol universe ready.", 5000)
        except Exception as e:
            self.statusBar().showMessage(f"Error initializing universe: {e}", 10000)

    @Slot(str)
    def start_symbol_resolution(self, query: str):
        """
        Starts the process of resolving a user's query to a valid ticker symbol.
        """
        if not query: return
        self.statusBar().showMessage(f"Resolving '{query}'...")

        self.resolve_thread = QThread()
        self.resolve_worker = SymbolResolverWorker(query)
        self.resolve_worker.moveToThread(self.resolve_thread)

        self.resolve_thread.started.connect(self.resolve_worker.run)
        self.resolve_worker.finished.connect(self.resolve_thread.quit)
        self.resolve_worker.finished.connect(self.resolve_worker.deleteLater)
        self.resolve_thread.finished.connect(self.resolve_thread.deleteLater)

        self.resolve_worker.resolved.connect(self.start_analysis_for_symbol)
        self.resolve_worker.error.connect(self.on_analysis_error)

        self.resolve_thread.start()

    @Slot(str)
    def start_analysis_for_symbol(self, symbol: str):
        if not symbol: return
        self.current_symbol = symbol
        self.statusBar().showMessage(f"Fetching live data for {symbol}...")
        self.thread = QThread()
        self.worker = DataWorker(symbol)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.results_ready.connect(self.on_analysis_complete)
        self.worker.error.connect(self.on_analysis_error)

        self.chart_panel.reload_button.setEnabled(False)
        self.thread.start()

    @Slot()
    def start_full_scan(self):
        query = self.search_bar.get_search_text() if hasattr(self.search_bar, "get_search_text") else ""
        if query:
            self.statusBar().showMessage(f"Resolving scan target '{query}'...")
            try:
                resolved = resolve_symbol(query)
            except Exception as exc:
                logging.error(f"Failed to resolve scan query '{query}': {exc}")
                self.statusBar().showMessage(f"Error resolving '{query}': {exc}", 10000)
                return

            if not resolved or not resolved.get("symbol"):
                self.statusBar().showMessage(f"Could not resolve ticker for '{query}'", 10000)
                return

            tickers_to_scan = [resolved["symbol"]]
            status_message = f"Starting scan for {resolved['symbol']}..."
        else:
            tickers_to_scan = DEFAULT_UNIVERSE
            status_message = "Starting full scan..."

        self.statusBar().showMessage(status_message)
        self.scan_button.setEnabled(False)
        self.results_table.setRowCount(0)

        self.scan_thread = QThread()
        self.scan_worker = ScanWorker(tickers_to_scan)
        self.scan_worker.moveToThread(self.scan_thread)

        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.progress.connect(self.update_scan_progress)
        self.scan_worker.result_ready.connect(self.add_scan_result)

        self.scan_thread.start()

    @Slot(int, int, str)
    def update_scan_progress(self, count, total, ticker):
        self.statusBar().showMessage(f"Scanning ({count}/{total}): {ticker}...")

    @Slot(dict)
    def add_scan_result(self, result: dict):
        row_position = self.results_table.rowCount()
        self.results_table.insertRow(row_position)
        self.results_table.setItem(row_position, 0, QTableWidgetItem(result.get("Ticker")))
        self.results_table.setItem(row_position, 1, QTableWidgetItem(result.get("Name")))
        self.results_table.setItem(row_position, 2, QTableWidgetItem(str(result.get("Score"))))
        self.results_table.setItem(row_position, 3, QTableWidgetItem(result.get("Market Cap")))

    @Slot()
    def on_scan_finished(self):
        self.statusBar().showMessage("Full scan complete.", 10000)
        self.scan_button.setEnabled(True)
        self.scan_thread.quit()
        self.scan_thread.wait()

    @Slot(int, int)
    def on_table_double_click(self, row, column):
        ticker_item = self.results_table.item(row, 0)
        if ticker_item:
            # Re-resolve the symbol to ensure we get the latest data,
            # even if it's from the potentially cached table results.
            self.start_symbol_resolution(ticker_item.text())

    @Slot(dict)
    def on_analysis_complete(self, results: dict):
        self.statusBar().showMessage("Analysis complete.", 5000)
        self.latest_analysis_results = results

        self.refresh_chart()
        self.chart_panel.update_overview(results['metadata'])
        self.chart_panel.update_signals(results['signals'])
        self.chart_panel.set_stale_badge_visibility(results['is_stale'])
        self.chart_panel.export_button.setEnabled(True)
        self.chart_panel.reload_button.setEnabled(True)

    @Slot(str)
    def on_analysis_error(self, error_message: str):
        self.statusBar().showMessage(f"Error: {error_message}", 10000)
        self.chart_panel.chart_view.setText(f"Analysis failed for symbol.\nError: {error_message}")
        self.chart_panel.export_button.setEnabled(False)
        self.latest_analysis_results = None
        self.chart_panel.reload_button.setEnabled(True)

    @Slot()
    def export_analysis_to_excel(self):
        if not self.latest_analysis_results or not self.latest_analysis_results.get('chart_path'):
            self.statusBar().showMessage("No complete analysis data to export.", 5000)
            return

        self.statusBar().showMessage("Exporting to Excel...", 3000)
        try:
            filepath = export_single_stock_to_excel(
                symbol=self.latest_analysis_results['symbol'],
                metadata=self.latest_analysis_results['metadata'],
                ohlcv_df=self.latest_analysis_results['ohlcv'],
                indicators=self.latest_analysis_results['indicators'],
                signals=self.latest_analysis_results['signals'],
                fib_data=self.latest_analysis_results['fib_data'],
                chart_path=self.latest_analysis_results['chart_path']
            )
            if filepath:
                self.statusBar().showMessage(f"Export successful: {filepath}", 10000)
            else:
                self.statusBar().showMessage("Export failed. See logs for details.", 10000)
        except Exception as e:
            logging.error(f"Excel export failed: {e}")
            self.statusBar().showMessage(f"Export failed: {e}", 10000)

    def refresh_chart(self):
        """Regenerates the chart image using the latest analysis data and UI options."""
        if not self.latest_analysis_results:
            return

        chart_options = self.chart_panel.get_chart_options()
        ohlcv_for_chart = self.latest_analysis_results['ohlcv'].tail(252)
        indicators_for_chart = {
            k: (v.tail(252) if hasattr(v, 'tail') else v)
            for k, v in self.latest_analysis_results['indicators'].items()
        }
        chart_path = self.chart_service.draw(
            self.latest_analysis_results['symbol'],
            ohlcv_for_chart,
            indicators_for_chart,
            self.latest_analysis_results['fib_data'],
            chart_options,
        )

        if chart_path:
            self.latest_analysis_results['chart_path'] = chart_path
            self.chart_panel.update_chart(chart_path)

    @Slot(dict)
    def on_chart_options_changed(self, _options: dict):
        self.refresh_chart()

    @Slot()
    def on_chart_reload_requested(self):
        if self.current_symbol:
            self.start_analysis_for_symbol(self.current_symbol)

if __name__ == "__main__":
    # Force software-based OpenGL rendering to avoid graphics driver issues.
    # This must be set *before* the QApplication is instantiated.
    QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())