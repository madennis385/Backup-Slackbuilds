# main.py
import os
import logging
from config import get_config
from file_monitor import CachedFileMonitor
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    try:
        monitor = CachedFileMonitor(
            monitor_dir = get_config[0], #MONITOR_DIR
            file_extensions = get_config[3], #FILE_EXTENSIONS
            dest_base_dir = get_config[1], #DEST_BASE_DIR
            dest_subdir_name=get_config[2], #DEST_SUBDIR_NAME
            check_interval=get_config[4], #CHECK_INTERVAL_SECONDS
            stable_threshold=get_config[5], #STABLE_CHECKS_THRESHOLD
        )
        monitor.run()
    except Exception as e:
        logging.error(f"Failed to initialize CachedFileMonitor: {e}")

if __name__ == "__main__":
    main()