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
        self.resize(500, 320)
        self._toc_loaded = False
        self._init_ui()
        self._update_session_state()

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
        self.session_check = QCheckBox(tr("mount.specify_session"))
        self.session_check.toggled.connect(self._on_session_toggled)
        fl.addWidget(self.session_check)
        fl.addWidget(QLabel(tr("mount.session") + ":"))
        self.session_spin = QSpinBox()
        self.session_spin.setMinimum(1)
        self.session_spin.setMaximum(99)
        self.session_spin.setValue(1)
        self.session_spin.setEnabled(False)
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
        self.unmount_btn = QPushButton(tr("mount.unmount"))
        self.unmount_btn.setToolTip(tr("mount.unmount_tip"))
        self.unmount_btn.clicked.connect(self._on_unmount)
        bl.addWidget(self.unmount_btn)
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

    def _update_session_state(self):
        enabled = self.session_check.isChecked()
        self.session_spin.setEnabled(enabled)
        if enabled and not self._toc_loaded:
            self._load_sessions()
            self._toc_loaded = True

    def _on_session_toggled(self):
        self._update_session_state()

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
        ro = "ro" if self.ro_check.isChecked() else "rw"
        mount_pt = self.mount_edit.text().strip()
        if self.session_check.isChecked():
            session = self.session_spin.value()
            lba = self._sessions.get(session)
            if lba and session > 1:
                return f"mount -t iso9660 -o {ro},sbsector={lba} '{drive}' '{mount_pt}'"
        return f"mount -t iso9660 -o {ro} '{drive}' '{mount_pt}'"

    def _on_copy(self):
        cmd = self._build_command()
        QApplication.clipboard().setText(cmd)
        self.info_label.setText(tr("mount.copied"))

    def _check_mount_point(self, mount_pt):
        try:
            os.makedirs(mount_pt, exist_ok=True)
        except PermissionError:
            return False, tr("mount.err_perm").format(pt=mount_pt)
        if os.path.ismount(mount_pt):
            return False, tr("mount.err_already_mounted").format(pt=mount_pt)
        try:
            items = os.listdir(mount_pt)
            if items:
                return False, tr("mount.err_not_empty").format(pt=mount_pt, n=len(items))
        except PermissionError:
            pass
        return True, ""

    def _on_execute(self):
        drive = self._resolve_drive() or self.drive_path
        cmd = self._build_command()
        mount_pt = self.mount_edit.text().strip()
        session = self.session_spin.value()

        ok, err = self._check_mount_point(mount_pt)
        if not ok:
            self.info_label.setText(err)
            return

        reply = QMessageBox.question(
            self, tr("mount.confirm_title"),
            tr("mount.confirm_text").format(cmd=cmd),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        ro = "ro" if self.ro_check.isChecked() else "rw"
        opts = ro
        if self.session_check.isChecked():
            session = self.session_spin.value()
            lba = self._sessions.get(session)
            if lba and session > 1:
                opts = f"{ro},sbsector={lba}"
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

    def _on_unmount(self):
        mount_pt = self.mount_edit.text().strip()
        if not mount_pt:
            return
        if not os.path.ismount(mount_pt):
            self.info_label.setText(tr("mount.not_mounted").format(pt=mount_pt))
            return

        reply = QMessageBox.question(
            self, tr("mount.unmount_confirm_title"),
            tr("mount.unmount_confirm_text").format(pt=mount_pt),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        for elevator in ["pkexec", "kdesu", "gksudo", "gksu"]:
            try:
                self.info_label.setText(tr("mount.unmounting").format(pt=mount_pt, tool=elevator))
                QApplication.processEvents()
                result = subprocess.run([elevator, "umount", mount_pt],
                                        capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    self.info_label.setText(tr("mount.unmount_ok").format(pt=mount_pt))
                    return
                else:
                    err = (result.stderr + result.stdout).strip()
                    self.info_label.setText(tr("mount.unmount_failed").format(err=err[:200] if err else "unknown"))
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
        if count > 0:
            self.session_spin.setMaximum(count)
            self.session_spin.setValue(count)
        if count > 1:
            self.info_label.setText(tr("mount.sessions_found").format(n=count))
        elif count == 1:
            self.info_label.setText(tr("mount.single_session"))
        else:
            self.info_label.setText(tr("mount.no_sessions"))


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