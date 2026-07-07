from PySide6.QtCore import QSettings


def get_settings():
    return QSettings("xorriso-gui", "xorriso-gui")