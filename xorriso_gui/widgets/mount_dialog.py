import subprocess
import os

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QLineEdit, QSpinBox, QCheckBox,
                                QMessageBox, QApplication, QComboBox)
from PySide6.QtCore import Qt, QThread, Signal

from xorriso_gui.i18n import tr


class MountDialog(QDialog):
    def __init__(self, drive_path="/dev/cdrom", parent=None):
        super().__init__(parent)
        self.drive_path = drive_path
        self._sessions = {}
        self.setWindowTitle(tr("mount.title"))
        self.resize(480, 280)
        self._init_ui()
        self._load_sessions()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        dl = QHBoxLayout()
        dl.addWidget(QLabel(tr("mount.drive") + ":"))
        self.drive_combo = QComboBox()
        self.drive_combo.setEditable(True)
        self.drive_combo.setMinimumWidth(250)
        if self.drive_path:
            self.drive_combo.setEditText(self.drive_path)
        dl.addWidget(self.drive_combo)
        layout.addLayout(dl)

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
        self.mount_edit = QLineEdit(os.path.expanduser("~/mnt/xorriso"))
        ml.addWidget(self.mount_edit)
        layout.addLayout(ml)

        self.ro_check = QCheckBox(tr("mount.readonly"))
        self.ro_check.setChecked(True)
        layout.addWidget(self.ro_check)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #61afef;")
        self.info_label.setWordWrap(True)
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

    def _resolve_drive(self):
        line_edit = self.drive_combo.lineEdit()
        text = line_edit.text().strip() if line_edit else ""
        for i in range(self.drive_combo.count()):
            if self.drive_combo.itemText(i) == text:
                data = self.drive_combo.itemData(i)
                if data:
                    return data
                break
        return text

    def _build_command(self):
        drive = self._resolve_drive() or self.drive_path
        session = self.session_spin.value()
        ro = "ro" if self.ro_check.isChecked() else "rw"
        mount_pt = self.mount_edit.text().strip()
        if session > 1:
            return f"xorriso -dev '{drive}' -osirrox on -mount '{drive}' auto {session} '{mount_pt}'"
        else:
            return f"mount -t iso9660 -o {ro} '{drive}' '{mount_pt}'"

    def _on_copy(self):
        cmd = self._build_command()
        QApplication.clipboard().setText(cmd)
        self.info_label.setText(tr("mount.copied"))

    def _on_execute(self):
        drive = self._resolve_drive() or self.drive_path
        cmd = self._build_command()
        mount_pt = self.mount_edit.text().strip()
        session = self.session_spin.value()

        try:
            os.makedirs(mount_pt, exist_ok=True)
        except (PermissionError, OSError):
            pass

        reply = QMessageBox.question(
            self, tr("mount.confirm_title"),
            tr("mount.confirm_text").format(cmd=cmd),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        if session > 1:
            mount_args = ["xorriso", "-dev", drive, "-osirrox", "on",
                          "-mount", drive, "auto", str(session), mount_pt]
        else:
            ro = "ro" if self.ro_check.isChecked() else "rw"
            mount_args = ["mount", "-t", "iso9660", "-o", ro, drive, mount_pt]

        for elevator in ["pkexec", "kdesu", "gksudo", "gksu"]:
            try:
                self.info_label.setText(tr("mount.trying").format(tool=elevator))
                QApplication.processEvents()
                result = subprocess.run([elevator] + mount_args,
                                        capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    self.info_label.setText(tr("mount.success").format(pt=mount_pt))
                    return
                elif "not authorized" in (result.stderr + result.stdout).lower() \
                        or "incorrect password" in (result.stderr + result.stdout).lower():
                    self.info_label.setText(tr("mount.auth_failed"))
                    return
            except FileNotFoundError:
                continue

        self.info_label.setText(tr("mount.no_elevator"))

    def _load_sessions(self):
        drive = self._resolve_drive() or self.drive_path
        if not drive:
            return
        self._worker = _SessionWorker(drive, self)
        self._worker.result.connect(self._on_sessions_loaded)
        self._worker.start()

    def _on_sessions_loaded(self, sessions):
        self._sessions = {num: lba for num, lba in sessions}
        count = len(sessions)
        if count > 1:
            self.session_spin.setMaximum(count)
            self.session_spin.setValue(count)
            self.info_label.setText(tr("mount.sessions_found").format(n=count))
        else:
            self.info_label.setText(tr("mount.single_session"))

    def _build_command(self):
        drive = self._resolve_drive() or self.drive_path
        session = self.session_spin.value()
        ro = "ro" if self.ro_check.isChecked() else "rw"
        mount_pt = self.mount_edit.text().strip()
        lba = self._sessions.get(session)
        if lba and session > 1:
            return f"mount -t iso9660 -o {ro},sbsector={lba} '{drive}' '{mount_pt}'"
        else:
            return f"mount -t iso9660 -o {ro} '{drive}' '{mount_pt}'"

    def _on_copy(self):
        cmd = self._build_command()
        QApplication.clipboard().setText(cmd)
        self.info_label.setText(tr("mount.copied"))

    def _on_execute(self):
        drive = self._resolve_drive() or self.drive_path
        cmd = self._build_command()
        mount_pt = self.mount_edit.text().strip()
        session = self.session_spin.value()

        try:
            os.makedirs(mount_pt, exist_ok=True)
        except (PermissionError, OSError):
            pass

        reply = QMessageBox.question(
            self, tr("mount.confirm_title"),
            tr("mount.confirm_text").format(cmd=cmd),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        ro = "ro" if self.ro_check.isChecked() else "rw"
        lba = self._sessions.get(session)
        if lba and session > 1:
            opts = f"{ro},sbsector={lba}"
        else:
            opts = ro
        mount_args = ["mount", "-t", "iso9660", "-o", opts, drive, mount_pt]

        found_elevator = False
        for elevator in ["pkexec", "kdesu", "gksudo", "gksu"]:
            try:
                found_elevator = True
                self.info_label.setText(tr("mount.trying").format(tool=elevator))
                QApplication.processEvents()
                result = subprocess.run([elevator] + mount_args,
                                        capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    self.info_label.setText(tr("mount.success").format(pt=mount_pt))
                    return
                else:
                    err = (result.stderr + result.stdout).strip()
                    if err:
                        self.info_label.setText(tr("mount.failed").format(err=err[:200]))
                    else:
                        self.info_label.setText(tr("mount.failed").format(err=f"exit code {result.returncode}"))
                    return
            except FileNotFoundError:
                continue

        if found_elevator:
            self.info_label.setText(tr("mount.failed").format(err="all elevators failed"))
        else:
            self.info_label.setText(tr("mount.no_elevator"))


class _SessionWorker(QThread):
    result = Signal(list)

    def __init__(self, drive, parent=None):
        super().__init__(parent)
        self.drive = drive
        self.finished.connect(self.deleteLater)

    def run(self):
        sessions = []
        try:
            r = subprocess.run(
                ["xorriso", "-dev", self.drive, "-toc"],
                capture_output=True, text=True, timeout=30
            )
            for line in (r.stdout + r.stderr).split("\n"):
                if "ISO session" in line:
                    parts = [p.strip() for p in line.split(",")]
                    try:
                        prefix, num = parts[0].rsplit(None, 1)
                        lba = int(parts[1].rstrip("s"))
                        sessions.append((int(num), lba))
                    except (ValueError, IndexError):
                        continue
        except Exception:
            pass
        self.result.emit(sessions)