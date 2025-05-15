# TODO:
I need to re-write this document, the installation instructions are not current, at all.

# Directory Monitor & Cached Backup Script

This Python script monitors a specified directory for files with particular extensions. When these files become "stable" (i.e., their size hasn't changed for a configurable period), the script backs them up to a designated destination directory. It intelligently avoids duplicating backups of unchanged files by checking MD5 hashes against a local SQLite database of previously backed-up files.

## Features

* **Directory Monitoring:** Actively watches a user-defined directory.
* **File Extension Filtering:** Focuses only on files with specified extensions (e.g., `.zip`, `.tgz`, `.log`).
* **Stability Check:** Waits for a file's size to remain constant for a set duration before considering it for backup, preventing copies of in-progress files.
* **MD5 Hashing:** Computes MD5 hashes of stable files to detect content changes.
* **Cached Backups:** Uses a SQLite database (`backup_state.sqlite`) to keep track of backed-up files and their hashes. This prevents redundant backups of files whose content hasn't changed, even if they are re-processed.
* **Configurable:**
    * Interactive prompts for easy setup on first run.
    * Command-line option (`--no-input` or `--auto`) to use default settings, suitable for automation or running as a service.
* **Logging:** Provides informative console output about its operations, including scanned files, stable files, copied files, and errors.

## Requirements

* Python 3.x
* Standard Python libraries (no external packages need to be installed via pip):
    * `os`
    * `sys`
    * `logging`
    * `sqlite3`
    * `shutil`
    * `pathlib`
    * `hashlib`
    * `time`
    * `dataclasses`
    * Optional: if you want to run this interactively you'll need questionary `pip install questionary`
## Configuration
1.  **Interactive Mode:**
    Simply run `python3 main.py`. The script will prompt you for:
    * **Path to be monitored?**: The directory you want to watch for files.
    * **Base Backup Directory?**: The main directory where your backups will be stored.
    * **Destination Directory?**: The name of the subdirectory (inside the Base Backup Directory) where files from this specific monitored path will be saved.
    * **File extensions to watch for?**: Comma-separated list of extensions (e.g., `.tgz,.zip,.log`).
    * **Monitor time (in minutes)?**: How often to scan the monitored directory.
    * **Stable Time (in minutes)?**: How long a file's size must remain unchanged before it's considered stable and ready for backup.

### Backup State Database

The script creates and uses a file named `backup_state.sqlite` in the same directory where the backups are stored. This SQLite database stores the relative paths and MD5 hashes of files that have already been backed up, preventing redundant copies.

## Usage

There are three sample files in this directory `rc.cached_file_monitor.sample`, `config.ini.sample` and, `file_type_presets.conf.sample` : Adjust these three files to match your local desired setup and save them without the `.sample` extension.
rc.cached_file_monitor will need to be placed in /etc/rc.d to run automatically when your system starts. Additionally, you'll want to add these lines to your /etc/rc.local:
        ```
        if [ -x /etc/rc.d/rc.cached_file_monitor ]; then
            /etc/rc.d/rc.cached_file_monitor start
        fi
        ```
You can also add
        ```
        if [ -x /etc/rc.d/rc.cached_file_monitor ]; then
            /etc/rc.d/rc.cached_file_monitor stop
        fi
        ```

To your rc.local_shutdown to make sure the database gets saved before a shutdown/restart event.

## How It Works

1.  **Initialization**: The script loads its configuration, either from user prompts or default settings.
2.  **Scanning**: Periodically (defined by `check_interval`), the `CachedFileMonitor` scans the `monitor_dir` for files matching the specified `file_extensions`.
3.  **Tracking Stability**:
    * Newly detected files are added to a tracking list with their current size.
    * On subsequent scans, if a tracked file's size has changed, its stability counter is reset.
    * If a file's size remains unchanged across enough checks to meet the `stable_threshold` duration, it's deemed "stable."
4.  **Backup Process for Stable Files**:
    * The MD5 hash of the stable file is computed.
    * The `backup_db.py` module checks if a file with the same relative path (to the monitored directory) and MD5 hash already exists in the `backup_state.sqlite` database.
    * If it's already backed up and unchanged, the script logs this and skips copying.
    * If it's new or has changed (different MD5), the file is copied to the `dest_dir` (which is `dest_base_dir` / `dest_subdir_name`).
    * Information about the newly backed-up file (path, MD5 hash, timestamp) is recorded in the database.
5.  **Database Persistence**: The `backup_state.sqlite` database is saved to disk from its in-memory version when the script shuts down gracefully (e.g., via `Ctrl+C`) or periodically during operation if such functionality were added to `save_to_disk` calls within the main loop (currently it's on shutdown).

## Logging

The script provides logging output to /var/log/cached_file_monitor.log, indicating its current operations, such as:
* Initialization parameters.
* Files being detected and monitored.
* Changes in file sizes.
* Files becoming stable.
* Files being copied or skipped (if already backed up).
* Any errors encountered.

Log messages are formatted as: `YYYY-MM-DD HH:MM:SS - LEVELNAME - Message`.

## Future Considerations / To-Do

* More advanced error handling and recovery.
* ~~Configuration via a separate config file (e.g., INI, YAML, JSON) instead of only prompts/defaults.~~
* Option for one-time run (scan and backup once, then exit) vs. continuous monitoring.
