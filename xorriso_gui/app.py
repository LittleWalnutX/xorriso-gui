import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from xorriso_gui.main_window import MainWindow


_ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon.svg")


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("xorriso-gui")
    app.setApplicationName("xorriso-gui")
    app.setApplicationDisplayName("xorriso-gui — ISO 镜像管理器")
    if os.path.exists(_ICON_PATH):
        app.setWindowIcon(QIcon(_ICON_PATH))

    style_sheet = """
    QTreeView {
        font-size: 13px;
    }
    QTreeView::item {
        padding: 2px 4px;
    }
    QToolTip {
        background-color: #ffffdc;
        border: 1px solid #c0c0c0;
        padding: 4px;
    }
    """
    app.setStyleSheet(style_sheet)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()