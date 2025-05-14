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

## File Structure

The script is organized into the following files:

* **`main.py`**: The entry point of the application. It handles command-line arguments, initializes the configuration, and starts the file monitor.
* **`config.py`**: Manages loading the configuration settings. It can prompt the user for input or use predefined defaults. Defines the `Config` dataclass structure.
* **`file_monitor.py`**: Contains the `CachedFileMonitor` class, which is the core of the script. It handles file scanning, stability checks, MD5 computation, and the backup process.
* **`backup_db.py`**: Manages the SQLite database (`backup_state.sqlite`). This includes creating the schema, recording backed-up files, and checking if a file has already been backed up.

## Configuration

The script can be configured in two ways:

1.  **Interactive Mode:**
    Simply run `python main.py`. The script will prompt you for:
    * **Path to be monitored?**: The directory you want to watch for files.
    * **Base Backup Directory?**: The main directory where your backups will be stored.
    * **Destination Directory?**: The name of the subdirectory (inside the Base Backup Directory) where files from this specific monitored path will be saved.
    * **File extensions to watch for?**: Comma-separated list of extensions (e.g., `.tgz,.zip,.log`).
    * **Monitor time (in minutes)?**: How often to scan the monitored directory.
    * **Stable Time (in minutes)?**: How long a file's size must remain unchanged before it's considered stable and ready for backup.

2.  **Non-Interactive Mode (using defaults):**
    Run the script with the `--no-input` or `--auto` flag:
    `python main.py --no-input`
    or
    `python main.py --auto`

    This will use the default values defined in `config.py`:
    * **Monitor Directory**: `/tmp`
    * **Base Backup Directory**: Your user's home directory (e.g., `/home/user`)
    * **Destination Subdirectory Name**: `SavedCachedFiles`
    * **File Extensions**: `.tgz,.tbz,.tlz,.txz`
    * **Monitor Interval**: 5 minutes
    * **Stable Time**: 2 minutes

### Backup State Database

The script creates and uses a file named `backup_state.sqlite` in the same directory where the script is run. This SQLite database stores the relative paths and MD5 hashes of files that have already been backed up, preventing redundant copies.

## Usage

1.  Ensure you have Python 3 installed.
2.  Place the script files (`main.py`, `config.py`, `file_monitor.py`, `backup_db.py`) in the same directory.
3.  Open your terminal or command prompt and navigate to that directory.
4.  **To run with interactive configuration:**
    ```bash
    python main.py
    ```
5.  **To run with default/automated configuration:**
    ```bash
    python main.py --no-input
    ```
    or
    ```bash
    python main.py --auto
    ```
6.  The script will start monitoring and logging its actions to the console.
7.  To stop the script, press `Ctrl+C`. The script will attempt to save the current backup state to disk before exiting.

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

6. **Optional** : There is an rc.cached_file_monitor file in this repo. If you want this to run in the background:
    * Put `main.py` `backup_db.py` `config.py` and `file_monitor.py` in `/opt/cached_file_monitor/` 
    * Move the rc.cached_file_monitor to `/etc/rc.d` and make the file exectuable. 
    * Add these lines to `/etc/rc.local` :
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
## Logging

The script provides logging output to the console, indicating its current operations, such as:
* Initialization parameters.
* Files being detected and monitored.
* Changes in file sizes.
* Files becoming stable.
* Files being copied or skipped (if already backed up).
* Any errors encountered.

Log messages are formatted as: `YYYY-MM-DD HH:MM:SS - LEVELNAME - Message`.

## Future Considerations / To-Do

* More advanced error handling and recovery.
* Configuration via a separate config file (e.g., INI, YAML, JSON) instead of only prompts/defaults.
* Option for one-time run (scan and backup once, then exit) vs. continuous monitoring.