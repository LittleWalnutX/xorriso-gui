import re
from PySide6.QtCore import QProcess, QObject, Signal


class XorrisoProcess(QObject):
    started = Signal()
    finished = Signal(int)
    ready_read_stdout = Signal(str)
    ready_read_stderr = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = QProcess(self)
        self._process.setProgram("xorriso")
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.started.connect(self.started.emit)
        self._process.finished.connect(self._on_finished)
        self._command_line = ""

    def run(self, arguments):
        self._command_line = "xorriso " + " ".join(arguments)
        self._process.setArguments(arguments)
        self._process.start()

    def run_command_line(self, cmdline):
        self._command_line = cmdline
        self._process.setArguments(["-x"])
        self._process.start()
        self._process.write(cmdline.encode() + b"\n-end\n")
        self._process.closeWriteChannel()

    def command_line(self):
        return self._command_line

    def wait_finished(self, timeout=30000):
        return self._process.waitForFinished(timeout)

    def kill(self):
        self._process.kill()

    def is_running(self):
        return self._process.state() != QProcess.NotRunning

    def _on_stdout(self):
        data = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        self.ready_read_stdout.emit(data)

    def _on_stderr(self):
        data = self._process.readAllStandardError().data().decode("utf-8", errors="replace")
        self.ready_read_stderr.emit(data)

    def _on_finished(self, exit_code, exit_status):
        self.finished.emit(exit_code)