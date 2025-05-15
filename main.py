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

# Import Config and DEFAULT_CONFIG_INI_PATH for checking
from config import get_config, Config, DEFAULT_CONFIG_INI_PATH
from file_monitor import CachedFileMonitor

# Setup logging (consider moving to a dedicated logging setup function if it gets complex)
# For a service, logging to a file is often preferred over basicConfig's stream handler.
# However, basicConfig is fine for now.
log_file_path = Path("/var/log/cached_file_monitor.log") # Example log file path
try:
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    # Attempt to set up file logging.
    # If this fails (e.g. permissions), it will fall back to console.
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler(sys.stdout) # Also log to console
        ]
    )
except OSError as e:
    # Fallback to console-only logging if file logging setup fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logging.warning(f"Could not set up file logging to {log_file_path}: {e}. Logging to console only.")


# Get a logger instance for this module
logger = logging.getLogger(__name__)


shutdown_event = threading.Event()

def get_current_user_group() -> Tuple[Optional[str], Optional[str]]:
    try:
        uid = os.getuid()
        gid = os.getgid()
        user_name = pwd.getpwuid(uid).pw_name
        group_name = grp.getgrgid(gid).gr_name
        return user_name, group_name
    except Exception as e:
        logger.error(f"Could not determine user/group: {e}")
        return None, None

def signal_handler(signum, frame):
    logger.info(f"Signal {signal.Signals(signum).name} received. Initiating shutdown...")
    shutdown_event.set()

def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("=====================================================================")
    logger.info("Backup Slackbuilds Application - Main Script Initializing")
    logger.info("=====================================================================")


    user_name, group_name = get_current_user_group()
    if user_name and group_name:
        logger.info(f"Script running as user: '{user_name}', group: '{group_name}'.")
    else:
        # This warning was: "Proceeding with default configuration."
        # Now, config must exist.
        logger.warning("Could not determine current user and group.")

    # --- Configuration Check ---
    # The --auto or --no-input flags are no longer relevant for config loading behavior here,
    # as config.ini MUST exist. These flags might be repurposed for other things if needed.
    # use_defaults_cli_arg = "--no-input" in sys.argv or "--auto" in sys.argv # Keep if used elsewhere

    if not DEFAULT_CONFIG_INI_PATH.exists():
        logger.critical(f"Configuration file '{DEFAULT_CONFIG_INI_PATH}' not found.")
        logger.critical("Please run 'python setup.py' to configure the application first.")
        sys.exit(1)

    try:
        # get_config now strictly loads from INI or raises an error.
        # The 'auto' parameter is effectively True by default in the new get_config.
        app_config = get_config(config_ini_path=DEFAULT_CONFIG_INI_PATH)
        logger.info(f"Successfully loaded configuration from {DEFAULT_CONFIG_INI_PATH}")
    except (FileNotFoundError, ValueError) as e: # Catch errors from get_config
        logger.critical(f"Failed to load configuration: {e}")
        logger.critical(f"Ensure '{DEFAULT_CONFIG_INI_PATH}' is valid or run 'python setup.py' again.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An unexpected error occurred during configuration loading: {e}", exc_info=True)
        sys.exit(1)


    # --- Post-configuration logic (e.g., overrides, directory creation) ---
    is_nobody_nogroup = (user_name == "nobody" and group_name == "nogroup")
    if is_nobody_nogroup:
        logger.warning(
            "CRITICAL: Script detected it is running as 'nobody:nogroup'. "
            "Backup path will be overridden to '/opt/stor0/SavedCachedFiles'. "
            "Ensure this path is writable by 'nobody:nogroup'."
        )
        # It's generally better if overrides are also part of the config or clearly documented.
        # Forcing an override like this can be surprising.
        # Consider if this logic is still desired or if setup.py should guide this.
        # For now, keeping the existing override logic:
        original_dest_base = app_config.dest_base_dir
        original_dest_subdir = app_config.dest_subdir_name
        
        app_config.dest_base_dir = Path("/opt/stor0") # Hardcoded override
        app_config.dest_subdir_name = "SavedCachedFiles" # Hardcoded override
        
        logger.info(f"Path override for 'nobody:nogroup':")
        logger.info(f"  Original Destination Base: {original_dest_base}")
        logger.info(f"  Original Destination Subdir: {original_dest_subdir}")
        logger.info(f"  Overridden Destination Base: {app_config.dest_base_dir}")
        logger.info(f"  Overridden Destination Subdir: {app_config.dest_subdir_name}")


    effective_dest_dir = app_config.dest_base_dir / app_config.dest_subdir_name
    try:
        effective_dest_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured effective backup destination directory exists: {effective_dest_dir}")
    except OSError as e:
        logger.error(f"CRITICAL: Could not create effective backup destination directory {effective_dest_dir}: {e}")
        logger.error("Please check permissions and path configuration. Exiting.")
        sys.exit(1) # This seems critical enough to exit.

    logger.info(f"Final effective configuration to be used:")
    logger.info(f"  Monitor Directory: {app_config.monitor_dir}")
    logger.info(f"  Destination Base: {app_config.dest_base_dir}")
    logger.info(f"  Destination Subdir: {app_config.dest_subdir_name}")
    logger.info(f"  Effective Backup Dir: {effective_dest_dir}")
    logger.info(f"  File Extensions: {app_config.file_extensions}")
    logger.info(f"  Check Interval: {app_config.check_interval // 60} minutes ({app_config.check_interval} seconds)")
    logger.info(f"  Stable Threshold: {app_config.stable_threshold // 60} minutes ({app_config.stable_threshold} seconds)")
    logger.info(f"  Categories File Path: {app_config.categories_file_path}")
    logger.info("---------------------------------------------------------------------")

    try:
        monitor = CachedFileMonitor(app_config, shutdown_event)
        monitor.run()

    except SystemExit: # Can be raised by sys.exit()
        logger.info("SystemExit caught in main. Application is terminating.")
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt caught in main. Initiating shutdown...")
        shutdown_event.set() # Ensure event is set if not already
    except Exception as e:
        logger.error(f"Unhandled exception in main execution block: {e}", exc_info=True)
    finally:
        if shutdown_event.is_set():
            logger.info("Main script determined shutdown event was set. Finalizing.")
        else:
            logger.info("Main script execution finished (possibly due to an error before shutdown event was set).")
        logger.info("=====================================================================")
        logger.info("Backup Slackbuilds Application - Main Script Shutdown Complete")
        logger.info("=====================================================================")


if __name__ == "__main__":
    # Ensure current script directory is in path for imports if running directly
    # This can be helpful if the module isn't "installed"
    current_script_path = Path(__file__).resolve().parent
    if str(current_script_path) not in sys.path:
        sys.path.insert(0, str(current_script_path))
        
    main()