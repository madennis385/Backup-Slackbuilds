# config.py
from pathlib import Path
MONITOR_DIR = "/tmp"
DEST_BASE_DIR = Path.home()
DEST_SUBDIR_NAME = "SavedSlackbuilds"
FILE_EXTENSIONS = [".tgz", ".tbz", ".tlz", ".txz"]
CHECK_INTERVAL_SECONDS = 300
STABLE_CHECKS_THRESHOLD = 2