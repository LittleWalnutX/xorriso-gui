from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTreeView,
                                QHeaderView, QPushButton, QFileDialog,
                                QHBoxLayout, QToolButton)
from PySide6.QtCore import Qt, Signal, QDir
from PySide6.QtWidgets import QFileSystemModel
from PySide6.QtGui import QAction


class DiskPanel(QWidget):
    path_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        hdr = QHBoxLayout()
        self.path_label = QLabel("磁盘文件系统")
        self.path_label.setStyleSheet("padding: 4px; font-weight: bold;")
        hdr.addWidget(self.path_label)
        hdr.addStretch()

        up_btn = QToolButton()
        up_btn.setText("⬆")
        up_btn.setToolTip("向上一层")
        up_btn.clicked.connect(self._go_up)
        hdr.addWidget(up_btn)

        layout.addLayout(hdr)

        self._model = QFileSystemModel(self)
        self._model.setRootPath(QDir.rootPath())
        self._model.setFilter(
            QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot | QDir.Hidden
        )
        self._model.setReadOnly(True)

        self.tree = QTreeView(self)
        self.tree.setModel(self._model)
        self.tree.setRootIndex(self._model.index(QDir.homePath()))
        self.tree.setSelectionMode(QTreeView.ExtendedSelection)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(False)
        self.tree.setDragDropMode(QTreeView.DragOnly)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.AscendingOrder)
        self.tree.setAnimated(False)
        self.tree.setIndentation(16)
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.setItemsExpandable(True)
        self.tree.setColumnHidden(1, True)
        self.tree.setColumnHidden(2, True)
        self.tree.setColumnHidden(3, True)

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        self.tree.clicked.connect(self._on_clicked)
        self.tree.doubleClicked.connect(self._on_double_clicked)

        layout.addWidget(self.tree)

        self.path_label.setText(QDir.homePath())

    def _go_up(self):
        current = self._model.filePath(self.tree.rootIndex())
        parent = QDir(current)
        parent.cdUp()
        self.tree.setRootIndex(self._model.index(parent.absolutePath()))
        self.path_label.setText(parent.absolutePath())

    def _on_clicked(self, index):
        path = self._model.filePath(index)
        self.path_label.setText(path)

    def _on_double_clicked(self, index):
        path = self._model.filePath(index)
        file_info = self._model.fileInfo(index)
        if file_info.isDir():
            self.tree.setRootIndex(index)
            self.path_label.setText(path)

    def set_path(self, path):
        self.tree.setRootIndex(self._model.index(path))
        self.path_label.setText(path)

    def get_current_path(self):
        return self._model.filePath(self.tree.rootIndex())

    def get_selected_paths(self):
        indexes = self.tree.selectionModel().selectedRows()
        return [self._model.filePath(idx) for idx in indexes]

    def get_selected_names(self):
        indexes = self.tree.selectionModel().selectedRows()
        return [self._model.fileName(idx) for idx in indexes]