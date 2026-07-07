from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget,
                                QTableWidgetItem, QHeaderView, QPushButton,
                                QHBoxLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from xorriso_gui.models.task_item import TaskType


_TYPE_LABELS = {
    TaskType.ADD: "添加",
    TaskType.MAP: "映射",
    TaskType.UPDATE: "更新",
    TaskType.REMOVE: "删除",
    TaskType.MKDIR: "新建文件夹",
    TaskType.RENAME: "重命名",
    TaskType.CHMOD: "改权限",
    TaskType.EXTRACT: "提取",
    TaskType.BLANK: "格式化",
    TaskType.INFO: "信息",
}


class TaskQueueWidget(QWidget):
    task_removed = Signal(int)
    execute_requested = Signal()
    clear_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        hdr_layout = QHBoxLayout()
        title = QLabel("任务队列")
        title.setStyleSheet("padding: 4px; font-weight: bold;")
        hdr_layout.addWidget(title)
        hdr_layout.addStretch()

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._on_clear)
        self.clear_btn.setToolTip("清空所有待执行任务")
        hdr_layout.addWidget(self.clear_btn)

        self.remove_btn = QPushButton("移除选中")
        self.remove_btn.clicked.connect(self._on_remove_selected)
        self.remove_btn.setToolTip("移除选中的任务")
        hdr_layout.addWidget(self.remove_btn)

        layout.addLayout(hdr_layout)

        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["操作", "源", "目标"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setMaximumHeight(150)
        layout.addWidget(self.table)

        self.execute_btn = QPushButton("▶ 执行")
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

    def add_task(self, task):
        row = self.table.rowCount()
        self.table.insertRow(row)

        type_item = QTableWidgetItem(_TYPE_LABELS.get(task.task_type, task.task_type))
        type_item.setFlags(type_item.flags() | Qt.ItemIsUserCheckable)
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
        rows = set()
        for idx in self.table.selectedIndexes():
            rows.add(idx.row())
        for row in sorted(rows, reverse=True):
            self.remove_task(row)