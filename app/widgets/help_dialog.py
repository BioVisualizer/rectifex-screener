from PySide6.QtWidgets import QDialog, QTabWidget, QTextEdit, QVBoxLayout
from help_texts import HELP_TEXT_DE, HELP_TEXT_EN

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
