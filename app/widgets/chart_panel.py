from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QLabel, QPushButton,
                               QHBoxLayout, QGroupBox, QFormLayout, QCheckBox, QFrame)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Slot

class ChartPanel(QWidget):
    """
    The right-hand panel of the UI, displaying the chart and its analysis controls.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 0, 0)

        # --- Chart Display Area ---
        self.chart_view = QLabel("Select a stock to display the chart.")
        self.chart_view.setMinimumHeight(400)
        self.chart_view.setFrameShape(QFrame.Shape.StyledPanel)
        self.chart_view.setScaledContents(True)

        # --- Stale Cache Badge ---
        self.stale_badge = QLabel("Stale Cache")
        self.stale_badge.setObjectName("StaleBadge")
        self.stale_badge.setVisible(False)

        chart_layout = QVBoxLayout()
        chart_layout.addWidget(self.chart_view)
        chart_layout.addWidget(self.stale_badge, alignment=self.stale_badge.alignment() | self.stale_badge.alignmentFlag.AlignTop)


        # --- Control Tabs ---
        self.tab_widget = QTabWidget()

        # Overview Tab
        self.overview_tab = QWidget()
        self.overview_layout = QFormLayout(self.overview_tab)
        self.overview_layout.addRow("Market Cap:", QLabel("-"))
        self.overview_layout.addRow("P/E Ratio:", QLabel("-"))

        # Indicators Tab
        self.indicators_tab = QWidget()
        indicators_layout = QFormLayout(self.indicators_tab)
        self.cb_ema_ribbon = QCheckBox("EMA Ribbon")
        self.cb_bbands = QCheckBox("Bollinger Bands")
        self.cb_vwap = QCheckBox("VWAP")
        self.cb_rsi = QCheckBox("RSI Pane")
        self.cb_macd = QCheckBox("MACD Pane")
        indicators_layout.addRow(self.cb_ema_ribbon)
        indicators_layout.addRow(self.cb_bbands)
        indicators_layout.addRow(self.cb_vwap)
        indicators_layout.addRow(self.cb_rsi)
        indicators_layout.addRow(self.cb_macd)

        # Fibonacci Tab
        self.fib_tab = QWidget()
        fib_layout = QFormLayout(self.fib_tab)
        self.cb_fib_levels = QCheckBox("Show Fibonacci Levels")
        fib_layout.addRow(self.cb_fib_levels)

        # Signals Tab
        self.signals_tab = QWidget()
        self.signals_layout = QVBoxLayout(self.signals_tab)
        self.signals_layout.addWidget(QLabel("Signals will appear here."))

        self.tab_widget.addTab(self.overview_tab, "Overview")
        self.tab_widget.addTab(self.indicators_tab, "Indicators")
        self.tab_widget.addTab(self.fib_tab, "Fibonacci")
        self.tab_widget.addTab(self.signals_tab, "Signals")

        # --- Toolbar ---
        toolbar_layout = QHBoxLayout()
        self.reload_button = QPushButton("Reload (Live)")
        self.export_button = QPushButton("Export to Excel")
        self.export_button.setEnabled(False) # Disabled until analysis is complete
        toolbar_layout.addWidget(self.reload_button)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.export_button)

        # --- Assembly ---
        main_layout.addLayout(chart_layout)
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

    @Slot(str)
    def update_chart(self, image_path: str):
        """Loads and displays the chart from the given image path."""
        if image_path:
            pixmap = QPixmap(image_path)
            self.chart_view.setPixmap(pixmap)
        else:
            self.chart_view.setText("Failed to load chart.")

    @Slot(bool)
    def set_stale_badge_visibility(self, visible: bool):
        """Shows or hides the 'Stale Cache' badge."""
        self.stale_badge.setVisible(visible)

    @Slot(dict)
    def update_overview(self, metadata: dict):
        """Populates the overview tab with fundamental data."""
        # Clear old data
        while self.overview_layout.rowCount() > 0:
            self.overview_layout.removeRow(0)

        # Add new data
        self.overview_layout.addRow("Name:", QLabel(metadata.get('longName', 'N/A')))
        self.overview_layout.addRow("Exchange:", QLabel(metadata.get('exchange', 'N/A')))
        self.overview_layout.addRow("Market Cap:", QLabel(f"{metadata.get('marketCap', 0) / 1e9:.2f}B" if metadata.get('marketCap') else "N/A"))
        self.overview_layout.addRow("Trailing P/E:", QLabel(str(round(metadata.get('trailingPE', 0), 2)) if metadata.get('trailingPE') else "N/A"))
        self.overview_layout.addRow("Forward P/E:", QLabel(str(round(metadata.get('forwardPE', 0), 2)) if metadata.get('forwardPE') else "N/A"))
        self.overview_layout.addRow("Div. Yield:", QLabel(f"{metadata.get('dividendYield', 0) * 100:.2f}%" if metadata.get('dividendYield') else "N/A"))