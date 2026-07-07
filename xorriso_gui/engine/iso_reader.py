import re
import subprocess
from xorriso_gui.models.file_tree_model import FileNode

_LSL_LINE = re.compile(
    r"^([drwxstl-]{10})\s+"
    r"(\d+)\s+"
    r"(\S+)\s+"
    r"(\S+)\s+"
    r"(\d+)\s+"
    r"(\S{3}\s+\d{1,2}\s+(?:\d{4}|\d{1,2}:\d{2}))\s+"
    r"'(.+)'$"
)

_META_PREFIXES = ("xorriso", "Drive current", "Media current",
                  "Media status", "Media summary", "Volume id",
                  "Beginning to", "Full drive")


def _is_meta_line(line):
    return line.startswith(_META_PREFIXES)


def _parse_lsl_line(line):
    m = _LSL_LINE.match(line.strip())
    if not m:
        return None
    mode_str = m.group(1)
    size = int(m.group(5))
    date_str = m.group(6)
    full_path = m.group(7)
    is_dir = mode_str.startswith("d")
    is_symlink = mode_str.startswith("l")
    name = full_path.rstrip("/").rsplit("/", 1)[-1] or "/"
    return name, full_path, is_dir, is_symlink, size, mode_str, date_str


def _build_tree_from_flat(entries):
    root = FileNode(name="/", path="/", is_dir=True)
    path_to_node = {"/": root}

    for name, full_path, is_dir, is_symlink, size, mode, date in entries:
        if full_path == "/":
            root.mode = mode
            root.date = date
            continue

        node = FileNode(
            name=name, path=full_path, size=size,
            is_dir=is_dir, is_symlink=is_symlink,
            mode=mode, date=date
        )

        parent_path = full_path.rsplit("/", 1)[0]
        if not parent_path:
            parent_path = "/"
        parent = path_to_node.get(parent_path)
        if parent:
            parent.add_child(node)
            if is_dir and not is_symlink:
                path_to_node[full_path] = node

    root.sort_children()
    _add_placeholders(root)
    return root


def _add_placeholders(node):
    if node.is_dir:
        if node.child_count() == 0:
            placeholder = FileNode(
                name="——（空文件夹）——", path="", is_dir=False,
                is_placeholder=True
            )
            node.add_child(placeholder)
        # Don't recurse into placeholder
        for child in node.children:
            if not child.is_placeholder:
                _add_placeholders(child)


def _call_xorriso_find(drive_path):
    try:
        result = subprocess.run(
            ["xorriso", "-dev", drive_path, "-find", "/", "-exec", "lsdl"],
            capture_output=True, text=True, timeout=60
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return ""
    except Exception:
        return ""


def load_iso_contents(drive_path=None, command_args=None):
    if command_args:
        drive_path = _extract_drive_from_args(command_args)
    if not drive_path:
        return FileNode(name="/", path="/", is_dir=True), "未指定驱动器路径"

    output = _call_xorriso_find(drive_path)
    if not output:
        return FileNode(name="/", path="/", is_dir=True), "命令执行失败或超时"

    entries = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line or _is_meta_line(line):
            continue
        entry = _parse_lsl_line(line)
        if entry:
            entries.append(entry)

    if not entries:
        return FileNode(name="/", path="/", is_dir=True), "光盘为空或无法解析内容"

    root = _build_tree_from_flat(entries)
    return root, None


def _extract_drive_from_args(args):
    for i, a in enumerate(args):
        if a in ("-dev", "-indev") and i + 1 < len(args):
            return args[i + 1]
    return None


def load_empty_iso():
    root = FileNode(name="/", path="/", is_dir=True)
    _add_placeholders(root)
    return root


def parse_lsl_output(output, base_path="/"):
    entries = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line or _is_meta_line(line) or line.startswith("total"):
            continue
        entry = _parse_lsl_line(line)
        if entry:
            entries.append(entry)
    if not entries:
        return FileNode(name="/", path="/", is_dir=True)
    return _build_tree_from_flat(entries)