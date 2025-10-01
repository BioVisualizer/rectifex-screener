from PySide6.QtGui import QPalette, QColor

def get_dark_palette() -> QPalette:
    """Returns a QPalette for a modern dark theme."""
    palette = QPalette()

    # Base colors
    palette.setColor(QPalette.ColorRole.Window, QColor(35, 39, 46))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 221, 222))
    palette.setColor(QPalette.ColorRole.Base, QColor(28, 31, 36))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(44, 49, 58))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(35, 39, 46))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(220, 221, 222))

    # Text and highlights
    palette.setColor(QPalette.ColorRole.Text, QColor(220, 221, 222))
    palette.setColor(QPalette.ColorRole.Button, QColor(44, 49, 58))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 221, 222))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 64, 64)) # For alerts

    # Interactive elements
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(240, 240, 240))

    # Disabled state
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))

    return palette

def get_light_palette() -> QPalette:
    """Returns a QPalette for a modern light theme."""
    palette = QPalette()

    # Base colors
    palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(233, 233, 233))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))

    # Text and highlights
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button, QColor(225, 225, 225))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))

    # Interactive elements
    palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    # Disabled state
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(160, 160, 160))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(160, 160, 160))

    return palette