import shlex

from xorriso_gui.models.task_item import TaskType


class TaskBuilder:
    def __init__(self):
        self.input_drive = None
        self.output_drive = None
        self.is_growing = False
        self.is_modifying = False
        self.volume_id = None
        self.blank_media = False
        self.osirrox_enabled = False

    def set_input_drive(self, path):
        self.input_drive = path

    def set_output_drive(self, path):
        self.output_drive = path

    def set_same_drive(self, path):
        self.input_drive = path
        self.output_drive = path
        self.is_growing = True

    def set_volume_id(self, vid):
        self.volume_id = vid

    def set_blank(self, blank):
        self.blank_media = blank

    def build_args(self, tasks):
        args = []

        if self.is_growing and self.input_drive:
            args.extend(["-dev", self.input_drive])
        else:
            if self.input_drive:
                args.extend(["-indev", self.input_drive])
            if self.output_drive:
                args.extend(["-outdev", self.output_drive])

        if self.blank_media:
            args.extend(["-blank", "as_needed"])

        if self.volume_id:
            args.extend(["-volid", self.volume_id])

        has_extract = self._has_extract(tasks)
        if has_extract:
            args.extend(["-osirrox", "on"])

        group_add = []
        group_map = []
        group_update = []
        group_rm = []
        group_mv = []
        group_extract = []
        group_chmod = []

        for task in tasks:
            if task.task_type == TaskType.ADD:
                group_add.append(task.source)
            elif task.task_type == TaskType.MAP:
                group_map.append((task.source, task.target))
            elif task.task_type == TaskType.UPDATE:
                group_update.append((task.source, task.target))
            elif task.task_type == TaskType.REMOVE:
                group_rm.append(task.target)
            elif task.task_type == TaskType.RENAME:
                group_mv.append((task.source, task.target))
            elif task.task_type == TaskType.EXTRACT:
                group_extract.append((task.source, task.target))
            elif task.task_type == TaskType.CHMOD:
                group_chmod.append((task.extra.get("mode", ""), task.target))

        if group_rm:
            args.append("-rm_r")
            args.extend(group_rm)
            args.append("--")

        if group_mv:
            args.append("-mv")
            for src, dst in group_mv:
                args.extend([src, dst])
            args.append("--")

        if group_chmod:
            for mode, path in group_chmod:
                args.extend(["-chmod", mode, path, "--"])

        for src, dst in group_map:
            args.extend(["-map", src, dst])

        for src, dst in group_update:
            args.extend(["-update_r", src, dst])

        if group_add:
            args.extend(["-cd", "/"])
            args.append("-add")
            args.extend(group_add)
            args.append("--")

        if group_extract:
            for src, dst in group_extract:
                args.extend(["-extract", src, dst])

        has_changes = bool(group_add or group_map or group_update or group_rm
                           or group_mv or group_chmod or group_extract)

        if not has_changes:
            args.extend(["-changes_pending", "yes"])

        args.append("-commit")

        return args

    @staticmethod
    def args_to_display(args):
        return " ".join(shlex.quote(a) for a in args)

    def build_commands(self, tasks):
        return self.args_to_display(self.build_args(tasks))

    def build_blank_only(self, drive_path):
        args = ["-outdev", drive_path, "-blank", "as_needed", "-commit"]
        return self.args_to_display(args)

    def build_burn_iso(self, iso_path, drive_path):
        args = ["-as", "cdrecord", "-v", f"dev={drive_path}", iso_path]
        return self.args_to_display(args)

    def build_toc(self, drive_path):
        args = ["-dev", drive_path, "-toc"]
        return self.args_to_display(args)

    def is_empty_tasks(self, tasks):
        return len(tasks) == 0

    @staticmethod
    def _has_extract(tasks):
        for t in tasks:
            if t.task_type == TaskType.EXTRACT:
                return True
        return False