# main.py
import os
import sys
import logging
from pathlib import Path
import pwd
import grp
from typing import Tuple, Optional
import signal
import threading

# config.py now handles Config dataclass and get_config returns a Config object
from config import get_config, Config
from file_monitor import CachedFileMonitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

shutdown_event = threading.Event()

def get_current_user_group() -> Tuple[Optional[str], Optional[str]]:
    try:
        uid = os.getuid()
        gid = os.getgid()
        user_name = pwd.getpwuid(uid).pw_name
        group_name = grp.getgrgid(gid).gr_name
        return user_name, group_name
    except Exception as e:
        logging.error(f"Could not determine user/group: {e}")
        return None, None

def signal_handler(signum, frame):
    logging.info(f"Signal {signal.Signals(signum).name} received. Initiating shutdown...")
    shutdown_event.set()

def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    user_name, group_name = get_current_user_group()

    if user_name and group_name:
        logging.info(f"Script initializing. Running as user: '{user_name}', group: '{group_name}'.")
    else:
        logging.warning("Could not determine current user and group. Proceeding with default configuration.")

    is_nobody_nogroup = (user_name == "nobody" and group_name == "nogroup")

    try:
        use_defaults_cli_arg = "--no-input" in sys.argv or "--auto" in sys.argv
        
        # get_config() now returns a Config object directly
        app_config = get_config(auto=use_defaults_cli_arg)

        # Override destination if running as nobody:nogroup
        if is_nobody_nogroup:
            logging.warning(
                "CRITICAL: Script detected it is running as 'nobody:nogroup'. "
                "Backup path will be overridden to '/opt/stor0/SavedCachedFiles'. " # Make sure this matches your desired override
                "Ensure this path is writable by 'nobody:nogroup'."
            )
            # Modify the existing app_config object's attributes
            app_config.dest_base_dir = Path("/opt/stor0") # Example override
            app_config.dest_subdir_name = "SavedCachedFiles" # Example override
            
            logging.info(f"Path override: Destination base directory set to '{app_config.dest_base_dir}' and subdirectory to '{app_config.dest_subdir_name}'.")
            
        # Ensure the effective destination directory exists
        # (especially if overridden or using defaults from INI/hardcoded)
        effective_dest_dir = app_config.dest_base_dir / app_config.dest_subdir_name
        try:
            effective_dest_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Ensured effective backup destination directory exists: {effective_dest_dir}")
        except OSError as e:
            logging.error(f"Could not create effective backup destination directory {effective_dest_dir}: {e}")
            # Decide if you want to exit or try to continue if this fails. For now, it logs and continues.

        logging.info(f"Final configuration loaded:")
        logging.info(f"  Monitor Directory: {app_config.monitor_dir}")
        logging.info(f"  Destination Base: {app_config.dest_base_dir}")
        logging.info(f"  Destination Subdir: {app_config.dest_subdir_name}")
        logging.info(f"  Effective Backup Dir: {effective_dest_dir}")
        logging.info(f"  File Extensions: {app_config.file_extensions}")
        logging.info(f"  Check Interval: {app_config.check_interval // 60} minutes")
        logging.info(f"  Stable Threshold: {app_config.stable_threshold // 60} minutes")
        logging.info(f"  Categories File: {app_config.categories_file_path}")


        monitor = CachedFileMonitor(app_config, shutdown_event)
        monitor.run()

    except SystemExit:
        logging.info("SystemExit caught in main. Performing cleanup.")
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt caught in main. Setting shutdown event.")
        shutdown_event.set()
    except Exception as e:
        logging.error(f"Unhandled exception in main: {e}", exc_info=True)
    finally:
        if shutdown_event.is_set():
            logging.info("Main script shutting down due to shutdown event.")
        else:
            logging.info("Main script execution finished normally or due to unhandled error before shutdown event.")

if __name__ == "__main__":
    main()