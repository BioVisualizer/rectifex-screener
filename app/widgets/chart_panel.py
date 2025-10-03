from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QLabel, QPushButton,
                               QHBoxLayout, QGroupBox, QFormLayout, QCheckBox, QFrame, QSizePolicy)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Slot, Qt
from typing import List

# Import the Signal dataclass for type hinting
from core.signals.engine import Signal

class ChartPanel(QWidget):
    """
    The right-hand panel of the UI, displaying the chart and its analysis controls.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_chart_pixmap = None

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 0, 0)

        # --- Chart Display Area ---
        self.chart_view = QLabel("Select a stock to display the chart.")
        self.chart_view.setMinimumHeight(400)
        self.chart_view.setFrameShape(QFrame.Shape.StyledPanel)

        # This is the critical fix: prevent the label from expanding the layout.
        # It will now ignore its own size hint and fill the available space.
        self.chart_view.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.chart_view.setScaledContents(True)

        # --- Stale Cache Badge ---
        self.stale_badge = QLabel("Stale Cache")
        self.stale_badge.setObjectName("StaleBadge")
        self.stale_badge.setVisible(False)

        chart_layout = QVBoxLayout()
        chart_layout.addWidget(self.chart_view)
        chart_layout.addWidget(self.stale_badge, alignment=Qt.AlignRight)


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
        import os
        if image_path and os.path.exists(image_path):
            self.current_chart_pixmap = QPixmap(image_path)
            self.chart_view.setPixmap(self.current_chart_pixmap)
        else:
            self.chart_view.setText(f"Failed to load chart.\nPath: '{image_path}'")
            self.current_chart_pixmap = None

    @Slot(bool)
    def set_stale_badge_visibility(self, visible: bool):
        """Shows or hides the 'Stale Cache' badge."""
        self.stale_badge.setVisible(visible)

    @Slot(dict)
    def update_overview(self, metadata: dict):
        """Populates the overview tab with fundamental data, handling None values gracefully."""
        # Clear old data
        while self.overview_layout.rowCount() > 0:
            self.overview_layout.removeRow(0)

        # Helper to format the data, returning "N/A" if the value is None
        def format_value(value, formatter):
            return formatter(value) if value is not None else "N/A"

        # Add new data with robust None-checking
        self.overview_layout.addRow("Name:", QLabel(format_value(metadata.get('longName'), str)))
        self.overview_layout.addRow("Exchange:", QLabel(format_value(metadata.get('exchange'), str)))

        market_cap = metadata.get('marketCap')
        if market_cap is not None:
            if market_cap >= 1e12:
                market_cap_str = f"${market_cap / 1e12:.2f}T"
            else:
                market_cap_str = f"${market_cap / 1e9:.2f}B"
        else:
            market_cap_str = "N/A"
        self.overview_layout.addRow("Market Cap:", QLabel(market_cap_str))

        self.overview_layout.addRow("Trailing P/E:", QLabel(format_value(metadata.get('trailingPE'), lambda v: f"{v:.2f}")))
        self.overview_layout.addRow("Forward P/E:", QLabel(format_value(metadata.get('forwardPE'), lambda v: f"{v:.2f}")))
        self.overview_layout.addRow("Div. Yield:", QLabel(format_value(metadata.get('dividendYield'), lambda v: f"{v * 100:.2f}%")))

    @Slot(list)
    def update_signals(self, signals: List[Signal]):
        """Populates the signals tab with the latest analysis."""
        # Clear old widgets from the layout
        while self.signals_layout.count():
            child = self.signals_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not signals:
            self.signals_layout.addWidget(QLabel("No recent signals found."))
            return

        # Sort signals by date, most recent first
        sorted_signals = sorted(signals, key=lambda s: s.ts, reverse=True)

        for signal in sorted_signals:
            # Create a visually distinct group box for each signal
            signal_box = QGroupBox(f"{signal.ts.strftime('%Y-%m-%d')}: {signal.label}")
            signal_box.setObjectName(f"SignalCard_{signal.direction.lower()}")

            form_layout = QFormLayout(signal_box)
            form_layout.addRow("Direction:", QLabel(signal.direction.capitalize()))
            form_layout.addRow("Confidence:", QLabel(f"{signal.confidence:.0f} / 100"))

            reason_label = QLabel(signal.reason)
            reason_label.setWordWrap(True)
            form_layout.addRow("Reason:", reason_label)

            self.signals_layout.addWidget(signal_box)

        self.signals_layout.addStretch(1)