class TaskType:
    ADD = "add"
    MAP = "map"
    UPDATE = "update"
    REMOVE = "remove"
    RMDIR = "rmdir"
    RENAME = "rename"
    CHMOD = "chmod"
    EXTRACT = "extract"
    BLANK = "blank"
    INFO = "info"


class TaskItem:
    def __init__(self, task_type, source="", target="", description="", extra=None):
        self.task_type = task_type
        self.source = source
        self.target = target
        self.description = description
        self.extra = extra or {}

    def __repr__(self):
        return f"TaskItem({self.task_type}, {self.source!r}, {self.target!r})"