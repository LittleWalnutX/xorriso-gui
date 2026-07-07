import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from xorriso_gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("xorriso-gui")
    app.setApplicationName("xorriso-gui")
    app.setApplicationDisplayName("xorriso-gui — ISO 镜像管理器")

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