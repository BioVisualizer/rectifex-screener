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
from core.scan.worker import ScanWorker # Import the new scan worker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# (DataWorker class remains the same)
class DataWorker(QObject):
    """
    Handles all long-running data operations for a SINGLE stock.
    """
    finished = Signal()
    results_ready = Signal(dict)
    error = Signal(str)

    def __init__(self, symbol: str):
        super().__init__()
        self.symbol = symbol
        self.cache = CacheService()
        self.indicator_engine = IndicatorEngine()
        self.fib_engine = auto_fib_levels
        self.signal_engine = SignalsEngine()
        self.chart_service = ChartService()

    @Slot()
    def run(self):
        try:
            logging.info(f"Worker starting for symbol: {self.symbol}")

            resolution = resolve_symbol(self.symbol)
            if not resolution:
                raise ValueError(f"Could not resolve symbol '{self.symbol}'")

            resolved_symbol = resolution['symbol']
            is_stale = resolution['source'] == 'fuzzy_cache'

            ohlcv_df = fetch_live_ohlcv(resolved_symbol)
            metadata = fetch_live_metadata(resolved_symbol)
            self.cache.save_ohlcv(resolved_symbol, ohlcv_df)

            indicators = self.indicator_engine.compute(ohlcv_df)
            fib_data = self.fib_engine(ohlcv_df['High'], ohlcv_df['Low'], ohlcv_df['Close'])
            signals = self.signal_engine.generate(ohlcv_df, indicators)

            chart_options = {
                'show_ema_ribbon': True, 'show_bbands': True, 'show_vwap': True,
                'show_rsi': True, 'show_macd': True, 'show_fib': True,
                'bb_len': 20, 'bb_std': 2.0
            }
            chart_path = self.chart_service.draw(resolved_symbol, ohlcv_df.tail(252), indicators, fib_data, chart_options)

            self.results_ready.emit({
                "symbol": resolved_symbol, "ohlcv": ohlcv_df, "chart_path": chart_path,
                "metadata": metadata, "indicators": indicators, "signals": signals,
                "fib_data": fib_data, "is_stale": is_stale
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

        self.chart_panel = ChartPanel()

        main_splitter.addWidget(self.results_table)
        main_splitter.addWidget(self.chart_panel)
        main_splitter.setSizes([600, 1000])

        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(main_splitter)

        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Ready. Use the search bar or run a full scan.")

        # --- Connections ---
        self.search_bar.symbolSelected.connect(self.start_analysis_for_symbol)
        self.chart_panel.export_button.clicked.connect(self.export_analysis_to_excel)
        self.scan_button.clicked.connect(self.start_full_scan)

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
    def start_analysis_for_symbol(self, symbol: str):
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

        self.thread.start()

    @Slot()
    def start_full_scan(self):
        self.statusBar().showMessage("Starting full scan...")
        self.scan_button.setEnabled(False)
        self.results_table.setRowCount(0) # Clear previous results

        self.scan_thread = QThread()
        self.scan_worker = ScanWorker(DEFAULT_UNIVERSE)
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

    @Slot(dict)
    def on_analysis_complete(self, results: dict):
        self.statusBar().showMessage("Analysis complete.", 5000)
        self.latest_analysis_results = results

        self.chart_panel.update_chart(results['chart_path'])
        self.chart_panel.update_overview(results['metadata'])
        self.chart_panel.set_stale_badge_visibility(results['is_stale'])
        self.chart_panel.export_button.setEnabled(True)

    @Slot(str)
    def on_analysis_error(self, error_message: str):
        self.statusBar().showMessage(f"Error: {error_message}", 10000)
        self.chart_panel.chart_view.setText(f"Analysis failed for symbol.\nError: {error_message}")
        self.chart_panel.export_button.setEnabled(False)
        self.latest_analysis_results = None

    @Slot()
    def export_analysis_to_excel(self):
        if not self.latest_analysis_results:
            self.statusBar().showMessage("No analysis data to export.", 5000)
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())