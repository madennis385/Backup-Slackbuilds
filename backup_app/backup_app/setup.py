#!/usr/bin/env python3
# setup_cached_monitor.py

import os
import sys
import shutil
import subprocess
from pathlib import Path
import pwd
import grp

# --- Configuration ---
APP_NAME = "cached_file_monitor"
DEFAULT_APP_INSTALL_DIR = Path(f"/opt/{APP_NAME}")
DEFAULT_SERVICE_USER = "nobody"
DEFAULT_SERVICE_GROUP = "nogroup"
# This is the backup destination hardcoded in main.py for nobody:nogroup
DEFAULT_SERVICE_BACKUP_BASE_DIR = Path("/opt/stor0")
DEFAULT_SERVICE_BACKUP_SUBDIR = "SavedCachedFiles"

LOG_DIR_BASE = Path("/var/log")
PID_DIR_BASE = Path("/var/run")

SOURCE_FILES_PY = ["main.py", "config.py", "file_monitor.py", "backup_db.py"]
SOURCE_CONFIG_FILE = "file_type_presets.conf" # This goes into the 'data' subdirectory

# --- Helper Functions ---

def check_root():
    """Exit if the script is not run as root."""
    if os.geteuid() != 0:
        print("ERROR: This script must be run as root or with sudo.")
        sys.exit(1)
    print("Running as root. Proceeding with setup.")

def prompt_user(message: str, default: str = None) -> str:
    """Prompt user for input with an optional default value."""
    if default:
        prompt_message = f"{message} [{default}]: "
    else:
        prompt_message = f"{message}: "
    
    while True:
        user_input = input(prompt_message).strip()
        if not user_input and default is not None:
            return default
        if user_input:
            return user_input
        if not user_input and default is None:
            print("Input cannot be empty.")


def find_python() -> str:
    """Find python3 executable."""
    python_exe = shutil.which("python3")
    if not python_exe:
        print("ERROR: python3 executable not found in PATH. Please install Python 3.")
        sys.exit(1)
    print(f"Found Python 3 at: {python_exe}")
    return python_exe

def check_user_group_exist(user_name: str, group_name: str):
    """Check if specified user and group exist."""
    try:
        pwd.getpwnam(user_name)
        print(f"User '{user_name}' found.")
    except KeyError:
        print(f"ERROR: User '{user_name}' does not exist. Please create it or choose an existing user.")
        sys.exit(1)
    try:
        grp.getgrnam(group_name)
        print(f"Group '{group_name}' found.")
    except KeyError:
        print(f"ERROR: Group '{group_name}' does not exist. Please create it or choose an existing group.")
        sys.exit(1)

def create_dir_safely(dir_path: Path, owner_user: str, owner_group: str, mode: int):
    """Create directory, set ownership and permissions."""
    try:
        if not dir_path.exists():
            print(f"Creating directory: {dir_path}")
            dir_path.mkdir(parents=True, exist_ok=False) # exist_ok=False to ensure we set perms on new dir
        else:
            print(f"Directory already exists: {dir_path}. Ensuring permissions...")

        uid = pwd.getpwnam(owner_user).pw_uid
        gid = grp.getgrnam(owner_group).gr_gid
        
        os.chown(dir_path, uid, gid)
        print(f"Set ownership of {dir_path} to {owner_user}:{owner_group}")
        
        os.chmod(dir_path, mode)
        print(f"Set permissions of {dir_path} to {oct(mode)}")

    except OSError as e:
        print(f"ERROR: Could not create or set permissions for {dir_path}: {e}")
        sys.exit(1)
    except KeyError as e:
        print(f"ERROR: Invalid user '{owner_user}' or group '{owner_group}': {e}")
        sys.exit(1)

def copy_file_safely(source_path: Path, dest_path: Path, owner_user: str, owner_group: str, mode: int):
    """Copy file, set ownership and permissions."""
    try:
        print(f"Copying {source_path} to {dest_path}")
        shutil.copy2(source_path, dest_path) # copy2 preserves metadata like timestamps

        uid = pwd.getpwnam(owner_user).pw_uid
        gid = grp.getgrnam(owner_group).gr_gid

        os.chown(dest_path, uid, gid)
        print(f"Set ownership of {dest_path} to {owner_user}:{owner_group}")

        os.chmod(dest_path, mode)
        print(f"Set permissions of {dest_path} to {oct(mode)}")

    except FileNotFoundError:
        print(f"ERROR: Source file not found: {source_path}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Could not copy or set permissions for {dest_path}: {e}")
        sys.exit(1)

