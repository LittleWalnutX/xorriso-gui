import subprocess
import re


class DriveInfo:
    def __init__(self, address="", path="", vendor="", product="", is_mmc=False):
        self.address = address
        self.path = path
        self.vendor = vendor
        self.product = product
        self.is_mmc = is_mmc
        self.is_writable = False
        self.has_media = False
        self.media_status = ""
        self.sessions = []

    def display_name(self):
        name = f"{self.vendor} {self.product}".strip()
        if name:
            return f"{self.path} ({name})"
        return self.path


class SessionInfo:
    def __init__(self, num=0, lba=0, size=0):
        self.num = num
        self.lba = lba
        self.size = size


def parse_device_links(output):
    drives = []
    lines = output.strip().split("\n")
    for line in lines:
        match = re.match(r"(\d+)\s+-dev\s+['\"](.+?)['\"]\s+r[w-]r[w-]", line)
        if match:
            idx = int(match.group(1))
            path = match.group(2)
            vendor_match = re.search(r"'([^']+)'\s+'([^']+)'", line)
            vendor = vendor_match.group(1) if vendor_match else ""
            product = vendor_match.group(2) if vendor_match else ""
            drives.append(DriveInfo(
                address=f"-dev '{path}'",
                path=path,
                vendor=vendor,
                product=product,
                is_mmc=True
            ))
    return drives


def parse_toc(output):
    sessions = []
    for line in output.strip().split("\n"):
        match = re.match(r"(\d+)\s+(\d+)s\s+(\d+)", line.strip())
        if match:
            sessions.append(SessionInfo(
                num=int(match.group(1)),
                lba=int(match.group(2)),
                size=int(match.group(3))
            ))
    return sessions


def scan_drives():
    try:
        result = subprocess.run(
            ["xorriso", "-device_links"],
            capture_output=True, text=True, timeout=5
        )
        drives = parse_device_links(result.stdout + result.stderr)
        return drives
    except Exception as e:
        return []


def get_toc(drive_path):
    try:
        result = subprocess.run(
            ["xorriso", "-dev", drive_path, "-toc"],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        status = "unknown"
        if "Media current:" in output:
            status_line = [l for l in output.split("\n") if "Media current:" in l]
            if status_line:
                status = status_line[0].split("Media current:")[-1].strip()
                if "is blank" in status:
                    status = "blank"
                elif "is appendable" in status:
                    status = "appendable"
                elif "is closed" in status:
                    status = "closed"
        sessions = parse_toc(output)
        return status, sessions, output
    except Exception as e:
        return "error", [], str(e)