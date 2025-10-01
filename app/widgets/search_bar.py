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
            # Display format: "ASML (ASML Holding N.V.)"
            display_text = f"{item['symbol']} ({item['name']})"
            standard_item = QStandardItem(display_text)
            standard_item.setData(item['symbol'], Qt.ItemDataRole.UserRole) # Store symbol separately
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

        # Timer to delay search, preventing too many requests while typing
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300) # 300ms delay
        self.search_timer.timeout.connect(self.perform_search)

        self.search_input.textChanged.connect(self.on_text_changed)
        self.search_input.returnPressed.connect(self.on_return_pressed)

        # Setup the completer
        self.completer = QCompleter(self)
        self.completer_model = SearchCompleterModel(self)
        self.completer.setModel(self.completer_model)
        self.completer.setPopup(QListView()) # Use a list view for the popup
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.activated.connect(self.on_completer_activated)

        self.search_input.setCompleter(self.completer)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.search_input)
        self.setLayout(layout)

    def on_text_changed(self, text: str):
        """When text changes, restart the search timer."""
        if len(text) > 1: # Start searching after 2 characters
            self.search_timer.start()
        else:
            self.completer.popup().hide()

    @Slot()
    def perform_search(self):
        """
        Executes the fuzzy search and updates the completer model.
        This should be run in a separate thread in a real-world app to avoid UI stutters,
        but for now, rapidfuzz is fast enough for direct calls with a timer.
        """
        query = self.search_input.text()
        logging.info(f"Performing async-like search for: {query}")
        try:
            results = search_symbol(query, top_k=5)
            self.completer_model.update_results(results)
            self.completer.complete()
        except Exception as e:
            logging.error(f"Error during symbol search: {e}")

    @Slot()
    def on_return_pressed(self):
        """
        Handles the return key press event. If completer is not active,
        emits the raw text as the selected symbol.
        """
        if not self.completer.popup().isVisible():
            symbol = self.search_input.text().strip().upper()
            if symbol:
                logging.info(f"Return pressed, emitting symbol: {symbol}")
                self.symbolSelected.emit(symbol)

    @Slot(str)
    def on_completer_activated(self, text: str):
        """
        Handles the selection of an item from the completer list.
        The `text` is the display text, so we extract the symbol from it.
        """
        # A bit of a hack to get the original symbol back from the display text
        symbol = text.split(" ")[0]
        logging.info(f"Completer activated, emitting symbol: {symbol}")
        self.symbolSelected.emit(symbol)
        self.search_input.clear() # Clear input after selection
        self.completer.popup().hide()