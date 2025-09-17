from PySide6.QtWidgets import QDialog, QVBoxLayout, QSizePolicy
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class ChartDialog(QDialog):
    """A dialog to display a Matplotlib chart."""
    def __init__(self, fig: Figure, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Technical Analysis Chart")
        self.setMinimumSize(900, 700)
        self.setModal(False) # Allow interacting with main window

        layout = QVBoxLayout()
        canvas = FigureCanvas(fig)
        canvas.setParent(self)

        # Set the size policy to be expanding
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        canvas.updateGeometry()

        layout.addWidget(canvas)

        self.setLayout(layout)
