# main.py
import os
import sys
import logging
from pathlib import Path # Add Path import if not already implicitly available for Config instantiation
from config import get_config, Config # Import Config dataclass
from file_monitor import CachedFileMonitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    try:
        use_defaults = "--no-input" in sys.argv or "--auto" in sys.argv
        # config_tuple will hold the raw values from get_config
        config_tuple = get_config(auto=use_defaults)

        # Create a Config object
        app_config = Config(
            monitor_dir=Path(config_tuple[0]),
            dest_base_dir=Path(config_tuple[1]),
            dest_subdir_name=config_tuple[2],
            file_extensions=config_tuple[3],
            check_interval=config_tuple[4],
            stable_threshold=config_tuple[5]
        )

        # Pass the single Config object
        monitor = CachedFileMonitor(app_config)
        monitor.run()
    except Exception as e:
        logging.error(f"Failed to initialize or run CachedFileMonitor: {e}", exc_info=True)

if __name__ == "__main__":
    main()