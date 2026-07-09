from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget,
                                QTableWidgetItem, QHeaderView, QPushButton,
                                QHBoxLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from xorriso_gui.models.task_item import TaskType


_TYPE_LABEL_KEYS = {
    TaskType.ADD: "task.type_add",
    TaskType.MAP: "task.type_map",
    TaskType.UPDATE: "task.type_update",
    TaskType.REMOVE: "task.type_remove",
    TaskType.MKDIR: "task.type_mkdir",
    TaskType.RENAME: "task.type_rename",
    TaskType.CHMOD: "task.type_chmod",
    TaskType.EXTRACT: "task.type_extract",
    TaskType.BLANK: "task.type_blank",
    TaskType.INFO: "task.type_info",
}


class TaskQueueWidget(QWidget):
    task_removed = Signal(object)
    execute_requested = Signal()
    clear_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        hdr_layout = QHBoxLayout()
        self.title_label = QLabel("Task Queue")
        self.title_label.setStyleSheet("padding: 4px; font-weight: bold;")
        hdr_layout.addWidget(self.title_label)
        hdr_layout.addStretch()

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self._on_clear)
        self.clear_btn.setToolTip("Clear all pending tasks")
        hdr_layout.addWidget(self.clear_btn)

        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self._on_remove_selected)
        self.remove_btn.setToolTip("Remove selected task")
        hdr_layout.addWidget(self.remove_btn)

        layout.addLayout(hdr_layout)

        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["Action", "Source", "Target"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setMaximumHeight(150)
        layout.addWidget(self.table)

        self.execute_btn = QPushButton("▶ Execute")
        self.execute_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; "
            "font-weight: bold; padding: 6px 20px; border-radius: 4px; "
            "font-size: 14px; }"
            "QPushButton:hover { background-color: #2ecc71; }"
            "QPushButton:pressed { background-color: #1e8449; }"
        )
        self.execute_btn.clicked.connect(self._on_execute)
        self.execute_btn.setEnabled(False)
        layout.addWidget(self.execute_btn)

    def _type_label(self, task_type):
        from xorriso_gui.i18n import tr
        key = _TYPE_LABEL_KEYS.get(task_type, task_type)
        return tr(key, task_type)

    def _update_type_labels(self):
        from xorriso_gui.i18n import tr
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                task = item.data(Qt.UserRole)
                if task:
                    item.setText(self._type_label(task.task_type))

    def add_task(self, task):
        row = self.table.rowCount()
        self.table.insertRow(row)

        type_item = QTableWidgetItem(self._type_label(task.task_type))
        type_item.setFlags(type_item.flags() | Qt.ItemIsUserCheckable)
        type_item.setData(Qt.UserRole, task)
        self.table.setItem(row, 0, type_item)

        self.table.setItem(row, 1, QTableWidgetItem(task.source))
        self.table.setItem(row, 2, QTableWidgetItem(task.target))

        self.table.scrollToBottom()
        self.execute_btn.setEnabled(True)

    def remove_task(self, row):
        if 0 <= row < self.table.rowCount():
            self.table.removeRow(row)
        if self.table.rowCount() == 0:
            self.execute_btn.setEnabled(False)

    def clear_all(self):
        self.table.setRowCount(0)
        self.execute_btn.setEnabled(False)

    def get_tasks(self, task_data):
        task_data.clear()
        for row in range(self.table.rowCount()):
            task_data.append(self.table.item(row, 0).data(Qt.UserRole))

    def task_count(self):
        return self.table.rowCount()

    def _on_execute(self):
        self.execute_requested.emit()

    def _on_clear(self):
        self.clear_requested.emit()

    def _on_remove_selected(self):
        rows_to_remove = []
        for idx in self.table.selectedIndexes():
            if idx.row() not in rows_to_remove:
                rows_to_remove.append(idx.row())
                task = self.table.item(idx.row(), 0).data(Qt.UserRole)
                if task:
                    self.task_removed.emit(task)
        for row in sorted(rows_to_remove, reverse=True):
            self.remove_task(row)