def generate_rc_script_content(python_bin: str, script_path: str, app_user: str, app_name: str, log_file: str, pid_file: str) -> str:
    """Generates the content for the rc.d init script."""
    # Corrected LOG_FILE path (removed extra slash)
    return f"""#!/bin/sh
#
# /etc/rc.d/rc.{app_name}
#
# Init script for {app_name.replace('_', ' ').title()}

APP_NAME="{app_name}"
APP_USER="{app_user}"
PYTHON_BIN="{python_bin}"
SCRIPT_PATH="{script_path}"
PID_DIR=$(dirname "{pid_file}")
PID_FILE="{pid_file}"
LOG_DIR=$(dirname "{log_file}")
LOG_FILE="{log_file}"

start() {{
    echo "Starting ${{APP_NAME}}..."

    # Ensure PID and Log directories exist (should be created by setup)
    # but good to have a fallback for the service user.
    # Note: Service user might not have permission to create /var/run or /var/log subdirs
    # This is primarily the setup script's job.
    # mkdir -p "$PID_DIR"
    # chown $APP_USER "$PID_DIR" # This might fail if APP_USER is not root
    # mkdir -p "$LOG_DIR"
    # chown $APP_USER "$LOG_DIR" # This might fail

    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "${{APP_NAME}} is already running (PID: $(cat "$PID_FILE"))."
        return 1
    fi

    # Start in background, pass --auto to use defaults and nobody:nogroup logic
    # The user running the rc script (usually root) executes su
    su -s /bin/sh -c "nohup $PYTHON_BIN $SCRIPT_PATH --auto >> $LOG_FILE 2>&1 & echo \\$! > $PID_FILE" $APP_USER
    
    # Brief pause to allow PID file creation
    sleep 0.5 
    if [ -f "$PID_FILE" ]; then
        echo "${{APP_NAME}} started with PID $(cat "$PID_FILE")."
    else
        echo "ERROR: ${{APP_NAME}} started but PID file was not created. Check logs at $LOG_FILE."
        return 1
    fi
}}

stop() {{
    echo "Stopping ${{APP_NAME}}..."
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            sleep 1 # Give it a moment to stop gracefully
            if kill -0 "$PID" 2>/dev/null; then
                echo "Process $PID did not stop gracefully. Sending SIGKILL..."
                kill -9 "$PID"
            fi
            echo "${{APP_NAME}} stopped."
        else
            echo "Process not running (PID: $PID from stale PID file). Cleaning up."
        fi
        rm -f "$PID_FILE"
    else
        echo "No PID file found. Is ${{APP_NAME}} running?"
    fi
}}

restart() {{
    stop
    sleep 1
    start
}}

status() {{
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "${{APP_NAME}} is running with PID $PID."
            return 0
        else
            echo "${{APP_NAME}} PID file found ($PID_FILE), but process (PID: $PID) not running."
            return 1 # Process not running, but PID file exists
        fi
    else
        echo "${{APP_NAME}} is not running."
        return 3 # Service not running
    fi
}}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) restart ;;
    status) status ;;
    *) echo "Usage: $0 {{start|stop|restart|status}}" ;;
esac

exit 0
"""

