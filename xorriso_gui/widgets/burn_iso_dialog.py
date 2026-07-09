from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QLineEdit, QComboBox, QFileDialog,
                                QMessageBox, QGroupBox, QCheckBox)
from PySide6.QtCore import Qt, Signal

from xorriso_gui.engine.drive_manager import scan_drives
from xorriso_gui.engine.task_builder import TaskBuilder
from xorriso_gui.i18n import tr


class BurnIsoDialog(QDialog):
    execute_requested = Signal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("burn.title"))
        self.setMinimumWidth(480)
        self._init_ui()
        self._refresh_drives()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        iso_group = QGroupBox(tr("burn.iso_group"))
        iso_layout = QHBoxLayout()
        self.iso_edit = QLineEdit()
        self.iso_edit.setPlaceholderText(tr("burn.select_iso"))
        iso_layout.addWidget(self.iso_edit)
        browse_btn = QPushButton(tr("btn.browse"))
        browse_btn.clicked.connect(self._browse_iso)
        iso_layout.addWidget(browse_btn)
        iso_group.setLayout(iso_layout)
        layout.addWidget(iso_group)

        drive_group = QGroupBox(tr("burn.drive_group"))
        drive_layout = QHBoxLayout()
        self.drive_combo = QComboBox()
        self.drive_combo.setEditable(True)
        self.drive_combo.setMinimumWidth(200)
        drive_layout.addWidget(self.drive_combo)
        refresh_btn = QPushButton(tr("btn.refresh"))
        refresh_btn.clicked.connect(self._refresh_drives)
        drive_layout.addWidget(refresh_btn)
        drive_group.setLayout(drive_layout)
        layout.addWidget(drive_group)

        opts_group = QGroupBox(tr("burn.options_group"))
        opts_layout = QHBoxLayout()
        self.eject_check = QCheckBox(tr("burn.eject_after"))
        self.eject_check.setChecked(True)
        opts_layout.addWidget(self.eject_check)
        opts_layout.addStretch()
        opts_group.setLayout(opts_layout)
        layout.addWidget(opts_group)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton(tr("confirm.cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        self.burn_btn = QPushButton(tr("burn.burn_btn"))
        self.burn_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 6px 20px; }"
        )
        self.burn_btn.setStyleSheet(
            
            
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
            self, tr("dialog.select_iso"), "",
            tr("iso_filter")
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
            QMessageBox.warning(self, "Error", tr("error.select_iso"))
            return
        if not drive:
            QMessageBox.warning(self, "Error", tr("error.select_target"))
            return

        eject = "-eject" if self.eject_check.isChecked() else ""
        args = ["-as", "cdrecord", "-v", f"dev={drive}"]
        if eject:
            args.append(eject)
        args.append(iso_path)

        display = "xorriso " + " ".join(args)

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("burn.confirm_title"))
        msg.setIcon(QMessageBox.Question)
        msg.setText(tr("burn.confirm_text").format(drive=drive))
        msg.setInformativeText(display[:200] + ("..." if len(display) > 200 else ""))
        msg.setDetailedText(display)
        run_btn = msg.addButton("▶ 刻录", QMessageBox.AcceptRole)
        msg.addButton("取消", QMessageBox.RejectRole)

        if msg.exec():
            self.execute_requested.emit(args, display)
            self.accept()