# main.py
import os
import logging
from config import MONITOR_DIR, DEST_BASE_DIR,DEST_SUBDIR_NAME, FILE_EXTENSIONS, CHECK_INTERVAL_SECONDS, STABLE_CHECKS_THRESHOLD
from file_monitor import SlackBuildMonitor
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    try:
        monitor = SlackBuildMonitor(
            monitor_dir=MONITOR_DIR,
            file_extensions=FILE_EXTENSIONS,
            dest_base_dir = DEST_BASE_DIR, 
            dest_subdir_name=DEST_SUBDIR_NAME,
            check_interval=CHECK_INTERVAL_SECONDS,
            stable_threshold=STABLE_CHECKS_THRESHOLD
        )
        monitor.run()
    except Exception as e:
        logging.error(f"Failed to initialize SlackBuildMonitor: {e}")

if __name__ == "__main__":
    main()