# --- Main Setup Logic ---
def main():
    check_root()
    print(f"--- {APP_NAME} Setup ---")

    # 1. Get Python interpreter
    python_executable = find_python()

    # 2. Application Install Directory
    print("\n--- Application Installation ---")
    app_install_dir_str = prompt_user("Enter installation directory for the application scripts", str(DEFAULT_APP_INSTALL_DIR))
    app_install_dir = Path(app_install_dir_str)
    create_dir_safely(app_install_dir, "root", "root", 0o755)

    # 3. Application Data Directory (for sqlite DB and presets config)
    app_data_dir = app_install_dir / "data"
    # Service user/group will be prompted next, then used here.
    
    # 4. Service User/Group
    print("\n--- Service User Configuration ---")
    print(f"The {APP_NAME} service will run as a non-privileged user.")
    service_user = prompt_user("Enter user for the service to run as", DEFAULT_SERVICE_USER)
    service_group = prompt_user("Enter group for the service", DEFAULT_SERVICE_GROUP)
    check_user_group_exist(service_user, service_group)

    # Now create app_data_dir with service user ownership
    print(f"\nCreating application data directory: {app_data_dir}")
    create_dir_safely(app_data_dir, service_user, service_group, 0o775) # rwxrwxr-x

    # 5. Copy application files
    print("\n--- Copying Application Files ---")
    current_script_dir = Path(__file__).parent
    for py_file in SOURCE_FILES_PY:
        source_py = current_script_dir / py_file
        dest_py = app_install_dir / py_file
        copy_file_safely(source_py, dest_py, "root", "root", 0o644) # Readable by all, writable by root

    source_conf = current_script_dir / SOURCE_CONFIG_FILE
    dest_conf = app_data_dir / SOURCE_CONFIG_FILE # Goes into 'data' subdir
    if source_conf.exists():
        copy_file_safely(source_conf, dest_conf, service_user, service_group, 0o664) # rw-rw-r--
    else:
        print(f"WARNING: Source configuration file {SOURCE_CONFIG_FILE} not found. The application might create a default one in {app_data_dir}.")


    # 6. Service Backup Destination Directory (used by main.py when run as nobody:nogroup)
    print("\n--- Service Backup Destination ---")
    service_backup_base_str = prompt_user(
        f"Enter BASE directory for backups when service runs as '{service_user}:{service_group}'",
        str(DEFAULT_SERVICE_BACKUP_BASE_DIR)
    )
    service_backup_subdir_str = prompt_user(
        f"Enter SUBDIRECTORY name for these backups",
        str(DEFAULT_SERVICE_BACKUP_SUBDIR)
    )
    service_backup_dest_dir = Path(service_backup_base_str) / service_backup_subdir_str
    print(f"The service, when running as {service_user}:{service_group}, will attempt to save backups to: {service_backup_dest_dir}")
    print(f"Ensure your main.py script reflects this path for the '{service_user}:{service_group}' condition.")
    print(f"(Currently, your main.py seems to use /opt/stor0/SavedCachedFiles for nobody:nogroup)")
    
    if input(f"Do you want to create/ensure permissions for {service_backup_dest_dir} now? (y/n): ").lower() == 'y':
        create_dir_safely(service_backup_dest_dir, service_user, service_group, 0o775) # rwxrwxr-x
    else:
        print(f"Skipping creation/permission setting for {service_backup_dest_dir}. Please ensure it's manually configured.")


    # 7. Log Directory
    print("\n--- Log Directory Setup ---")
    log_dir = LOG_DIR_BASE / APP_NAME
    create_dir_safely(log_dir, service_user, service_group, 0o775) # rwxrwxr-x
    final_log_file = log_dir / f"{APP_NAME}.log"
    print(f"Log file will be: {final_log_file}")
    # Create an empty log file so service user owns it
    if not final_log_file.exists():
        final_log_file.touch()
        uid = pwd.getpwnam(service_user).pw_uid
        gid = grp.getgrnam(service_group).gr_gid
        os.chown(final_log_file, uid, gid)
        os.chmod(final_log_file, 0o664) # rw-rw-r--
        print(f"Created and permissioned empty log file: {final_log_file}")


    # 8. PID Directory
    print("\n--- PID Directory Setup ---")
    pid_dir = PID_DIR_BASE / APP_NAME
    create_dir_safely(pid_dir, service_user, service_group, 0o775) # rwxrwxr-x
    final_pid_file = pid_dir / f"{APP_NAME}.pid"
    print(f"PID file will be: {final_pid_file}")

    # 9. Generate and install rc.d script
    print("\n--- Init Script Generation ---")
    rc_script_name = f"rc.{APP_NAME}"
    rc_script_path = Path("/etc/rc.d") / rc_script_name
    
    main_script_full_path = app_install_dir / "main.py"

    rc_content = generate_rc_script_content(
        python_bin=python_executable,
        script_path=str(main_script_full_path),
        app_user=service_user,
        app_name=APP_NAME,
        log_file=str(final_log_file),
        pid_file=str(final_pid_file)
    )

    try:
        with open(rc_script_path, "w") as f:
            f.write(rc_content)
        print(f"Generated init script: {rc_script_path}")
        os.chmod(rc_script_path, 0o755) # rwxr-xr-x
        print(f"Set permissions for {rc_script_path} to 0755 (executable).")
    except Exception as e:
        print(f"ERROR: Could not write or set permissions for init script {rc_script_path}: {e}")
        sys.exit(1)

    # 10. Python Dependencies
    print("\n--- Python Dependencies ---")
    print("This application uses the 'questionary' Python library for interactive configuration.")
    print("If you run the script manually (not as a service with --auto), it will need this library.")
    if shutil.which("pip3"):
        print("You can typically install it using: pip3 install questionary")
    elif shutil.which("pip"):
        print("You can typically install it using: pip install questionary")
    else:
        print("Please ensure 'questionary' is installed via your preferred Python package management method.")


    print("\n--- Setup Complete! ---")
    print(f"Application installed to: {app_install_dir}")
    print(f"Data directory: {app_data_dir}")
    print(f"Service will run as: {service_user}:{service_group}")
    print(f"Service backup destination (for {service_user}:{service_group}): {service_backup_dest_dir} (ensure main.py matches this if not using defaults)")
    print(f"Log file: {final_log_file}")
    print(f"PID file: {final_pid_file}")
    print(f"Init script: {rc_script_path}")
    print("\nTo manage the service:")
    print(f"  Start:   {rc_script_path} start")
    print(f"  Stop:    {rc_script_path} stop")
    print(f"  Restart: {rc_script_path} restart")
    print(f"  Status:  {rc_script_path} status")
    print("\nTo make the service start on boot (Slackware):")
    print(f"1. Ensure {rc_script_path} is executable (it should be).")
    print(f"2. If it's not already, add it to /etc/rc.d/rc.local or manage through /etc/rc.d/rc.M (advanced).")
    print("   A common way for rc.M is to make it executable and it will be run if in rc.d.")
    print(f"   Ensure '/etc/rc.d/{rc_script_name}' is executable: chmod +x /etc/rc.d/{rc_script_name}")

if __name__ == "__main__":
    main()
