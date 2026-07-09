from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTreeView,
                                QHeaderView, QMenu, QInputDialog, QFileDialog,
                                QMessageBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from xorriso_gui.widgets.file_tree_view import FileTreeView
from xorriso_gui.models.file_tree_model import FileTreeModel
from xorriso_gui.i18n import tr


class IsoDropTreeView(FileTreeView):
    files_dropped = Signal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QTreeView.DropOnly)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        target_path = "/"
        idx = self.indexAt(event.position().toPoint())
        if idx.isValid():
            node = idx.internalPointer()
            if node and node.is_dir:
                target_path = node.path

        local_paths = []
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p:
                local_paths.append(p)

        if local_paths:
            self.files_dropped.emit(local_paths, target_path)
            event.acceptProposedAction()
        else:
            event.ignore()


class IsoPanel(QWidget):
    prepare_add = Signal(str, str)
    prepare_extract = Signal(str, str)
    prepare_remove = Signal(str)
    prepare_rename = Signal(str, str)
    prepare_mkdir = Signal(str)
    prepare_chmod = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = FileTreeModel(self)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.path_label = QLabel(tr("panel.iso_contents"))
        self.path_label.setStyleSheet("padding: 4px; font-weight: bold;")
        layout.addWidget(self.path_label)

        self.tree = IsoDropTreeView(self)
        self.tree.setModel(self._model)
        self.tree.setRootIsDecorated(True)
        self.tree.setSelectionMode(QTreeView.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        layout.addWidget(self.tree)

    def _connect_signals(self):
        self.tree.files_dropped.connect(self._on_files_dropped)

    def model(self):
        return self._model

    def load_contents(self, root_node):
        self._model.set_root_node(root_node)
        self.tree.expandToDepth(1)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)

    def clear(self):
        self._model.clear()

    def get_selected_paths(self):
        return self.tree.get_selected_paths(Qt.UserRole)

    def get_selected_names(self):
        return self.tree.get_selected_names()

    def get_target_directory_for_context(self):
        selected = self.get_selected_paths()
        if selected:
            idx = self.tree.selectionModel().selectedIndexes()
            if idx:
                node = idx[0].internalPointer()
                if node and node.is_dir:
                    return node.path
                if node and node.parent:
                    return node.parent.path
        return "/"

    def _on_files_dropped(self, local_paths, iso_target_path):
        for p in local_paths:
            name = p.rstrip("/").rsplit("/", 1)[-1]
            iso_path = iso_target_path.rstrip("/") + "/" + name
            self.prepare_add.emit(p, iso_path)

    def _on_context_menu(self, pos):
        menu = QMenu(self)
        selected = self.get_selected_paths()
        target_dir = self.get_target_directory_for_context()

        new_folder_act = QAction(tr("menu.new_folder"), self)
        new_folder_act.setToolTip(tr("tooltip.create_dir_in_iso"))
        new_folder_iso_path = target_dir.rstrip("/") + "/"
        new_folder_act.triggered.connect(
            lambda: self._on_mkdir(new_folder_iso_path))
        menu.addAction(new_folder_act)

        if selected:
            menu.addSeparator()

            remove_act = QAction(tr("menu.delete"), self)
            remove_act.triggered.connect(self._on_remove)
            menu.addAction(remove_act)

            rename_act = QAction(tr("menu.rename"), self)
            rename_act.triggered.connect(self._on_rename)
            menu.addAction(rename_act)

            menu.addSeparator()

            extract_act = QAction(tr("menu.extract"), self)
            extract_act.triggered.connect(self._on_extract)
            menu.addAction(extract_act)

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _on_mkdir(self, parent_path):
        name, ok = QInputDialog.getText(self, tr("dialog.new_folder"), tr("dialog.folder_name"))
        if ok and name:
            new_path = parent_path.rstrip("/") + "/" + name
            self.prepare_mkdir.emit(new_path)

    def _on_remove(self):
        for p in self.get_selected_paths():
            if p and p != "/":
                self.prepare_remove.emit(p)

    def _on_rename(self):
        paths = self.get_selected_paths()
        if not paths:
            return
        old = paths[0]
        name = old.rsplit("/", 1)[-1]
        new_name, ok = QInputDialog.getText(self, tr("dialog.rename"), tr("dialog.new_name"), text=name)
        if ok and new_name and new_name != name:
            parent = old.rsplit("/", 1)[0]
            if not parent:
                parent = ""
            new_path = parent + "/" + new_name
            self.prepare_rename.emit(old, new_path)

    def _on_extract(self):
        for p in self.get_selected_paths():
            if p == "/":
                continue
            dest = QFileDialog.getExistingDirectory(self, tr("dialog.extract_to").format(path=p))
            if dest:
                self.prepare_extract.emit(p, dest)