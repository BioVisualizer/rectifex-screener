# =============================================================================
# Rectifex - GUI
# =============================================================================

import sys
import pandas as pd
import webbrowser
import re
import configparser
import os
from pathlib import Path

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QComboBox, QLabel,
                             QTableWidget, QTableWidgetItem, QProgressBar, QHeaderView,
                             QMessageBox, QFileDialog, QDialog, QTabWidget, QTextEdit,
                             QStatusBar, QMenu, QLineEdit, QDialogButtonBox, QListWidget,
                             QGroupBox, QFormLayout, QSpinBox)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QAction, QColor, QBrush

import screener_engine
from help_texts import HELP_TEXT_DE, HELP_TEXT_EN
import copy
import technical_analyzer
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# --- Configuration Handling ---
CONFIG_DIR = Path.home() / ".config" / "rectifex"
CONFIG_FILE = CONFIG_DIR / "settings.conf"

def load_api_key():
    if not CONFIG_FILE.exists():
        return ""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config.get('API', 'key', fallback="")

def save_api_key(key):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config = configparser.ConfigParser()
    config['API'] = {'key': key}
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

# --- Dialogs ---

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Enter your Financial Modeling Prep API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setText(load_api_key())
        layout.addWidget(self.api_key_input)

        info_label = QLabel('<a href="https://site.financialmodelingprep.com/register">Get a free API key from Financial Modeling Prep</a>')
        info_label.setOpenExternalLinks(True)
        layout.addWidget(info_label)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def accept(self):
        save_api_key(self.api_key_input.text())
        super().accept()

