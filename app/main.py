# =============================================================================
# Rectifex - GUI
# VERSION 57.0: "Stability & Polish"
# =============================================================================

import sys
import pandas as pd
import webbrowser
import re
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QComboBox, QLabel,
                             QTableWidget, QTableWidgetItem, QProgressBar, QHeaderView,
                             QMessageBox, QFileDialog, QDialog, QTabWidget, QTextEdit, QStatusBar, QMenu, QStyledItemDelegate)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QAction, QColor

import screener_engine
from help_texts import HELP_TEXT_DE, HELP_TEXT_EN

class ScoreDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        score = index.data(Qt.EditRole)
        # Ensure we only handle cells with valid score data
        if not isinstance(score, (int, float)) or pd.isna(score):
            super().paint(painter, option, index)
            return

        score = max(0, min(100, score))

        # Define colors for the three-tier system
        red = QColor("#ffcdd2")
        yellow = QColor("#fff9c4")
        green = QColor("#c8e6c9")

        # Determine color based on score boundaries
        if score >= 70:
            color = green
        elif score >= 40:
            color = yellow
        else:
            color = red

        # Draw the background bar
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)

        # Calculate bar width based on score
        padding = 3
        bar_rect = option.rect.adjusted(padding, padding, -padding, -padding)
        if bar_rect.width() > 0 and bar_rect.height() > 0:
            bar_width = int(bar_rect.width() * (score / 100.0))
            painter.drawRect(bar_rect.left(), bar_rect.top(), bar_width, bar_rect.height())

        # Draw the text on top
        display_text = index.data(Qt.DisplayRole)
        # Use the default text color from the widget's palette
        painter.setPen(option.palette.color(option.palette.Text))
        # Right-align text with some padding
        text_rect = option.rect.adjusted(0, 0, -padding * 2, 0)
        painter.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, display_text)

        painter.restore()

