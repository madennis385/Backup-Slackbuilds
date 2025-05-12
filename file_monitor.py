# file_monitor.py
import time
import shutil
import logging
from pathlib import Path

class SlackBuildMonitor:
    def __init__(self, monitor_dir, file_extensions, dest_base_dir, dest_subdir_name, check_interval, stable_threshold):
        self.monitor_dir = Path(monitor_dir)
        self.dest_base_dir = Path(dest_base_dir) # Ensure dest_base_dir is a Path object
        self.file_extensions = file_extensions
        self.dest_dir = self.ensure_dest_dir(dest_subdir_name)
        self.check_interval = check_interval
        self.stable_threshold = stable_threshold
        self.monitored_files = {}

    def ensure_dest_dir(self, subdir_name):
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
                if file_info['stable_checks'] >= self.stable_threshold:
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
            dest_path = self.dest_dir / filepath.name
            shutil.copy2(filepath, dest_path)
            logging.info(f"Copied {filepath} to {dest_path}")
        except (shutil.Error, OSError) as e:
            logging.error(f"Error copying {filepath}: {e}")
        finally:
            self.monitored_files.pop(filepath, None)

    def run(self):
        if not self.dest_dir:
            logging.error("Destination directory is not set. Exiting.")
            return
        extensions_display_string = ", ".join([f"{ext}" for ext in self.file_extensions]) 
        logging.info(f"Monitoring directory: {self.monitor_dir} for {extensions_display_string} files.")
        try:
            while True:
                logging.debug("Scanning directory...")
                current_files = self.scan_files()
                self.handle_existing_files(current_files)
                self.handle_new_files(current_files)
                logging.debug(f"Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user.")
        except Exception as e:
            logging.error(f"Unexpected error: {e}", exc_info=True)
        finally:
            logging.info("SlackBuildMonitor shutting down.")