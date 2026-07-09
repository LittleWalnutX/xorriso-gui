import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTreeView,
                                QHeaderView, QPushButton, QFileDialog,
                                QHBoxLayout, QToolButton, QMenu, QInputDialog,
                                QMessageBox)
from PySide6.QtCore import Qt, Signal, QDir
from PySide6.QtWidgets import QFileSystemModel
from PySide6.QtGui import QAction

from xorriso_gui.models.task_item import TaskItem, TaskType
from xorriso_gui.i18n import tr


class DiskPanel(QWidget):
    path_changed = Signal(str)
    add_to_iso = Signal(str, str)
    open_terminal = Signal(str)
    load_iso_file = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        hdr = QHBoxLayout()
        self.path_label = QLabel(tr("panel.disk_filesystem"))
        self.path_label.setStyleSheet("padding: 4px; font-weight: bold;")
        hdr.addWidget(self.path_label)
        hdr.addStretch()

        up_btn = QToolButton()
        up_btn.setText("\u2b06")
        up_btn.setToolTip(tr("menu.go_up"))
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
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)

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

    def _on_context_menu(self, pos):
        menu = QMenu(self)
        selected = self.get_selected_paths()
        current_dir = self.get_current_path()

        add_act = QAction(tr("menu.add_to_iso"), self)
        add_act.setToolTip(tr("menu.add_to_iso_tip"))
        add_act.triggered.connect(self._on_add_selected_to_iso)
        menu.addAction(add_act)

        iso_files = [p for p in selected if p.lower().endswith(".iso")]
        if iso_files:
            open_iso_act = QAction(tr("menu.open_as_iso"), self)
            open_iso_act.setToolTip(f"加载 {os.path.basename(iso_files[0])} 到输入框")
            open_iso_act.triggered.connect(lambda: self._on_open_as_iso(iso_files[0]))
            menu.addAction(open_iso_act)

        menu.addSeparator()

        new_folder_act = QAction(tr("menu.new_folder"), self)
        new_folder_act.triggered.connect(lambda: self._on_new_folder(current_dir))
        menu.addAction(new_folder_act)

        menu.addSeparator()

        refresh_act = QAction(tr("menu.refresh"), self)
        refresh_act.triggered.connect(self._on_refresh)
        menu.addAction(refresh_act)

        open_there_act = QAction(tr("menu.open_terminal"), self)
        open_there_act.triggered.connect(lambda: self._on_open_terminal(current_dir))
        menu.addAction(open_there_act)

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _on_add_selected_to_iso(self):
        for path in self.get_selected_paths():
            name = os.path.basename(path)
            self.add_to_iso.emit(path, "/" + name)

    def _on_open_as_iso(self, path):
        self.load_iso_file.emit(path)

    def _on_new_folder(self, parent_dir):
        name, ok = QInputDialog.getText(self, tr("dialog.new_folder"), tr("dialog.folder_name"))
        if ok and name:
            new_path = os.path.join(parent_dir, name)
            try:
                os.makedirs(new_path, exist_ok=True)
                self._on_refresh()
            except OSError as e:
                QMessageBox.warning(self, "错误", f"无法创建文件夹:\n{e}")

    def _on_refresh(self):
        current = self.get_current_path()
        old_index = self.tree.rootIndex()
        self._model.setRootPath("")
        self._model.setRootPath(current)
        self.tree.setRootIndex(self._model.index(current))

    def _on_open_terminal(self, path):
        self.open_terminal.emit(path)