class ScanWorker(QThread):
    progress = Signal(int); finished = Signal(object)
    def __init__(self, strategy, tickers):
        super().__init__()
        self.strategy = strategy
        self.tickers = tickers
    def run(self):
        self.finished.emit(screener_engine.run_complete_screener(self.strategy, self.tickers, self.progress))

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
            log_tab = QTextEdit()
            log_tab.setReadOnly(True)
            log_tab.setPlainText("\n".join(error_log))
            self.tab_widget.addTab(log_tab, "Scan Log")
            self.tab_widget.setCurrentWidget(log_tab)

        layout = QVBoxLayout(); layout.addWidget(self.tab_widget); self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Rectifex - Global Stock Screener"); self.setGeometry(100, 100, 1200, 800); self.result_df = None
        self.current_tickers = screener_engine.get_global_top_tickers()
        self.scan_errors = []

        main_layout = QVBoxLayout(); top_bar_layout = QHBoxLayout(); controls_layout = QHBoxLayout()
        self.strategy_label = QLabel("Analysis Strategy:")
        self.strategy_definitions = screener_engine.get_strategy_definitions()
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(self.strategy_definitions.keys())
        self.strategy_combo.currentTextChanged.connect(self.update_strategy_tooltip)
        self.update_strategy_tooltip(self.strategy_combo.currentText())

        self.scan_button = QPushButton("Start Scan")
        self.manage_tickers_button = QPushButton("Manage Tickers")
        self.save_csv_button = QPushButton("Save as CSV")
        self.save_csv_button.setEnabled(False)
        self.help_button = QPushButton("Help")

        self.scan_button.clicked.connect(self.start_scan)
        self.manage_tickers_button.clicked.connect(self.open_ticker_dialog)
        self.save_csv_button.clicked.connect(self.save_as_csv)
        self.help_button.clicked.connect(self.show_help_dialog)

        controls_layout.addWidget(self.strategy_label)
        controls_layout.addWidget(self.strategy_combo)
        controls_layout.addWidget(self.scan_button)
        controls_layout.addWidget(self.manage_tickers_button)
        controls_layout.addWidget(self.save_csv_button)

        top_bar_layout.addLayout(controls_layout); top_bar_layout.addStretch(); top_bar_layout.addWidget(self.help_button)
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False)
        self.results_table = QTableWidget(); self.results_table.setEditTriggers(QTableWidget.NoEditTriggers); self.results_table.setSortingEnabled(True); self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.results_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self.show_context_menu)
        main_layout.addLayout(top_bar_layout); main_layout.addWidget(self.progress_bar); main_layout.addWidget(self.results_table)
        central_widget = QWidget(); central_widget.setLayout(main_layout); self.setCentralWidget(central_widget)
        self.score_delegate = ScoreDelegate(self)
        self.setStatusBar(QStatusBar(self))

    def open_ticker_dialog(self):
        dialog = TickerManagerDialog(self.current_tickers, self)
        if dialog.exec():
            self.current_tickers = dialog.get_tickers()
            self.statusBar().showMessage(f"Ticker list updated to {len(self.current_tickers)} tickers.", 5000)

    def start_scan(self):
        self.scan_button.setEnabled(False); self.save_csv_button.setEnabled(False); self.progress_bar.setValue(0); self.progress_bar.setVisible(True); self.results_table.setRowCount(0)
        self.statusBar().showMessage(f"Starting scan for {len(self.current_tickers)} tickers...")
        self.worker = ScanWorker(self.strategy_combo.currentText().replace(" ", "_"), self.current_tickers)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.scan_finished)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        self.statusBar().showMessage(f"Scanning... {value}%")

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
        self.populate_table(df)

    def populate_table(self, df):
        self.results_table.setSortingEnabled(False)
        df_display = df.rename(columns={'MarketCapUSD': 'MarketCap (USD)'})
        self.results_table.setRowCount(len(df_display)); self.results_table.setColumnCount(len(df_display.columns)); self.results_table.setHorizontalHeaderLabels(df_display.columns)

        strategy_col_name = self.strategy_combo.currentText().replace(" ", "_")
        for c_idx, col_name in enumerate(df_display.columns):
            if '_Score' in col_name or col_name == strategy_col_name:
                self.results_table.setItemDelegateForColumn(c_idx, self.score_delegate)
            else:
                self.results_table.setItemDelegateForColumn(c_idx, None)

        for r_idx, (index, row) in enumerate(df_display.iterrows()):
            for c_idx, col_name in enumerate(df_display.columns):
                original_col_name = 'MarketCapUSD' if col_name == 'MarketCap (USD)' else col_name
                raw_value = df.iloc[r_idx][original_col_name]
                item = QTableWidgetItem()
                if isinstance(raw_value, (int, float)) and not pd.isna(raw_value):
                    item.setData(Qt.EditRole, raw_value)
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                display_text = "N/A"
                if not pd.isna(raw_value):
                    if col_name == 'MarketCap (USD)': display_text = f'${raw_value/1e9:,.0f}B'
                    elif '_Score' in col_name or "Value" in col_name or "Growth" in col_name or col_name in ["Balanced", "PE", "ROE_Avg3Y", "RevGrowth3YCAGR"]: display_text = f'{raw_value:,.1f}'
                    elif col_name == 'PB': display_text = f'{raw_value:,.2f}'
                    elif col_name == 'DivYield': display_text = f'{raw_value:,.2f}%'
                    else: display_text = str(raw_value)
                item.setText(display_text); self.results_table.setItem(r_idx, c_idx, item)
        self.results_table.resizeColumnsToContents(); self.results_table.setSortingEnabled(True)

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
            weights = self.strategy_definitions[strategy_name]
            tooltip_parts = [f"<b>{strategy_name} Strategy Weights:</b>", "<hr>"]
            for score, weight in weights.items():
                clean_score = score.replace('_', ' ')
                percent = f"{weight:.0%}"
                tooltip_parts.append(f"• {clean_score}: {percent}")
            self.strategy_combo.setToolTip("<br>".join(tooltip_parts))

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setDesktopFileName("io.github.BioVisualizer.Rectifex"); window = MainWindow(); window.show(); sys.exit(app.exec())
