import re
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTextEdit, QFileDialog, QMessageBox)

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
