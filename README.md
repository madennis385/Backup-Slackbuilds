# SlackBuild /tmp Monitor

This script monitors the `/tmp` directory (or another specified directory) for newly created files, specifically targeting SlackBuild archives or directories that often land there during the build process. Once a new file or directory content appears stable (i.e., its size hasn't changed for a defined period), the script copies it to a designated destination folder for archival or later inspection.

## Problem Solved

When building packages on Slackware, source tarballs and SlackBuild scripts are often downloaded or extracted to `/tmp`. Sometimes, these temporary files are cleaned up automatically, or you might forget to save a specific SlackBuild you used. This script helps automatically archive these files once they are fully downloaded or extracted.

## Real Life Problem Solved (or: what exactly, made me do this?)

I reinstall my OS pretty frequently, sometimes multiple times in a week. Some stuff, (nodejs, qt6) take FOREVER to compile. Oftentimes, because I boot from my handy-dandy slackware-current usb drive, and run `dd if=/dev/zero of=/dev/sda` before backing up those slackbuilds somewhere, I have to rebuild them. As written, this utility creates a new sub-directory in your home directory but, you *SHOULD* change that variable to an NFS share, or somewhere you're NOT going to format when you reinstall.

## Features

* Monitors a specified directory (default: `/tmp`).
* Detects newly created files within the monitored directory.
* Waits for file size stability before processing (configurable duration).
* Copies stable files to a designated destination directory using `shutil.copy2` (preserves metadata).
* Logs activities (file detection, stabilization, copying) to a log file (`file_monitor.log` by default).
* Uses a configurable polling interval to check for changes.

## How it Works

1.  The script periodically scans the `MONITOR_DIR`.
2.  It maintains a dictionary of files currently present, along with their size and the last time they were checked.
3.  When a new file is detected, it's added to the dictionary.
4.  If a known file's size has changed since the last check, its timestamp is updated.
5.  If a known file's size has *not* changed for a duration exceeding the `STABILITY_THRESHOLD`, the script considers it stable.
6.  Stable files are copied to the `DEST_DIR`.
7.  Files that have been successfully copied are marked as processed to avoid re-copying.
8.  The script logs these events to the specified `LOG_FILE`.

## Prerequisites

* Python 3.x
* Standard Python libraries (`os`, `time`, `shutil`, `logging`) - No external packages needed.
* A Linux/Unix-like environment where `/tmp` is commonly used (though the monitored directory is configurable).

## Installation

1.  Clone the repository:
    ```bash
    git clone [https://github.com/madennis385/Monitor-Slackbuilds.git](https://github.com/madennis385/Monitor-Slackbuilds.git)
    cd Monitor-Slackbuilds
    ```

## Configuration

**IMPORTANT:** Before running the script, you **MUST** configure the destination directory.

Edit the `oopRefactor/file_monitor.py` script and modify the configuration constants near the top of the file:

```python
# --- Configuration ---
MONITOR_DIR = "/tmp"  # Directory to monitor
DEST_DIR = "processed_tgz"  # <<< CHANGE THIS!!! Where to copy stable files
FILE_EXTENSIONS = list[".tgz", ".tbz", ".tlz", ".txz"]  # File extensions to monitor (probably doesn't need to change)
POLL_INTERVAL = 5  # Seconds between directory scans
STABILITY_THRESHOLD = 120  # Seconds a file size must remain unchanged to be considered stable (2 minutes)
LOG_FILE = "file_monitor.log"  # Path to the log file
# --- End Configuration ---
```

## Future Plans

While the current script fulfills its core purpose, there are several potential areas for enhancement and future development:

* **External Configuration:** Move configuration variables (`MONITOR_DIR`, `DEST_DIR`, `POLL_INTERVAL`, etc.) out of the script into a separate configuration file (e.g., `config.ini`, `config.yaml`) or allow them to be set via command-line arguments.
* **GUI Interface:** Develop a simple graphical user interface (GUI) 
* **Cleanup Utility:** Implement an optional feature (possibly as a separate utility or an argument) to clean up SlackBuild-specific files or directories from the `MONITOR_DIR` *after* they have been successfully copied and verified in the `DEST_DIR` and in installed slackbuilds.
* **Filesystem Event Monitoring:** Explore using more efficient filesystem event monitoring libraries (like `watchdog` on Linux/macOS/Windows or `inotify` directly on Linux) instead of polling.
* **System Service** Provide a wrapper script (using our favorite .rc files!)
* **Improved Logging:** Enhance logging with more detail, configurable log levels, and potentially log rotation.
* **Packaging:** Package the script for easier distribution and installation (e.g., using `setuptools` or `poetry` for installation via `pip`).
* **Duplicate Handling:** Add logic to check if an identical file (based on name or hash) already exists in the destination before copying, potentially skipping the copy or adding a version suffix.