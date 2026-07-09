import subprocess

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QLineEdit, QSpinBox, QCheckBox,
                                QMessageBox, QApplication)
from PySide6.QtCore import Qt, QThread, Signal

from xorriso_gui.i18n import tr


class MountDialog(QDialog):
    def __init__(self, drive_path="/dev/cdrom", parent=None):
        super().__init__(parent)
        self.drive_path = drive_path
        self.setWindowTitle("挂载光盘")
        self.resize(450, 250)
        self._init_ui()
        self._load_sessions()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(tr("mount.label").format(drive=self.drive_path)))

        fl = QHBoxLayout()
        fl.addWidget(QLabel(tr("mount.session") + ":"))
        self.session_spin = QSpinBox()
        self.session_spin.setMinimum(1)
        self.session_spin.setMaximum(99)
        self.session_spin.setValue(1)
        fl.addWidget(self.session_spin)
        fl.addStretch()
        layout.addLayout(fl)

        ml = QHBoxLayout()
        ml.addWidget(QLabel(tr("mount.mount_point") + ":"))
        self.mount_edit = QLineEdit("/mnt/xorriso")
        ml.addWidget(self.mount_edit)
        layout.addLayout(ml)

        self.ro_check = QCheckBox(tr("mount.readonly"))
        self.ro_check.setChecked(True)
        layout.addWidget(self.ro_check)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #61afef;")
        layout.addWidget(self.info_label)

        layout.addStretch()

        bl = QHBoxLayout()
        self.copy_btn = QPushButton(tr("mount.copy"))
        self.copy_btn.clicked.connect(self._on_copy)
        bl.addWidget(self.copy_btn)
        bl.addStretch()
        self.exec_btn = QPushButton(tr("mount.execute"))
        self.exec_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 6px 16px; }"
        )
        self.exec_btn.clicked.connect(self._on_execute)
        bl.addWidget(self.exec_btn)
        cancel_btn = QPushButton(tr("confirm.cancel"))
        cancel_btn.clicked.connect(self.reject)
        bl.addWidget(cancel_btn)
        layout.addLayout(bl)

    def _build_command(self):
        opts = ["ro"] if self.ro_check.isChecked() else ["rw"]
        session = self.session_spin.value()
        if session > 0:
            opts.append(f"sbsector={session}")
        mount_pt = self.mount_edit.text().strip()
        return f"mount -t iso9660 -o {','.join(opts)} '{self.drive_path}' '{mount_pt}'"

    def _on_copy(self):
        cmd = self._build_command()
        QApplication.clipboard().setText(cmd)
        self.info_label.setText(tr("mount.copied"))

    def _on_execute(self):
        cmd = self._build_command()
        mount_pt = self.mount_edit.text().strip()

        import os
        os.makedirs(mount_pt, exist_ok=True)

        full_cmd = f"mount -t iso9660 -o loop,ro '{self.drive_path}' '{mount_pt}'"
        if self.session_spin.value() > 1:
            opts = ["ro", f"session={self.session_spin.value()}"]
            full_cmd = f"mount -t iso9660 -o {','.join(opts)} '{self.drive_path}' '{mount_pt}'"

        reply = QMessageBox.question(
            self, tr("mount.confirm_title"),
            tr("mount.confirm_text").format(cmd=full_cmd),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            result = subprocess.run(["pkexec", "mount", "-t", "iso9660", "-o",
                                     "ro", self.drive_path, mount_pt],
                                    capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.info_label.setText(tr("mount.success").format(pt=mount_pt))
            else:
                self.info_label.setText(tr("mount.failed").format(err=result.stderr.strip() or result.stdout.strip()))
        except FileNotFoundError:
            self.info_label.setText(tr("mount.no_pkexec"))

    def _load_sessions(self):
        self._worker = _SessionWorker(self.drive_path, self)
        self._worker.result.connect(self._on_sessions_loaded)
        self._worker.start()

    def _on_sessions_loaded(self, count):
        if count > 1:
            self.session_spin.setMaximum(count)
            self.session_spin.setValue(count)
            self.info_label.setText(tr("mount.sessions_found").format(n=count))
        else:
            self.info_label.setText(tr("mount.single_session"))


class _SessionWorker(QThread):
    result = Signal(int)

    def __init__(self, drive, parent=None):
        super().__init__(parent)
        self.drive = drive
        self.finished.connect(self.deleteLater)

    def run(self):
        try:
            r = subprocess.run(
                ["xorriso", "-dev", self.drive, "-toc"],
                capture_output=True, text=True, timeout=30
            )
            count = 0
            for line in (r.stdout + r.stderr).split("\n"):
                if "ISO session" in line:
                    count += 1
            self.result.emit(count)
        except Exception:
            self.result.emit(1)