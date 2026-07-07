from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QIcon, QColor


class FileNode:
    def __init__(self, name="", path="", size=0, is_dir=False, is_symlink=False,
                 mode="", date=""):
        self.name = name
        self.path = path
        self.size = size
        self.is_dir = is_dir
        self.is_symlink = is_symlink
        self.mode = mode
        self.date = date
        self.children = []
        self.parent = None
        self._loaded = False

    def child_count(self):
        return len(self.children)

    def child_at(self, index):
        if 0 <= index < len(self.children):
            return self.children[index]
        return None

    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        return 0

    def add_child(self, child):
        child.parent = self
        self.children.append(child)

    def find_child(self, name):
        for c in self.children:
            if c.name == name:
                return c
        return None

    def sort_children(self):
        self.children.sort(key=lambda n: (not n.is_dir, n.name.lower()))


class FileTreeModel(QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._root = FileNode(name="", path="", is_dir=True)
        self._icons = {}
        self._init_icons()

    def _init_icons(self):
        style = QIcon.fromTheme
        self._icons["dir"] = style("folder") if not QIcon.fromTheme("folder").isNull() else QIcon()
        self._icons["file"] = style("text-x-generic") if not QIcon.fromTheme("text-x-generic").isNull() else QIcon()
        self._icons["symlink"] = style("emblem-symbolic-link") if not QIcon.fromTheme("emblem-symbolic-link").isNull() else QIcon()

    def root_node(self):
        return self._root

    def clear(self):
        self.beginResetModel()
        self._root = FileNode(name="", path="", is_dir=True)
        self.endResetModel()

    def set_root_node(self, node):
        self.beginResetModel()
        self._root = node
        self.endResetModel()

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            parent_node = self._root
        else:
            parent_node = parent.internalPointer()
        child = parent_node.child_at(row)
        if child:
            return self.createIndex(row, column, child)
        return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        node = index.internalPointer()
        if node is None or node.parent is None or node.parent == self._root:
            return QModelIndex()
        return self.createIndex(node.parent.row(), 0, node.parent)

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            return self._root.child_count()
        node = parent.internalPointer()
        return node.child_count() if node else 0

    def columnCount(self, parent=QModelIndex()):
        return 4

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if node is None:
            return None
        col = index.column()
        if role == Qt.DisplayRole:
            if col == 0:
                return node.name
            elif col == 1:
                if node.is_dir and not node.is_symlink:
                    return ""
                return format_size(node.size)
            elif col == 2:
                return node.mode
            elif col == 3:
                return node.date
        elif role == Qt.DecorationRole and col == 0:
            if node.is_symlink:
                return self._icons["symlink"]
            elif node.is_dir:
                return self._icons["dir"]
            else:
                return self._icons["file"]
        elif role == Qt.UserRole:
            return node.path
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return ["名称", "大小", "权限", "日期"][section]
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled


def format_size(size):
    if size is None or size < 0:
        return ""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size) < 1024.0:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"