# config.py
from dataclasses import dataclass
from pathlib import Path
from typing import List

@dataclass
class Config:
    monitor_dir: Path
    dest_base_dir: Path
    dest_subdir_name: str
    file_extensions: List[str]
    check_interval: int  # in seconds
    stable_threshold: int  # in seconds

from pathlib import Path

def get_config(auto=False):
    def get_input_or_accept_default(prompt, default, validator=None):
        if auto:
            return default

        while True:
            user_input = input(f"{prompt} [{default}]: ")
            user_input = user_input or default
            if validator and not validator(user_input):
                print("Invalid input. Please try again.")
            else:
                return user_input

    MONITOR_DIR = get_input_or_accept_default("Path to be monitored?", "/tmp", lambda x: Path(x).exists())
    DEST_BASE_DIR = get_input_or_accept_default("Base Backup Directory?", str(Path.home()), lambda x: Path(x).exists())
    DEST_SUBDIR_NAME = get_input_or_accept_default("Destination Directory?", "SavedCachedFiles")
    FILE_EXTENSIONS_INPUT = get_input_or_accept_default(
        "File extensions to watch for (comma-separated or single extension)?",
        ".tgz,.tbz,.tlz,.txz"
    )
    FILE_EXTENSIONS = [ext.strip() for ext in FILE_EXTENSIONS_INPUT.split(",") if ext.startswith(".")]

    if not FILE_EXTENSIONS:
        raise ValueError("No valid file extensions provided.")

    CHECK_INTERVAL_MINUTES = int(get_input_or_accept_default(
        "Monitor time (in minutes)?", "5", lambda x: x.isdigit() and int(x) > 0
    ))
    STABLE_CHECKS_THRESHOLD_MINUTES = int(get_input_or_accept_default(
        "Stable Time (in minutes)?", "2", lambda x: x.isdigit() and int(x) > 0
    ))

    return MONITOR_DIR, DEST_BASE_DIR, DEST_SUBDIR_NAME, FILE_EXTENSIONS, CHECK_INTERVAL_MINUTES * 60, STABLE_CHECKS_THRESHOLD_MINUTES

