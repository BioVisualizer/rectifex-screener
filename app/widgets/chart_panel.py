from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QGroupBox,
    QFormLayout,
    QCheckBox,
    QFrame,
    QSizePolicy,
    QDialog,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Slot, Qt, Signal
from typing import List

# Import the Signal dataclass for type hinting
from core.signals.engine import Signal as SignalModel


class ChartLabel(QLabel):
    """Specialised QLabel that emits a signal on double-click."""

    doubleClicked = Signal()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.doubleClicked.emit()


class ChartPopupWindow(QDialog):
    """Separate window that shows the chart and scales it with the window size."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chart Viewer")
        self.resize(1200, 800)
        self.setModal(False)
        self.setSizeGripEnabled(True)
        self._chart_pixmap = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.label = QLabel("No chart available.")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        layout.addWidget(self.label)

    def set_chart_pixmap(self, pixmap: QPixmap | None):
        self._chart_pixmap = pixmap
        self._update_display()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()

    def _update_display(self):
        if not self._chart_pixmap:
            self.label.clear()
            self.label.setText("No chart available.")
            return

        target_size = self.label.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            return

        scaled = self._chart_pixmap.scaled(
            target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.label.setPixmap(scaled)


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
        self.chart_view = ChartLabel("Select a stock to display the chart.")
        self.chart_view.setMinimumHeight(520)
        self.chart_view.setFrameShape(QFrame.Shape.StyledPanel)
        self.chart_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # --- Stale Cache Badge ---
        self.stale_badge = QLabel("Stale Cache")
        self.stale_badge.setObjectName("StaleBadge")
        self.stale_badge.setVisible(False)

        chart_layout = QVBoxLayout()
        chart_layout.addWidget(self.chart_view, stretch=1)
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

        for checkbox in (self.cb_ema_ribbon, self.cb_bbands, self.cb_vwap, self.cb_rsi, self.cb_macd):
            checkbox.setChecked(True)
        indicators_layout.addRow(self.cb_ema_ribbon)
        indicators_layout.addRow(self.cb_bbands)
        indicators_layout.addRow(self.cb_vwap)
        indicators_layout.addRow(self.cb_rsi)
        indicators_layout.addRow(self.cb_macd)

        # Fibonacci Tab
        self.fib_tab = QWidget()
        fib_layout = QFormLayout(self.fib_tab)
        self.cb_fib_levels = QCheckBox("Show Fibonacci Levels")
        self.cb_fib_levels.setChecked(True)
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
        main_layout.addLayout(chart_layout, stretch=3)
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.tab_widget, stretch=2)
        self.setLayout(main_layout)

        # --- Signals ---
        for checkbox in (
            self.cb_ema_ribbon,
            self.cb_bbands,
            self.cb_vwap,
            self.cb_rsi,
            self.cb_macd,
            self.cb_fib_levels,
        ):
            checkbox.toggled.connect(self._emit_chart_options)

        self.reload_button.clicked.connect(self._on_reload_clicked)
        self.chart_view.doubleClicked.connect(self._open_chart_popup)

        self.chart_popup = ChartPopupWindow(self)

    chartOptionsChanged = Signal(dict)
    reloadRequested = Signal()

    def get_chart_options(self) -> dict:
        """Return the current state of the chart related controls."""
        return {
            "show_ema_ribbon": self.cb_ema_ribbon.isChecked(),
            "show_bbands": self.cb_bbands.isChecked(),
            "show_vwap": self.cb_vwap.isChecked(),
            "show_rsi": self.cb_rsi.isChecked(),
            "show_macd": self.cb_macd.isChecked(),
            "show_fib": self.cb_fib_levels.isChecked(),
            "bb_len": 20,
            "bb_std": 2.0,
        }

    @Slot()
    def _emit_chart_options(self):
        """Notify listeners whenever the chart options change."""
        self.chartOptionsChanged.emit(self.get_chart_options())

    @Slot()
    def _on_reload_clicked(self):
        """Request a live reload of the currently displayed symbol."""
        self.reloadRequested.emit()

    @Slot(str)
    def update_chart(self, image_path: str):
        """Loads and displays the chart from the given image path."""
        import os
        if image_path and os.path.exists(image_path):
            self.current_chart_pixmap = QPixmap(image_path)
            self._update_chart_display()
            if self.chart_popup:
                self.chart_popup.set_chart_pixmap(self.current_chart_pixmap)
        else:
            self.chart_view.clear()
            self.chart_view.setText(f"Failed to load chart.\nPath: '{image_path}'")
            self.current_chart_pixmap = None
            if self.chart_popup:
                self.chart_popup.set_chart_pixmap(None)

    @Slot(bool)
    def set_stale_badge_visibility(self, visible: bool):
        """Shows or hides the 'Stale Cache' badge."""
        self.stale_badge.setVisible(visible)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_chart_display()

    def _update_chart_display(self):
        """Scale the current chart pixmap while keeping its aspect ratio."""
        if not self.current_chart_pixmap:
            return

        scaled = self.current_chart_pixmap.scaled(
            self.chart_view.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.chart_view.setPixmap(scaled)

    @Slot()
    def _open_chart_popup(self):
        """Open the detached chart viewer window."""
        if not self.current_chart_pixmap:
            return

        self.chart_popup.set_chart_pixmap(self.current_chart_pixmap)
        self.chart_popup.show()
        self.chart_popup.raise_()
        self.chart_popup.activateWindow()

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
    def update_signals(self, signals: List[SignalModel]):
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