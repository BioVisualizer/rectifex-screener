from PySide6.QtWidgets import QWidget, QLineEdit, QVBoxLayout, QListView, QCompleter
from PySide6.QtCore import QTimer, Slot, Signal, QAbstractListModel, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem
import logging

from core.data.universe import search_symbol

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SearchCompleterModel(QStandardItemModel):
    """Custom model to display search results in the completer."""
    def __init__(self, parent=None):
        super().__init__(parent)

    def update_results(self, results):
        self.clear()
        for item in results:
            display_text = f"{item['symbol']} ({item['name']})"
            standard_item = QStandardItem(display_text)
            standard_item.setData(item['symbol'], Qt.ItemDataRole.UserRole)
            self.appendRow(standard_item)

class SearchBar(QWidget):
    """
    A custom search bar widget with asynchronous autocompletion for stock symbols.
    """
    symbolSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search Ticker or Name...")

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)
        self.search_timer.timeout.connect(self.perform_search)

        self.search_input.textChanged.connect(self.on_text_changed)
        self.search_input.returnPressed.connect(self.on_return_pressed)

        self.completer = QCompleter(self)
        self.completer_model = SearchCompleterModel(self)
        self.completer.setModel(self.completer_model)
        self.completer.setPopup(QListView())
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.activated.connect(self.on_completer_activated)

        self.search_input.setCompleter(self.completer)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.search_input)
        self.setLayout(layout)

    def _submit_selection(self, symbol: str):
        """Unified method to emit the selected symbol and clean up the UI."""
        symbol = symbol.strip().upper()
        if symbol:
            logging.info(f"Submitting selected symbol: {symbol}")
            self.symbolSelected.emit(symbol)
            self.search_input.clear()
            self.completer.popup().hide()

    def get_search_text(self) -> str:
        """Return the current raw text in the search input."""
        return self.search_input.text().strip()

    def on_text_changed(self, text: str):
        """When text changes, restart the search timer."""
        if len(text) > 0:
            self.search_timer.start()
        else:
            self.completer.popup().hide()

    @Slot()
    def perform_search(self):
        """Executes the fuzzy search and updates the completer model."""
        query = self.search_input.text()
        if not query: return
        logging.info(f"Performing search for: {query}")
        try:
            results = search_symbol(query, top_k=7)
            self.completer_model.update_results(results)
            if self.completer_model.rowCount() > 0:
                self.completer.complete()
            else:
                self.completer.popup().hide()
        except Exception as e:
            logging.error(f"Error during symbol search: {e}")

    @Slot()
    def on_return_pressed(self):
        """
        Handles the return key press event. This is now the primary way to
        submit a ticker that is typed manually. The completer's 'activated'
        signal handles selections from the popup list.
        """
        self._submit_selection(self.search_input.text())

    @Slot()
    def on_completer_activated(self, index):
        """Handles the selection of an item from the completer list."""
        # The 'activated' signal can return an index (QModelIndex) or a string.
        # We handle both cases to be robust.
        if isinstance(index, str):
            symbol = index.split(" ")[0]
        else:
            symbol = self.completer_model.data(index, Qt.ItemDataRole.UserRole)

        self._submit_selection(symbol)