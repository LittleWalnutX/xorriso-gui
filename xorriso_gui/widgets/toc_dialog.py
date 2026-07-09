from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QComboBox, QTableWidget, QTableWidgetItem,
                                QHeaderView, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal

from xorriso_gui.engine.drive_manager import scan_drives
from xorriso_gui.i18n import tr


class TocDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("toc.title"))
        self.resize(550, 400)
        self._init_ui()
        self._refresh_drives()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        drive_layout = QHBoxLayout()
        drive_layout.addWidget(QLabel(tr("toc.drive_label")))
        self.drive_combo = QComboBox()
        self.drive_combo.setEditable(True)
        self.drive_combo.setMinimumWidth(250)
        drive_layout.addWidget(self.drive_combo)
        refresh_btn = QPushButton(tr("btn.refresh"))
        refresh_btn.clicked.connect(self._refresh_drives)
        drive_layout.addWidget(refresh_btn)
        show_btn = QPushButton(tr("toc.show_btn"))
        show_btn.clicked.connect(self._show_toc)
        drive_layout.addWidget(show_btn)
        layout.addLayout(drive_layout)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            tr("toc.session_col"), tr("toc.lba_col"),
            tr("toc.blocks_col"), tr("toc.size_col"),
            tr("toc.volid_col")
        ])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton(tr("confirm.cancel"))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _refresh_drives(self):
        self.drive_combo.clear()
        drives = scan_drives()
        for d in drives:
            self.drive_combo.addItem(d.display_name(), d.path)

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

    def _show_toc(self):
        drive = self._resolve_drive()
        if not drive:
            QMessageBox.warning(self, "Error", tr("error.select_drive"))
            return
        self.status_label.setText(tr("status.loading").format(path=drive))
        self._worker = _TocWorker(drive, self)
        self._worker.finished.connect(lambda out, sp: self._on_toc_loaded(out, sp, drive))
        self._worker.start()

    def _on_toc_loaded(self, output, space_summary, drive):
        self.table.setRowCount(0)
        self.status_label.setText(space_summary or "")

        sessions = []
        for line in output.split("\n"):
            if "ISO session" not in line:
                continue
            parts = [p.strip() for p in line.split(",")]
            try:
                prefix, num = parts[0].rsplit(None, 1)
                lba = int(parts[1].rstrip("s"))
                blocks = int(parts[2].rstrip("s"))
                sessions.append((int(num), lba, blocks, parts[3] if len(parts) > 3 else ""))
            except (ValueError, IndexError):
                continue

        for num, lba, blocks, volid in sessions:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(num)))
            self.table.setItem(row, 1, QTableWidgetItem(str(lba)))
            self.table.setItem(row, 2, QTableWidgetItem(str(blocks)))
            size_gb = blocks * 2048 / (1024**3)
            self.table.setItem(row, 3, QTableWidgetItem(f"{size_gb:.1f}G"))
            self.table.setItem(row, 4, QTableWidgetItem(volid))


class _TocWorker(QThread):
    finished = Signal(str, str)

    def __init__(self, drive, parent=None):
        super().__init__(parent)
        self.drive = drive
        self.finished.connect(self.deleteLater)

    def run(self):
        import subprocess
        try:
            r = subprocess.run(
                ["xorriso", "-dev", self.drive, "-toc"],
                capture_output=True, text=True, timeout=30
            )
            toc_out = r.stdout + r.stderr
        except Exception:
            toc_out = ""
        try:
            r2 = subprocess.run(
                ["xorriso", "-dev", self.drive, "-tell_media_space"],
                capture_output=True, text=True, timeout=30
            )
            space_out = r2.stdout + r2.stderr
            for line in space_out.split("\n"):
                if "Media summary:" in line:
                    space_summary = line.strip()
                    break
            else:
                space_summary = ""
        except Exception:
            space_summary = ""
        self.finished.emit(toc_out, space_summary)