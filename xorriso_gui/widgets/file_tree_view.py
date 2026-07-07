from PySide6.QtWidgets import QTreeView, QMenu, QHeaderView
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCursor


class FileTreeView(QTreeView):
    items_dragged = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QTreeView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeView.DragDrop)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setSortingEnabled(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self._context_menu_actions = []

        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

    def add_context_action(self, text, callback, icon=None):
        act = QAction(text, self)
        if icon:
            act.setIcon(icon)
        act.triggered.connect(callback)
        self._context_menu_actions.append(act)

    def get_selected_paths(self, user_role=Qt.UserRole):
        paths = []
        for idx in self.selectionModel().selectedIndexes():
            if idx.column() == 0:
                path = idx.data(user_role)
                if path:
                    paths.append(path)
        return paths

    def get_selected_names(self):
        names = []
        for idx in self.selectionModel().selectedIndexes():
            if idx.column() == 0:
                names.append(idx.data(Qt.DisplayRole))
        return names

    def set_context_menu_actions(self, actions):
        self._context_menu_actions = actions

    def show_context_menu(self, extra_actions=None):
        menu = QMenu(self)
        for act in self._context_menu_actions:
            menu.addAction(act)
        if extra_actions:
            menu.addSeparator()
            for act in extra_actions:
                menu.addAction(act)
        menu.exec(QCursor.pos())