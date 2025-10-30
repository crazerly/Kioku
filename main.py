import sys
import ctypes

from windows.decks import DecksWindow

try:
    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    QT_BACKEND = "PySide6"
except Exception:
    try:
        from PyQt5.QtCore import QSize
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QIcon
        QT_BACKEND = "PyQt5"
    except Exception:
        raise RuntimeError("PySide6 or PyQt5 is required. Install with `pip install PySide6` or `pip install PyQt5`.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_icon = QIcon()
    app_icon.addFile('icon\\lightbulb.png', QSize(16,16))
    app.setWindowIcon(app_icon)
    win = DecksWindow()
    win.show()
    app.exec()