# =============================================================================
# Rectifex - GUI
# =============================================================================

import sys
import pandas as pd
import webbrowser
import os

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QComboBox, QLabel,
                             QTableWidget, QTableWidgetItem, QProgressBar, QHeaderView,
                             QMessageBox, QFileDialog, QStatusBar, QMenu, QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QBrush

# Local Imports
import screener_engine
import ticker_fetcher
import technical_analyzer
from scan_worker import ScanWorker
from ui.settings_dialog import SettingsDialog, load_api_key
from ui.chart_dialog import ChartDialog
from ui.ticker_manager_dialog import TickerManagerDialog
from ui.help_dialog import HelpDialog
from ui.strategy_editor_dialog import StrategyEditorDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Rectifex - Global Stock Screener"); self.setGeometry(100, 100, 1200, 800); self.result_df = None
        self.current_tickers = [] # Start with an empty list
        self.scan_errors = []
        self.api_key = load_api_key()
        self.chart_cache = {}
        self.search_col_indices = None # To cache search column indices
        self.worker = None
        self.is_scanning = False

        main_layout = QVBoxLayout(); top_bar_layout = QHBoxLayout(); controls_layout = QHBoxLayout()
        self.strategy_label = QLabel("Analysis Strategy:")
        self.strategy_definitions = screener_engine.get_strategy_definitions()
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(self.strategy_definitions.keys())
        self.strategy_combo.currentTextChanged.connect(self.update_strategy_tooltip)
        self.update_strategy_tooltip(self.strategy_combo.currentText())

        self.scan_button = QPushButton("Start Scan")
        self.save_csv_button = QPushButton("Save as CSV"); self.save_csv_button.setEnabled(False)

        # --- Ticker Source Selection ---
        self.ticker_source_label = QLabel("Ticker Source:")
        self.ticker_source_combo = QComboBox()
        self.ticker_source_combo.addItems([
            "Default Global List", "Custom List"
        ])
        self.ticker_source_combo.currentIndexChanged.connect(self.on_ticker_source_changed)
        self.manage_tickers_button = QPushButton("Manage Custom List")
        self.manage_tickers_button.setEnabled(False)
        self.manage_tickers_button.clicked.connect(self.open_ticker_dialog)

        action_layout = QHBoxLayout()
        action_layout.addLayout(controls_layout)
        action_layout.addStretch()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search by Name or Ticker...")
        self.search_bar.setMaximumWidth(300)
        self.search_bar.textChanged.connect(self.filter_results_table)
        self.search_bar.setEnabled(False)
        action_layout.addWidget(self.search_bar)

        self.settings_button = QPushButton("Settings")
        self.help_button = QPushButton("Help")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.help_button.clicked.connect(self.show_help_dialog)
        action_layout.addWidget(self.settings_button)
        action_layout.addWidget(self.help_button)

        self.scan_button.clicked.connect(self.handle_scan_click)
        self.save_csv_button.clicked.connect(self.save_as_csv)

        controls_layout.addWidget(self.strategy_label); controls_layout.addWidget(self.strategy_combo)
        controls_layout.addWidget(self.ticker_source_label)
        controls_layout.addWidget(self.ticker_source_combo)
        controls_layout.addWidget(self.manage_tickers_button)
        controls_layout.addWidget(self.scan_button)
        controls_layout.addWidget(self.save_csv_button)

        top_bar_layout.addLayout(action_layout)
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False)
        self.results_table = QTableWidget(); self.results_table.setEditTriggers(QTableWidget.NoEditTriggers); self.results_table.setSortingEnabled(True); self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.cellDoubleClicked.connect(self.show_chart_for_ticker)
        self.results_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self.show_context_menu)
        main_layout.addLayout(top_bar_layout); main_layout.addWidget(self.progress_bar); main_layout.addWidget(self.results_table)
        central_widget = QWidget(); central_widget.setLayout(main_layout); self.setCentralWidget(central_widget)
        self.setStatusBar(QStatusBar(self))
        self.create_menus()

    def create_menus(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        manage_strategies_action = QAction("Manage Strategies...", self)
        manage_strategies_action.triggered.connect(self.open_strategy_editor)
        file_menu.addAction(manage_strategies_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def open_strategy_editor(self):
        dialog = StrategyEditorDialog(self.strategy_definitions, self)
        if dialog.exec():
            self.strategy_definitions = dialog.get_updated_strategies()
            screener_engine.save_strategy_definitions(self.strategy_definitions)
            self.refresh_strategy_combo()
            self.statusBar().showMessage("Strategies saved successfully.", 5000)

    def refresh_strategy_combo(self):
        current_selection = self.strategy_combo.currentText()
        self.strategy_combo.blockSignals(True)
        self.strategy_combo.clear()
        self.strategy_combo.addItems(sorted(self.strategy_definitions.keys()))

        if current_selection in self.strategy_definitions:
            self.strategy_combo.setCurrentText(current_selection)

        self.strategy_combo.blockSignals(False)
        self.update_strategy_tooltip(self.strategy_combo.currentText())

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.api_key = load_api_key()
            self.statusBar().showMessage("Settings saved.", 5000)

    def open_ticker_dialog(self):
        dialog = TickerManagerDialog(self.current_tickers, self)
        if dialog.exec():
            self.current_tickers = dialog.get_tickers()
            self.statusBar().showMessage(f"Ticker list updated to {len(self.current_tickers)} tickers.", 5000)

    def handle_scan_click(self):
        if self.is_scanning:
            self.stop_scan()
        else:
            self.start_scan()

    def on_ticker_source_changed(self, index):
        source = self.ticker_source_combo.itemText(index)
        self.manage_tickers_button.setEnabled(source == "Custom List")

    def start_scan(self):
        ticker_source = self.ticker_source_combo.currentText()

        if ticker_source == "Default Global List":
            self.current_tickers = ticker_fetcher.get_default_tickers()
        elif ticker_source == "Custom List":
            # self.current_tickers is already updated by the dialog, so no action needed here.
            pass

        if not self.current_tickers:
            QMessageBox.warning(self, "No Tickers", f"The selected ticker list '{ticker_source}' is empty.")
            return

        # --- Start the Scan ---
        self.is_scanning = True
        self.scan_button.setText("Stop Scan")
        self.save_csv_button.setEnabled(False); self.search_bar.setEnabled(False); self.search_bar.clear(); self.progress_bar.setValue(0); self.progress_bar.setVisible(True); self.results_table.setRowCount(0)
        self.search_col_indices = None # Reset cached column indices
        data_source = "FMP" if self.api_key else "yfinance"
        self.statusBar().showMessage(f"Starting scan for {len(self.current_tickers)} tickers ({ticker_source}) using {data_source}...")
        self.worker = ScanWorker(self.strategy_combo.currentText().replace(" ", "_"), self.current_tickers, self.api_key)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.scan_finished)
        self.worker.start()

    def stop_scan(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.statusBar().showMessage("Stopping scan...")
            self.scan_button.setEnabled(False) # Prevent multiple clicks

    def update_progress(self, progress_data):
        count, total, ticker = progress_data
        percent = int((count / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(percent)
        self.statusBar().showMessage(f"Scanning ({count}/{total}): {ticker}...")

    def scan_finished(self, results):
        was_stopped = self.worker.is_stopped() if self.worker else False
        self.is_scanning = False
        self.scan_button.setText("Start Scan")
        self.scan_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.worker = None

        if was_stopped:
            self.statusBar().showMessage("Scan stopped by user.", 10000)
            return

        if not results:
             self.statusBar().showMessage("Scan failed: No results returned.", 10000)
             return
        df, summary = results
        self.scan_errors = summary.get('failed_list', [])
        status_msg = f"Scan finished. {summary.get('final_count', 0)} of {summary.get('total_tickers', 0)} stocks loaded. {summary.get('failed_count', 0)} tickers failed."
        self.statusBar().showMessage(status_msg, 10000)
        if df.empty: return
        self.result_df = df
        self.save_csv_button.setEnabled(True)
        self.search_bar.setEnabled(True)
        self.populate_table(df)

    def populate_table(self, df):
        self.results_table.setSortingEnabled(False)
        df_display = df.rename(columns={'MarketCapUSD': 'MarketCap (USD)'})
        self.results_table.setRowCount(len(df_display)); self.results_table.setColumnCount(len(df_display.columns)); self.results_table.setHorizontalHeaderLabels(df_display.columns)

        strategy_col_name = self.strategy_combo.currentText().replace(" ", "_")

        for r_idx, (index, row) in enumerate(df_display.iterrows()):
            for c_idx, col_name in enumerate(df_display.columns):
                original_col_name = 'MarketCapUSD' if col_name == 'MarketCap (USD)' else col_name
                raw_value = df.iloc[r_idx][original_col_name]
                item = QTableWidgetItem()

                if isinstance(raw_value, (int, float)) and not pd.isna(raw_value):
                    item.setData(Qt.EditRole, raw_value)
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                if '_Score' in col_name or col_name == strategy_col_name:
                    if isinstance(raw_value, (int, float)) and not pd.isna(raw_value):
                        score = max(0, min(100, raw_value))
                        red = QColor("#ffcdd2"); yellow = QColor("#fff9c4"); green = QColor("#c8e6c9")
                        if score >= 70: item.setBackground(QBrush(green))
                        elif score >= 40: item.setBackground(QBrush(yellow))
                        else: item.setBackground(QBrush(red))

                display_text = "N/A"
                if not pd.isna(raw_value):
                    if col_name == 'MarketCap (USD)': display_text = f'${raw_value/1e9:,.0f}B'
                    elif '_Score' in col_name or "Value" in col_name or "Growth" in col_name or col_name in ["Balanced", "PE", "ROE_Avg3Y", "RevGrowth3YCAGR"]: display_text = f'{raw_value:,.1f}'
                    elif col_name == 'PB': display_text = f'{raw_value:,.2f}'
                    elif col_name == 'DivYield': display_text = f'{raw_value:,.2f}%'
                    else: display_text = str(raw_value)

                item.setText(display_text)
                self.results_table.setItem(r_idx, c_idx, item)

        self.results_table.resizeColumnsToContents(); self.results_table.setSortingEnabled(True)

    def show_chart_for_ticker(self, row, column):
        """Handles the double-click event on the table to show a chart."""
        if self.result_df is None or row >= len(self.result_df):
            return

        try:
            # Find the 'Ticker' column index and get the ticker symbol
            header_labels = [self.results_table.horizontalHeaderItem(i).text() for i in range(self.results_table.columnCount())]
            ticker_col_idx = header_labels.index("Ticker")
            ticker = self.results_table.item(row, ticker_col_idx).text()
        except (ValueError, AttributeError):
            self.statusBar().showMessage("Could not find 'Ticker' column or row.", 5000)
            return

        self.statusBar().showMessage(f"Loading chart for {ticker}...", 2000)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            if ticker in self.chart_cache:
                fig = self.chart_cache[ticker]
                self.statusBar().showMessage(f"Showing cached chart for {ticker}.", 5000)
            else:
                fig = technical_analyzer.generate_analysis_figure(ticker)
                if fig:
                    self.chart_cache[ticker] = fig
                    self.statusBar().showMessage(f"Successfully loaded chart for {ticker}.", 5000)
                else:
                    self.statusBar().showMessage(f"Failed to generate chart for {ticker}.", 8000)
                    QMessageBox.warning(self, "Chart Error", f"Could not generate the technical analysis chart for {ticker}.")
                    return

            # Create and show the chart dialog
            dialog = ChartDialog(fig, self)
            dialog.show() # Use show() for non-modal dialog

        finally:
            QApplication.restoreOverrideCursor()


    def filter_results_table(self, text):
        """Filters the results table based on the search text."""
        search_text = text.lower()

        # Find and cache the column indices for 'Name' and 'Ticker' if not already done
        if self.search_col_indices is None:
            try:
                header_labels = [self.results_table.horizontalHeaderItem(i).text() for i in range(self.results_table.columnCount())]
                name_col = header_labels.index("Name")
                ticker_col = header_labels.index("Ticker")
                self.search_col_indices = {'Name': name_col, 'Ticker': ticker_col}
            except (ValueError, AttributeError):
                # This can happen if the table is empty or headers are not set
                self.search_col_indices = {} # Avoid re-trying by setting to empty dict
                return

        if not self.search_col_indices:
            return # Cannot search if columns are not found

        name_col = self.search_col_indices['Name']
        ticker_col = self.search_col_indices['Ticker']

        for row in range(self.results_table.rowCount()):
            name_item = self.results_table.item(row, name_col)
            ticker_item = self.results_table.item(row, ticker_col)

            # Ensure items exist before accessing their text
            name_text = name_item.text().lower() if name_item else ""
            ticker_text = ticker_item.text().lower() if ticker_item else ""

            match = search_text in name_text or search_text in ticker_text
            self.results_table.setRowHidden(row, not match)

    def show_context_menu(self, pos):
        if self.results_table.rowCount() == 0: return
        try:
            row = self.results_table.rowAt(pos.y())
            if row < 0: return
            header_labels = [self.results_table.horizontalHeaderItem(i).text() for i in range(self.results_table.columnCount())]
            ticker_col_idx = header_labels.index("Ticker")
            ticker = self.results_table.item(row, ticker_col_idx).text()
        except (ValueError, AttributeError):
            return

        menu = QMenu()
        yahoo_action = QAction(f"View '{ticker}' on Yahoo Finance", self)
        yahoo_action.triggered.connect(lambda: webbrowser.open(f"https://finance.yahoo.com/quote/{ticker}"))
        menu.addAction(yahoo_action)

        finviz_action = QAction(f"View '{ticker}' on Finviz", self)
        finviz_action.triggered.connect(lambda: webbrowser.open(f"https://finviz.com/quote.ashx?t={ticker}"))
        menu.addAction(finviz_action)

        menu.exec(self.results_table.mapToGlobal(pos))

    def save_as_csv(self):
        if self.result_df is None: return
        path, _ = QFileDialog.getSaveFileName(self, "Save as CSV", "rectifex_scan.csv", "CSV Files (*.csv)")
        if path:
            try:
                self.result_df.to_csv(path, index=False, decimal='.', sep=',')
                QMessageBox.information(self, "Success", f"Data saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error saving file:\n{e}")

    def show_help_dialog(self):
        dialog = HelpDialog(self, error_log=self.scan_errors); dialog.exec()

    def update_strategy_tooltip(self, strategy_name):
        if strategy_name in self.strategy_definitions:
            strategy_data = self.strategy_definitions[strategy_name]
            weights = strategy_data.get("weights", {})
            tooltip_parts = [f"<b>{strategy_name} Strategy Weights:</b>", "<hr>"]
            if not weights:
                tooltip_parts.append("No weights defined.")
            for score, weight in weights.items():
                clean_score = score.replace('_', ' ')
                percent = f"{weight:.0%}"
                tooltip_parts.append(f"• {clean_score}: {percent}")
            self.strategy_combo.setToolTip("<br>".join(tooltip_parts))

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    app = QApplication(sys.argv); app.setDesktopFileName("io.github.BioVisualizer.Rectifex"); window = MainWindow(); window.show(); sys.exit(app.exec())
