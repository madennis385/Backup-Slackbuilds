# main.py
import os
import sys
import logging
from pathlib import Path
# Import modules for checking user and group (assuming POSIX)
import pwd
import grp
from typing import Tuple, Optional # Import Tuple and Optional for type hinting

from config import get_config, Config # Import Config dataclass
from file_monitor import CachedFileMonitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_current_user_group() -> Tuple[Optional[str], Optional[str]]:
    """
    Gets the current username and group name.
    Assumes a POSIX-compliant system.
    Returns (username, groupname) or (None, None) if an error occurs.
    Note: Uses Tuple[Optional[str], Optional[str]] for Python < 3.9 compatibility with type hints.
    For Python 3.9+, tuple[Optional[str], Optional[str]] or tuple[str | None, str | None] (Python 3.10+) could be used.
    """
    try:
        uid = os.getuid()
        gid = os.getgid()
        user_name = pwd.getpwuid(uid).pw_name
        group_name = grp.getgrgid(gid).gr_name
        return user_name, group_name
    except Exception as e:
        logging.error(f"Could not determine user/group: {e}")
        return None, None

def main():
    user_name, group_name = get_current_user_group()

    if user_name and group_name:
        logging.info(f"Script initializing. Running as user: '{user_name}', group: '{group_name}'.")
    else:
        logging.warning("Could not determine current user and group. Proceeding with default configuration.")

    is_nobody_nogroup = (user_name == "nobody" and group_name == "nogroup")

    if is_nobody_nogroup:
        logging.warning(
            "CRITICAL: Script detected it is running as 'nobody:nogroup'. "
            "Backup path will be overridden to '/opt/SavedCachedFiles'. "
            "Ensure 'nobody:nogroup' has write permissions to '/opt' "
            "or that '/opt/SavedCachedFiles' is pre-created with appropriate ownership/permissions."
        )

    try:
        use_defaults = "--no-input" in sys.argv or "--auto" in sys.argv
        
        # Get base configuration
        # config_tuple is (monitor_dir, dest_base_dir, dest_subdir_name, file_extensions, check_interval, stable_threshold)
        config_values = get_config(auto=use_defaults)

        # Unpack for clarity, will re-pack into Config object
        monitor_dir_path_str = config_values[0]
        dest_base_dir_str = config_values[1]
        dest_subdir_name_str = config_values[2]
        file_extensions_list = config_values[3]
        check_interval_int = config_values[4]
        stable_threshold_int = config_values[5]

        # Override destination if running as nobody:nogroup
        if is_nobody_nogroup:
            effective_dest_base_dir = Path("/opt/stor0")
            effective_dest_subdir_name = "SavedCachedFiles"
            logging.info(f"Path override: Destination base directory set to '{effective_dest_base_dir}' and subdirectory to '{effective_dest_subdir_name}'.")
        else:
            effective_dest_base_dir = Path(dest_base_dir_str)
            effective_dest_subdir_name = dest_subdir_name_str
            
        # Create a Config object
        app_config = Config(
            monitor_dir=Path(monitor_dir_path_str),
            dest_base_dir=effective_dest_base_dir,
            dest_subdir_name=effective_dest_subdir_name,
            file_extensions=file_extensions_list,
            check_interval=check_interval_int,
            stable_threshold=stable_threshold_int
        )
        
        final_dest_dir = app_config.dest_base_dir / app_config.dest_subdir_name
        logging.info(f"Effective backup destination directory will be: {final_dest_dir}")

        monitor = CachedFileMonitor(app_config)
        monitor.run()

    except Exception as e:
        logging.error(f"Failed to initialize or run CachedFileMonitor: {e}", exc_info=True)

if __name__ == "__main__":
    main()

