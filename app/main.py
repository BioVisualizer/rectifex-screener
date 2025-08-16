# =============================================================================
# Aethelon - GUI
# VERSION 56.0: "International Release"
#
# =============================================================================

import sys
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QComboBox, QLabel,
                             QTableWidget, QTableWidgetItem, QProgressBar, QHeaderView,
                             QMessageBox, QFileDialog, QDialog, QTabWidget, QTextEdit)
from PySide6.QtCore import QThread, Signal, Qt

import screener_engine
from help_texts import HELP_TEXT_DE, HELP_TEXT_EN

class ScanWorker(QThread):
    progress = Signal(int); finished = Signal(object)
    def __init__(self, strategy): super().__init__(); self.strategy = strategy
    def run(self): self.finished.emit(screener_engine.run_complete_screener(self.strategy, self.progress))

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help & Information")
        self.setMinimumSize(700, 500)
        self.tab_widget = QTabWidget()
        de_tab = QTextEdit(); de_tab.setReadOnly(True); de_tab.setMarkdown(HELP_TEXT_DE)
        self.tab_widget.addTab(de_tab, "Deutsch")
        en_tab = QTextEdit(); en_tab.setReadOnly(True); en_tab.setMarkdown(HELP_TEXT_EN)
        self.tab_widget.addTab(en_tab, "English")
        layout = QVBoxLayout(); layout.addWidget(self.tab_widget); self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Rectifex - Global Stock Screener"); self.setGeometry(100, 100, 1200, 800); self.result_df = None
        main_layout = QVBoxLayout(); top_bar_layout = QHBoxLayout(); controls_layout = QHBoxLayout()
        self.strategy_label = QLabel("Analysis Strategy:")
        self.strategy_combo = QComboBox(); self.strategy_combo.addItems(["Balanced", "High Growth", "Deep Value", "Quality Dividend"])
        self.scan_button = QPushButton("Start Scan")
        self.save_csv_button = QPushButton("Save as CSV"); self.save_csv_button.setEnabled(False)
        self.help_button = QPushButton("Help")
        self.scan_button.clicked.connect(self.start_scan)
        self.save_csv_button.clicked.connect(self.save_as_csv)
        self.help_button.clicked.connect(self.show_help_dialog)
        controls_layout.addWidget(self.strategy_label); controls_layout.addWidget(self.strategy_combo); controls_layout.addWidget(self.scan_button); controls_layout.addWidget(self.save_csv_button)
        top_bar_layout.addLayout(controls_layout); top_bar_layout.addStretch(); top_bar_layout.addWidget(self.help_button)
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False)
        self.results_table = QTableWidget(); self.results_table.setEditTriggers(QTableWidget.NoEditTriggers); self.results_table.setSortingEnabled(True); self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        main_layout.addLayout(top_bar_layout); main_layout.addWidget(self.progress_bar); main_layout.addWidget(self.results_table)
        central_widget = QWidget(); central_widget.setLayout(main_layout); self.setCentralWidget(central_widget)

    def start_scan(self):
        self.scan_button.setEnabled(False); self.save_csv_button.setEnabled(False); self.progress_bar.setValue(0); self.progress_bar.setVisible(True); self.results_table.setRowCount(0)
        self.worker = ScanWorker(self.strategy_combo.currentText().replace(" ", "_")); self.worker.progress.connect(self.update_progress); self.worker.finished.connect(self.scan_finished); self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def scan_finished(self, results):
        self.progress_bar.setVisible(False); self.scan_button.setEnabled(True)
        if not results:
             QMessageBox.warning(self, "Error", "An unexpected error occurred."); return
        df, summary_text = results
        QMessageBox.information(self, "Scan Finished", summary_text.replace("<br>", "\n").replace("<hr>", "\n------------------------------------\n").replace("<b>", "").replace("</b>", ""))
        if df.empty: return
        self.result_df = df
        self.save_csv_button.setEnabled(True)
        self.populate_table(df)

    def populate_table(self, df):
        self.results_table.setSortingEnabled(False)
        df_display = df.rename(columns={'MarketCapUSD': 'MarketCap (USD)'})
        self.results_table.setRowCount(len(df_display)); self.results_table.setColumnCount(len(df_display.columns)); self.results_table.setHorizontalHeaderLabels(df_display.columns)
        for r_idx, (index, row) in enumerate(df_display.iterrows()):
            for c_idx, col_name in enumerate(df_display.columns):
                original_col_name = 'MarketCapUSD' if col_name == 'MarketCap (USD)' else col_name
                raw_value = df.iloc[r_idx][original_col_name]
                item = QTableWidgetItem()
                if isinstance(raw_value, (int, float)) and not pd.isna(raw_value): item.setData(Qt.EditRole, raw_value)
                display_text = "N/A"
                if not pd.isna(raw_value):
                    if col_name == 'MarketCap (USD)': display_text = f'${raw_value/1e9:,.0f}B'
                    elif '_Score' in col_name or "Value" in col_name or "Growth" in col_name or col_name in ["Balanced", "PE", "ROE_Avg3Y", "RevGrowth3YCAGR"]: display_text = f'{raw_value:,.1f}'
                    elif col_name == 'PB': display_text = f'{raw_value:,.2f}'
                    elif col_name == 'DivYield': display_text = f'{raw_value:,.2f}%'
                    else: display_text = str(raw_value)
                item.setText(display_text); self.results_table.setItem(r_idx, c_idx, item)
        self.results_table.resizeColumnsToContents(); self.results_table.setSortingEnabled(True)

    def save_as_csv(self):
        if self.result_df is None: return
        path, _ = QFileDialog.getSaveFileName(self, "Save as CSV", "aethelon_scan.csv", "CSV Files (*.csv)")
        if path:
            try:
                self.result_df.to_csv(path, index=False, decimal='.', sep=',')
                QMessageBox.information(self, "Success", f"Data saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error saving file:\n{e}")

    def show_help_dialog(self):
        dialog = HelpDialog(self); dialog.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setDesktopFileName("io.github.Rectifex"); window = MainWindow(); window.show(); sys.exit(app.exec())
