from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QLineEdit, QComboBox, QFileDialog,
                                QMessageBox, QGroupBox, QCheckBox)
from PySide6.QtCore import Qt, Signal

from xorriso_gui.engine.drive_manager import scan_drives
from xorriso_gui.engine.task_builder import TaskBuilder


class BurnIsoDialog(QDialog):
    execute_requested = Signal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("刻录 ISO 镜像到光盘")
        self.setMinimumWidth(480)
        self._init_ui()
        self._refresh_drives()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        iso_group = QGroupBox("ISO 镜像文件")
        iso_layout = QHBoxLayout()
        self.iso_edit = QLineEdit()
        self.iso_edit.setPlaceholderText("选择 .iso 文件...")
        iso_layout.addWidget(self.iso_edit)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_iso)
        iso_layout.addWidget(browse_btn)
        iso_group.setLayout(iso_layout)
        layout.addWidget(iso_group)

        drive_group = QGroupBox("目标光盘驱动器")
        drive_layout = QHBoxLayout()
        self.drive_combo = QComboBox()
        self.drive_combo.setEditable(True)
        self.drive_combo.setMinimumWidth(200)
        drive_layout.addWidget(self.drive_combo)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._refresh_drives)
        drive_layout.addWidget(refresh_btn)
        drive_group.setLayout(drive_layout)
        layout.addWidget(drive_group)

        opts_group = QGroupBox("选项")
        opts_layout = QHBoxLayout()
        self.eject_check = QCheckBox("完成后弹出")
        self.eject_check.setChecked(True)
        opts_layout.addWidget(self.eject_check)
        opts_layout.addStretch()
        opts_group.setLayout(opts_layout)
        layout.addWidget(opts_group)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        self.burn_btn = QPushButton("▶ 刻录")
        self.burn_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; "
            "font-weight: bold; padding: 6px 20px; }"
        )
        self.burn_btn.clicked.connect(self._on_burn)
        btn_layout.addWidget(self.burn_btn)
        layout.addLayout(btn_layout)

    def _refresh_drives(self):
        self.drive_combo.clear()
        drives = scan_drives()
        for d in drives:
            self.drive_combo.addItem(d.display_name(), d.path)

    def _browse_iso(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 ISO 镜像文件", "",
            "ISO 镜像 (*.iso *.ISO);;所有文件 (*)"
        )
        if path:
            self.iso_edit.setText(path)

    def _resolve_drive(self):
        text = self.drive_combo.lineEdit().text().strip() if self.drive_combo.lineEdit() else ""
        for i in range(self.drive_combo.count()):
            if self.drive_combo.itemText(i) == text:
                data = self.drive_combo.itemData(i)
                if data:
                    return data
                break
        return text

    def _on_burn(self):
        iso_path = self.iso_edit.text().strip()
        drive = self._resolve_drive()

        if not iso_path:
            QMessageBox.warning(self, "错误", "请选择 ISO 镜像文件。")
            return
        if not drive:
            QMessageBox.warning(self, "错误", "请选择目标驱动器。")
            return

        eject = "-eject" if self.eject_check.isChecked() else ""
        args = ["-as", "cdrecord", "-v", f"dev={drive}"]
        if eject:
            args.append(eject)
        args.append(iso_path)

        display = "xorriso " + " ".join(args)

        msg = QMessageBox(self)
        msg.setWindowTitle("确认刻录")
        msg.setIcon(QMessageBox.Question)
        msg.setText(f"即将刻录 ISO 到 {drive}：")
        msg.setInformativeText(display[:200] + ("..." if len(display) > 200 else ""))
        msg.setDetailedText(display)
        run_btn = msg.addButton("▶ 刻录", QMessageBox.AcceptRole)
        msg.addButton("取消", QMessageBox.RejectRole)

        if msg.exec():
            self.execute_requested.emit(args, display)
            self.accept()