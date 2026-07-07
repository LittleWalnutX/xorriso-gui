from PySide6.QtCore import QThread, Signal

from xorriso_gui.engine.drive_manager import scan_drives, get_media_space
from xorriso_gui.engine.iso_reader import load_iso_contents


class ScanDrivesWorker(QThread):
    result = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.finished.connect(self.deleteLater)

    def run(self):
        drives = scan_drives()
        self.result.emit(drives)


class LoadIsoWorker(QThread):
    result = Signal(object, str)

    def __init__(self, drive_path, parent=None):
        super().__init__(parent)
        self.drive_path = drive_path
        self.finished.connect(self.deleteLater)

    def run(self):
        root, error = load_iso_contents(drive_path=self.drive_path)
        self.result.emit(root, error)


class MediaSpaceWorker(QThread):
    result = Signal(str, str)

    def __init__(self, drive_path, parent=None):
        super().__init__(parent)
        self.drive_path = drive_path
        self.finished.connect(self.deleteLater)

    def run(self):
        summary = get_media_space(self.drive_path)
        self.result.emit(self.drive_path, summary or "")