class ChartDialog(QDialog):
    """A dialog to display a Matplotlib chart."""
    def __init__(self, fig: Figure, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Technical Analysis Chart")
        self.setMinimumSize(900, 700) # Adjusted size
        self.setModal(False) # Allow interacting with main window

        layout = QVBoxLayout()
        canvas = FigureCanvas(fig)
        canvas.setParent(self)
        layout.addWidget(canvas)

        self.setLayout(layout)

class ScanWorker(QThread):
    progress = Signal(int); finished = Signal(object)
    def __init__(self, strategy, tickers, api_key):
        super().__init__()
        self.strategy = strategy
        self.tickers = tickers
        self.api_key = api_key
    def run(self):
        self.finished.emit(screener_engine.run_complete_screener(self.strategy, self.tickers, self.api_key, self.progress))

class TickerManagerDialog(QDialog):
    def __init__(self, current_tickers, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Ticker List")
        self.setMinimumSize(400, 500)
        self.tickers = current_tickers
        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText("\n".join(self.tickers))
        layout.addWidget(self.text_edit)
        button_layout = QHBoxLayout()
        self.load_button = QPushButton("Load from File...")
        self.load_button.clicked.connect(self.load_from_file)
        button_layout.addWidget(self.load_button)
        button_layout.addStretch()
        self.save_button = QPushButton("Save and Close")
        self.save_button.clicked.connect(self.accept)
        button_layout.addWidget(self.save_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_from_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Tickers", "", "Text Files (*.txt);;CSV Files (*.csv)")
        if path:
            try:
                with open(path, 'r') as f:
                    content = f.read()
                    tickers = re.split(r'[,\s;]+', content)
                    self.text_edit.setPlainText("\n".join(filter(None, tickers)))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load file:\n{e}")

    def get_tickers(self):
        return [line.strip().upper() for line in self.text_edit.toPlainText().splitlines() if line.strip()]

class HelpDialog(QDialog):
    def __init__(self, parent=None, error_log=None):
        super().__init__(parent)
        self.setWindowTitle("Help & Information")
        self.setMinimumSize(700, 500)
        self.tab_widget = QTabWidget()
        de_tab = QTextEdit(); de_tab.setReadOnly(True); de_tab.setMarkdown(HELP_TEXT_DE)
        self.tab_widget.addTab(de_tab, "Deutsch")
        en_tab = QTextEdit(); en_tab.setReadOnly(True); en_tab.setMarkdown(HELP_TEXT_EN)
        self.tab_widget.addTab(en_tab, "English")
        if error_log:
            log_tab = QTextEdit(); log_tab.setReadOnly(True)
            log_tab.setPlainText("\n".join(error_log))
            self.tab_widget.addTab(log_tab, "Scan Log")
            self.tab_widget.setCurrentWidget(log_tab)
        layout = QVBoxLayout(); layout.addWidget(self.tab_widget); self.setLayout(layout)

class StrategyEditorDialog(QDialog):
    def __init__(self, strategies, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Strategy Editor")
        self.setMinimumSize(700, 500)

        self.strategies = copy.deepcopy(strategies)
        self.current_strategy_name = None
        self.score_keys = ["Quality_Score", "Value_Score", "Growth_Score", "Momentum_Score", "Yield_Score", "Safety_Score"]

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        editor_layout = QHBoxLayout()
        main_layout.addLayout(editor_layout)

        # --- Left Panel: Strategy List ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Strategies:"))
        self.strategy_list_widget = QListWidget()
        left_layout.addWidget(self.strategy_list_widget)

        list_button_layout = QHBoxLayout()
        self.new_button = QPushButton("New")
        self.copy_button = QPushButton("Copy")
        self.delete_button = QPushButton("Delete")
        list_button_layout.addWidget(self.new_button)
        list_button_layout.addWidget(self.copy_button)
        list_button_layout.addWidget(self.delete_button)
        left_layout.addLayout(list_button_layout)
        editor_layout.addWidget(left_panel, 1)

        # --- Right Panel: Editor ---
        self.editor_groupbox = QGroupBox("Edit Strategy")
        self.editor_groupbox.setEnabled(False)
        form_layout = QFormLayout(self.editor_groupbox)

        self.name_input = QLineEdit()
        form_layout.addRow("Name:", self.name_input)

        self.score_spinboxes = {}
        for key in self.score_keys:
            spinbox = QSpinBox()
            spinbox.setRange(0, 100)
            spinbox.setSuffix("%")
            spinbox.valueChanged.connect(self.update_weight_sum)
            self.score_spinboxes[key] = spinbox
            form_layout.addRow(key.replace('_', ' ') + ":", spinbox)

        self.sum_label = QLabel("Total: 0%")
        self.sum_label.setStyleSheet("font-weight: bold;")
        form_layout.addRow(self.sum_label)
        editor_layout.addWidget(self.editor_groupbox, 2)

        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        main_layout.addWidget(self.button_box)

        # --- Connections & Initial State ---
        self.strategy_list_widget.itemSelectionChanged.connect(self.on_strategy_selection_changed)
        self.name_input.textChanged.connect(self.on_name_changed)
        self.new_button.clicked.connect(self.new_strategy)
        self.copy_button.clicked.connect(self.copy_strategy)
        self.delete_button.clicked.connect(self.delete_strategy)
        self.button_box.accepted.connect(self.on_accept)
        self.button_box.rejected.connect(self.reject)

        self.populate_strategy_list()

    def populate_strategy_list(self, select_name=None):
        self.strategy_list_widget.blockSignals(True)
        self.strategy_list_widget.clear()
        for name in sorted(self.strategies.keys()):
            self.strategy_list_widget.addItem(name)
            if name == select_name:
                self.strategy_list_widget.setCurrentRow(self.strategy_list_widget.count() - 1)
        self.strategy_list_widget.blockSignals(False)
        if self.strategy_list_widget.currentItem():
            self.on_strategy_selection_changed()
        else:
            self.editor_groupbox.setEnabled(False)


    def on_strategy_selection_changed(self):
        selected_items = self.strategy_list_widget.selectedItems()
        if not selected_items:
            self.current_strategy_name = None
            self.editor_groupbox.setEnabled(False)
            return

        new_name = selected_items[0].text()
        if self.current_strategy_name and self.current_strategy_name != new_name:
            self.save_current_editor_state()

        self.current_strategy_name = new_name
        self.load_strategy_into_editor()

    def load_strategy_into_editor(self):
        if not self.current_strategy_name: return

        strategy_data = self.strategies[self.current_strategy_name]
        is_predefined = strategy_data.get("predefined", False)

        self.name_input.setText(self.current_strategy_name)
        self.name_input.setReadOnly(is_predefined)
        self.delete_button.setEnabled(not is_predefined)
        self.editor_groupbox.setEnabled(True)

        for key, spinbox in self.score_spinboxes.items():
            spinbox.blockSignals(True)
            spinbox.setValue(int(strategy_data.get("weights", {}).get(key, 0) * 100))
            spinbox.blockSignals(False)

        self.update_weight_sum()

    def save_current_editor_state(self):
        if not self.current_strategy_name: return

        old_name = self.current_strategy_name
        new_name = self.name_input.text()

        if not new_name:
             # User cleared the name field, revert to old name to avoid issues
            self.name_input.setText(old_name)
            new_name = old_name

        strategy_data = self.strategies.pop(old_name)
        strategy_data["weights"] = {key: spinbox.value() / 100.0 for key, spinbox in self.score_spinboxes.items()}
        self.strategies[new_name] = strategy_data
        self.current_strategy_name = new_name


    def on_name_changed(self, new_name):
        if not self.current_strategy_name: return

        selected_items = self.strategy_list_widget.selectedItems()
        if not selected_items: return

        # Prevent renaming to an existing name
        if new_name != self.current_strategy_name and new_name in self.strategies:
            self.name_input.setStyleSheet("color: red;")
        else:
            self.name_input.setStyleSheet("")

        selected_items[0].setText(new_name)


    def update_weight_sum(self):
        total_weight = sum(spinbox.value() for spinbox in self.score_spinboxes.values())
        self.sum_label.setText(f"Total: {total_weight}%")
        if total_weight != 100:
            self.sum_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.sum_label.setStyleSheet("color: green; font-weight: bold;")

    def new_strategy(self):
        self.save_current_editor_state()
        base_name = "New Strategy"
        name = base_name
        i = 1
        while name in self.strategies:
            name = f"{base_name} {i}"
            i += 1

        self.strategies[name] = {"weights": {key: 0 for key in self.score_keys}, "predefined": False}
        self.populate_strategy_list(select_name=name)

    def copy_strategy(self):
        if not self.current_strategy_name: return
        self.save_current_editor_state()

        base_name = f"{self.current_strategy_name} (Copy)"
        name = base_name
        i = 1
        while name in self.strategies:
            name = f"{base_name} {i}"
            i += 1

        original_strategy = self.strategies[self.current_strategy_name]
        self.strategies[name] = {
            "weights": original_strategy["weights"].copy(),
            "predefined": False
        }
        self.populate_strategy_list(select_name=name)

    def delete_strategy(self):
        if not self.current_strategy_name or self.strategies[self.current_strategy_name].get("predefined", False):
            return

        reply = QMessageBox.question(self, "Confirm Deletion", f"Are you sure you want to delete '{self.current_strategy_name}'?")
        if reply == QMessageBox.Yes:
            del self.strategies[self.current_strategy_name]
            self.current_strategy_name = None
            self.populate_strategy_list()

    def on_accept(self):
        self.save_current_editor_state()

        invalid_strategies = []
        for name, data in self.strategies.items():
            total_weight = sum(data.get("weights", {}).values())
            if not (0.999 < total_weight < 1.001):
                invalid_strategies.append(name)

        if invalid_strategies:
            QMessageBox.warning(self, "Invalid Weights", "The following strategies do not have weights summing to 100%:\n\n" + "\n".join(invalid_strategies))
            return

        # Check for duplicate names
        if len(self.strategies.keys()) != len(set(self.strategies.keys())):
             QMessageBox.warning(self, "Duplicate Names", "Strategy names must be unique.")
             return

        self.accept()

    def get_updated_strategies(self):
        return self.strategies

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Rectifex - Global Stock Screener"); self.setGeometry(100, 100, 1200, 800); self.result_df = None
        self.current_tickers = screener_engine.get_global_top_tickers()
        self.scan_errors = []
        self.api_key = load_api_key()
        self.chart_cache = {}
        self.search_col_indices = None # To cache search column indices

        main_layout = QVBoxLayout(); top_bar_layout = QHBoxLayout(); controls_layout = QHBoxLayout()
        self.strategy_label = QLabel("Analysis Strategy:")
        self.strategy_definitions = screener_engine.get_strategy_definitions()
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(self.strategy_definitions.keys())
        self.strategy_combo.currentTextChanged.connect(self.update_strategy_tooltip)
        self.update_strategy_tooltip(self.strategy_combo.currentText())

        self.scan_button = QPushButton("Start Scan")
        self.manage_tickers_button = QPushButton("Manage Tickers")
        self.save_csv_button = QPushButton("Save as CSV"); self.save_csv_button.setEnabled(False)

        action_layout = QHBoxLayout()
        action_layout.addLayout(controls_layout)

        action_layout.addStretch()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search by Name or Ticker...")
        self.search_bar.setMaximumWidth(300)
        self.search_bar.textChanged.connect(self.filter_results_table)
        self.search_bar.setEnabled(False) # Initially disabled
        action_layout.addWidget(self.search_bar)

        self.settings_button = QPushButton("Settings")
        self.help_button = QPushButton("Help")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.help_button.clicked.connect(self.show_help_dialog)
        action_layout.addWidget(self.settings_button)
        action_layout.addWidget(self.help_button)

        self.scan_button.clicked.connect(self.start_scan)
        self.manage_tickers_button.clicked.connect(self.open_ticker_dialog)
        self.save_csv_button.clicked.connect(self.save_as_csv)

        controls_layout.addWidget(self.strategy_label); controls_layout.addWidget(self.strategy_combo)
        controls_layout.addWidget(self.scan_button); controls_layout.addWidget(self.manage_tickers_button)
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

    def start_scan(self):
        self.scan_button.setEnabled(False); self.save_csv_button.setEnabled(False); self.search_bar.setEnabled(False); self.search_bar.clear(); self.progress_bar.setValue(0); self.progress_bar.setVisible(True); self.results_table.setRowCount(0)
        self.search_col_indices = None # Reset cached column indices
        data_source = "FMP" if self.api_key else "yfinance"
        self.statusBar().showMessage(f"Starting scan for {len(self.current_tickers)} tickers using {data_source}...")
        self.worker = ScanWorker(self.strategy_combo.currentText().replace(" ", "_"), self.current_tickers, self.api_key)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.scan_finished)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        data_source = "FMP" if self.api_key else "yfinance"
        self.statusBar().showMessage(f"Scanning with {data_source}... {value}%")

    def scan_finished(self, results):
        self.progress_bar.setVisible(False); self.scan_button.setEnabled(True)
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
    app = QApplication(sys.argv); app.setDesktopFileName("io.github.BioVisualizer.Rectifex"); window = MainWindow(); window.show(); sys.exit(app.exec())
