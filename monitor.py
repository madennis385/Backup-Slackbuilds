import os
import time
import shutil
import logging
from pathlib import Path

# --- Configuration ---
MONITOR_DIR = "/tmp"
DEST_SUBDIR_NAME = "processed_tgz" # Subdirectory within MONITOR_DIR
FILE_EXTENSION = ".tgz"
CHECK_INTERVAL_SECONDS = 300  # 5 minutes (5 * 60)
STABLE_CHECKS_THRESHOLD = 2   # Needs to be stable for this many checks
# --- End Configuration ---

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# --- End Setup Logging ---

def ensure_dest_dir(base_dir, subdir_name):
    """Ensures the destination directory exists."""
    dest_path = Path(base_dir) / subdir_name
    try:
        dest_path.mkdir(parents=True, exist_ok=True)
        logging.info(f"Ensured destination directory exists: {dest_path}")
        return dest_path
    except OSError as e:
        logging.error(f"Could not create destination directory {dest_path}: {e}")
        return None

def get_file_size(filepath):
    """Gets the size of a file, returns None if file not found."""
    try:
        return os.path.getsize(filepath)
    except FileNotFoundError:
        return None
    except OSError as e:
        logging.error(f"Error getting size for {filepath}: {e}")
        return None # Treat OS errors like file not found for stability check

def main():
    """Main monitoring loop."""
    monitored_files = {} # Dictionary to track files: {filepath: {'last_size': size, 'stable_checks': count}}
    dest_dir = ensure_dest_dir(MONITOR_DIR, DEST_SUBDIR_NAME)

    if not dest_dir:
        logging.error("Exiting due to inability to create destination directory.")
        return # Exit if we can't create the destination

    logging.info(f"Starting monitoring of {MONITOR_DIR} for new {FILE_EXTENSION} files.")
    logging.info(f"Check interval: {CHECK_INTERVAL_SECONDS} seconds.")
    logging.info(f"Stability threshold: {STABLE_CHECKS_THRESHOLD} checks ({STABLE_CHECKS_THRESHOLD * CHECK_INTERVAL_SECONDS} seconds).")
    logging.info(f"Stable files will be copied to: {dest_dir}")

    try:
        while True:
            current_files_in_dir = set()
            logging.debug(f"Scanning {MONITOR_DIR}...")

            # --- Scan for candidate files ---
            try:
                for filename in os.listdir(MONITOR_DIR):
                    if filename.endswith(FILE_EXTENSION):
                        filepath = os.path.join(MONITOR_DIR, filename)
                        # Ensure it's a file and not a directory/symlink etc.
                        if os.path.isfile(filepath):
                            current_files_in_dir.add(filepath)
            except OSError as e:
                 logging.error(f"Error listing directory {MONITOR_DIR}: {e}")
                 # Decide if you want to continue or exit on dir access error
                 # For robustness, let's wait and try again
                 time.sleep(CHECK_INTERVAL_SECONDS)
                 continue # Skip the rest of the loop iteration


            # --- Check monitored files ---
            # Iterate over a copy of keys to allow removing items during iteration
            for filepath in list(monitored_files.keys()):
                if filepath not in current_files_in_dir:
                    # File was removed/renamed from outside
                    logging.warning(f"Tracked file disappeared: {filepath}. Removing from tracking.")
                    del monitored_files[filepath]
                    continue

                current_size = get_file_size(filepath)
                if current_size is None:
                    # File might have been deleted between listing and getting size, or error occurred
                    logging.warning(f"Could not get size for {filepath}. Removing from tracking.")
                    del monitored_files[filepath]
                    continue

                last_size = monitored_files[filepath]['last_size']
                stable_checks = monitored_files[filepath]['stable_checks']

                if current_size == last_size:
                    monitored_files[filepath]['stable_checks'] += 1
                    logging.debug(f"File {filepath} size ({current_size} bytes) unchanged. Stable checks: {monitored_files[filepath]['stable_checks']}/{STABLE_CHECKS_THRESHOLD}")

                    if monitored_files[filepath]['stable_checks'] >= STABLE_CHECKS_THRESHOLD:
                        logging.info(f"File {filepath} has been stable for {STABLE_CHECKS_THRESHOLD} checks. Copying to {dest_dir}...")
                        try:
                            dest_filepath = os.path.join(dest_dir, os.path.basename(filepath))
                            shutil.copy2(filepath, dest_filepath) # copy2 preserves metadata
                            logging.info(f"Successfully copied {filepath} to {dest_filepath}")
                            # Remove from monitoring after successful copy
                            del monitored_files[filepath]
                        except shutil.Error as e:
                            logging.error(f"Error copying file {filepath} to {dest_dir}: {e}")
                            # Decide if you want to keep monitoring or remove on copy error
                            # For now, let's remove it to avoid repeated copy attempts
                            del monitored_files[filepath]
                        except OSError as e:
                            logging.error(f"OS Error during copy of {filepath}: {e}")
                            del monitored_files[filepath] # Remove on OS error too

                else:
                    # Size changed, reset stable counter
                    logging.info(f"File {filepath} size changed from {last_size} to {current_size} bytes. Resetting stable checks.")
                    monitored_files[filepath]['last_size'] = current_size
                    monitored_files[filepath]['stable_checks'] = 0

            # --- Add new files to monitoring ---
            for filepath in current_files_in_dir:
                if filepath not in monitored_files:
                    current_size = get_file_size(filepath)
                    if current_size is not None:
                         logging.info(f"Detected new file: {filepath} (Size: {current_size} bytes). Starting monitoring.")
                         monitored_files[filepath] = {'last_size': current_size, 'stable_checks': 0}
                    else:
                         logging.warning(f"Detected new file {filepath}, but could not get initial size. Will retry next cycle.")
                         # Don't add to monitored_files yet if size couldn't be read

            # --- Wait for the next check interval ---
            logging.debug(f"Sleeping for {CHECK_INTERVAL_SECONDS} seconds...")
            time.sleep(CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logging.info("Monitoring stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        logging.info("Script shutting down.")

if __name__ == "__main__":
    main()