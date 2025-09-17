import configparser
from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox

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

# --- Dialog ---

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
