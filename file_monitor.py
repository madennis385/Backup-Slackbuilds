# file_monitor.py
import time
import shutil
import logging
from pathlib import Path
from config import Config # Assuming Config dataclass is defined here
import hashlib
from backup_db import BackupDB
import threading # Required for type hinting the event

class CachedFileMonitor:
    # Modify __init__ to accept the shutdown_event
    def __init__(self, config: Config, shutdown_event: threading.Event):
        self.config = config
        self.shutdown_event = shutdown_event # Store the event

        self.monitor_dir = Path(self.config.monitor_dir)
        self.dest_base_dir = Path(self.config.dest_base_dir)
        self.file_extensions = self.config.file_extensions
        self.check_interval = self.config.check_interval  # This is the total check interval in seconds
        self.stable_threshold = self.config.stable_threshold

        self.dest_dir = self.ensure_dest_dir(self.config.dest_subdir_name)
        self.monitored_files = {}
        self.db = BackupDB()

    def compute_md5(self, filepath: Path, chunk_size: int = 8192) -> str:
        # ... (same as before)
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
        # ... (same as before)
        dest_path = self.dest_base_dir / subdir_name
        try:
            dest_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Ensured destination directory exists: {dest_path}")
            return dest_path
        except OSError as e:
            logging.error(f"Could not create destination directory {dest_path}: {e}")
            raise

    def get_file_size(self, filepath):
        # ... (same as before)
        try:
            return filepath.stat().st_size
        except FileNotFoundError:
            return None
        except OSError as e:
            logging.error(f"Error getting size for {filepath}: {e}")
            return None

    def scan_files(self):
        # ... (same as before)
        try:
            return {
                f for f in self.monitor_dir.iterdir()
                if f.is_file() and f.suffix in self.file_extensions
            }
        except OSError as e:
            logging.error(f"Error listing directory {self.monitor_dir}: {e}")
            return set()

    def handle_existing_files(self, current_files):
        # ... (same as before)
        for filepath in list(self.monitored_files):
            if self.shutdown_event.is_set(): break # Check event during long loops
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
                if file_info['stable_checks'] * self.check_interval >= self.stable_threshold: # Assuming check_interval here is the "granularity of checks" not the sleep time
                                                                                              # If self.check_interval is the main loop sleep, this logic might need adjustment
                                                                                              # Or, rather, stable_checks * (time_per_check which is 1s here)
                    self.copy_stable_file(filepath)
            else:
                logging.info(f"{filepath} size changed from {file_info['last_size']} to {current_size}. Resetting checks.")
                self.monitored_files[filepath] = {'last_size': current_size, 'stable_checks': 0}


    def handle_new_files(self, current_files):
        # ... (same as before)
        for filepath in current_files:
            if self.shutdown_event.is_set(): break # Check event
            if filepath not in self.monitored_files:
                current_size = self.get_file_size(filepath)
                if current_size is not None:
                    logging.info(f"Detected new file: {filepath} (Size: {current_size}). Starting monitoring.")
                    self.monitored_files[filepath] = {'last_size': current_size, 'stable_checks': 0}
                else:
                    logging.warning(f"Detected new file {filepath}, but could not get size. Skipping for now.")

    def copy_stable_file(self, filepath):
        # ... (same as before, but you might want to add a self.shutdown_event.is_set() check if MD5 or copy is very long)
        try:
            file_md5 = self.compute_md5(filepath)
            if self.shutdown_event.is_set(): return # Check after potentially long operation

            rel_path = str(filepath.relative_to(self.monitor_dir))
            dest_path = self.dest_dir / filepath.name 

            if self.db.is_already_backed_up(rel_path, file_md5):
                logging.info(f"Skipped {filepath}; already backed up with same content.")
                return

            shutil.copy2(filepath, dest_path)
            if self.shutdown_event.is_set(): return # Check after potentially long operation

            self.db.record_backup(rel_path, file_md5)
            logging.info(f"Copied {filepath} to {dest_path}")

        except Exception as e:
            logging.error(f"Error copying {filepath}: {e}")
        finally:
            self.monitored_files.pop(filepath, None)


    def run(self):
        if not self.dest_dir: 
            logging.error("Destination directory is not set. Exiting.")
            return
        
        extensions_display_string = ", ".join(self.file_extensions)
        logging.info(f"Monitoring directory: {self.monitor_dir} for {extensions_display_string} files. Press Ctrl+C or send SIGTERM to stop.")
        
        try:
            # Main loop, checks the shutdown_event
            while not self.shutdown_event.is_set():
                logging.debug("Scanning directory...")
                current_files = self.scan_files()
                if self.shutdown_event.is_set(): break

                self.handle_existing_files(current_files)
                if self.shutdown_event.is_set(): break

                self.handle_new_files(current_files)
                if self.shutdown_event.is_set(): break
                
                logging.debug(f"Scan cycle complete. Waiting for {self.check_interval} seconds or shutdown signal.")
                # Sleep in small intervals to check the event frequently
                # The total sleep time will be self.check_interval
                for _ in range(self.check_interval):
                    if self.shutdown_event.is_set():
                        break
                    time.sleep(1) # Sleep 1 second at a time
                
                if self.shutdown_event.is_set():
                    logging.info("Shutdown signal detected during sleep interval. Exiting loop.")
                    break
        
        except Exception as e: # Catch any unexpected errors in the loop
            logging.error(f"Unexpected error in monitor run loop: {e}", exc_info=True)
            self.shutdown_event.set() # Ensure shutdown is triggered
        finally:
            # This block will execute when the loop terminates (due to event or exception)
            logging.info("CachedFileMonitor run loop ending. Attempting to save database.")
            self.db.save_to_disk()
            logging.info("CachedFileMonitor shutdown complete.")