# file_monitor.py
import time
import shutil
import logging
from pathlib import Path
from config import Config # Config is already imported but good to note
import hashlib
from backup_db import BackupDB

class CachedFileMonitor:
    # Change __init__ to accept a single Config object
    def __init__(self, config: Config):
        self.config = config  # Store the passed Config object

        # Initialize attributes from the config object
        # Ensure Path objects for directory attributes
        self.monitor_dir = Path(self.config.monitor_dir)
        self.dest_base_dir = Path(self.config.dest_base_dir) # Corrected typo from self.dest_base_dire
        # self.dest_subdir_name = self.config.dest_subdir_name # This can be accessed via self.config.dest_subdir_name
        self.file_extensions = self.config.file_extensions
        self.check_interval = self.config.check_interval
        self.stable_threshold = self.config.stable_threshold

        # ensure_dest_dir will use attributes from self.config or the initialized self.dest_base_dir
        self.dest_dir = self.ensure_dest_dir(self.config.dest_subdir_name)
        self.monitored_files = {}
        self.db = BackupDB()

    def compute_md5(self, filepath: Path, chunk_size: int = 8192) -> str:
        """Compute MD5 hash of the given file."""
        hash_md5 = hashlib.md5()
        try:
            with filepath.open("rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logging.error(f"Failed to compute MD5 for {filepath}: {e}")
            return ""

    def ensure_dest_dir(self, subdir_name):
        # Use self.dest_base_dir which is initialized as a Path object from the config
        dest_path = self.dest_base_dir / subdir_name
        try:
            dest_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Ensured destination directory exists: {dest_path}")
            return dest_path
        except OSError as e:
            logging.error(f"Could not create destination directory {dest_path}: {e}")
            raise

    def get_file_size(self, filepath):
        try:
            return filepath.stat().st_size
        except FileNotFoundError:
            return None
        except OSError as e:
            logging.error(f"Error getting size for {filepath}: {e}")
            return None

    def scan_files(self):
        try:
            # self.monitor_dir is already a Path object
            return {
                f for f in self.monitor_dir.iterdir()
                if f.is_file() and f.suffix in self.file_extensions
            }
        except OSError as e:
            logging.error(f"Error listing directory {self.monitor_dir}: {e}")
            return set()

    def handle_existing_files(self, current_files):
        for filepath in list(self.monitored_files):
            if filepath not in current_files:
                logging.warning(f"Tracked file disappeared: {filepath}. Removing from tracking.")
                self.monitored_files.pop(filepath, None)
                continue

            current_size = self.get_file_size(filepath)
            if current_size is None:
                logging.warning(f"Could not get size for {filepath}. Removing from tracking.")
                self.monitored_files.pop(filepath, None)
                continue

            file_info = self.monitored_files[filepath]
            if current_size == file_info['last_size']:
                file_info['stable_checks'] += 1
                logging.debug(f"{filepath} size stable at {current_size}. Checks: {file_info['stable_checks']}")
                # Use self.stable_threshold and self.check_interval directly
                if file_info['stable_checks'] * self.check_interval >= self.stable_threshold:
                    self.copy_stable_file(filepath)
            else:
                logging.info(f"{filepath} size changed from {file_info['last_size']} to {current_size}. Resetting checks.")
                self.monitored_files[filepath] = {'last_size': current_size, 'stable_checks': 0}

    def handle_new_files(self, current_files):
        for filepath in current_files:
            if filepath not in self.monitored_files:
                current_size = self.get_file_size(filepath)
                if current_size is not None:
                    logging.info(f"Detected new file: {filepath} (Size: {current_size}). Starting monitoring.")
                    self.monitored_files[filepath] = {'last_size': current_size, 'stable_checks': 0}
                else:
                    logging.warning(f"Detected new file {filepath}, but could not get size. Skipping for now.")

    def copy_stable_file(self, filepath):
        try:
            file_md5 = self.compute_md5(filepath)
            # self.monitor_dir is a Path object
            rel_path = str(filepath.relative_to(self.monitor_dir))
            dest_path = self.dest_dir / filepath.name # self.dest_dir is already Path

            if self.db.is_already_backed_up(rel_path, file_md5):
                logging.info(f"Skipped {filepath}; already backed up with same content.")
                return

            shutil.copy2(filepath, dest_path)
            self.db.record_backup(rel_path, file_md5)
            logging.info(f"Copied {filepath} to {dest_path}")

        except Exception as e:
            logging.error(f"Error copying {filepath}: {e}")
        finally:
            self.monitored_files.pop(filepath, None)

    def run(self):
        if not self.dest_dir: # self.dest_dir is initialized in __init__
            logging.error("Destination directory is not set. Exiting.")
            return
        extensions_display_string = ", ".join(self.file_extensions)
        # self.monitor_dir is a Path object
        logging.info(f"Monitoring directory: {self.monitor_dir} for {extensions_display_string} files.")
        try:
            while True:
                logging.debug("Scanning directory...")
                current_files = self.scan_files()
                self.handle_existing_files(current_files)
                self.handle_new_files(current_files)
                # self.check_interval is an int
                logging.debug(f"Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user.")
        except Exception as e:
            logging.error(f"Unexpected error: {e}", exc_info=True)
        finally:
                logging.info("CachedFileMonitor shutting down.")
                self.db.save_to_disk()