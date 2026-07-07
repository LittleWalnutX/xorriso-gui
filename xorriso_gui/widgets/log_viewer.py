from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor


class LogViewer(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(5000)
        self.setFont(QFont("monospace", 10))
        self.setStyleSheet("QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; }")
        self._follow = True

    def append_text(self, text, color=None):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        if color:
            old_fmt = self.currentCharFormat()
            fmt = self.currentCharFormat()
            fmt.setForeground(color)
            cursor.insertText(text, fmt)
            fmt.setForeground(old_fmt.foreground())
        else:
            cursor.insertText(text)

        if self._follow:
            self.setTextCursor(cursor)
            self.ensureCursorVisible()

    def append_stdout(self, text):
        from PySide6.QtGui import QColor
        self.append_text(text, QColor("#d4d4d4"))

    def append_stderr(self, text):
        from PySide6.QtGui import QColor
        self.append_text(text, QColor("#e06c75"))

    def append_info(self, text):
        from PySide6.QtGui import QColor
        self.append_text(text + "\n", QColor("#61afef"))

    def append_success(self, text):
        from PySide6.QtGui import QColor
        self.append_text(text + "\n", QColor("#98c379"))

    def append_error(self, text):
        from PySide6.QtGui import QColor
        self.append_text(text + "\n", QColor("#e06c75"))

    def clear_log(self):
        self.clear()