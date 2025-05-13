from pathlib import Path

def get_config():
    def get_input_or_accept_default(prompt, default):
        user_input = input(f"{prompt} [{default}]: ")
        if user_input:
            return user_input
        else:
            return default
    MONITOR_DIR = get_input_or_accept_default("Path to be monitored?:", "/tmp")
    """Path to be monitored, defaults to /tmp"""
    DEST_BASE_DIR = get_input_or_accept_default("Base Backup Directory?", Path.home())
    """Base path for backed up files, defaults to users home"""
    DEST_SUBDIR_NAME = get_input_or_accept_default("Destination Directory?", "SavedCachedFiles")
    """Subdirectory (within the base directory) to back up files"""
    FILE_EXTENSIONS = [".tgz", ".tbz", ".tlz", ".txz"]
    #To-Augment: allow for input, and accept single extensions, or a comma seperated list.
    #Future Enhancement: choose from a selection of common extensions?
    """File extensions to watch for"""
    CHECK_INTERVAL_SECONDS = get_input_or_accept_default("Monitor time (in seconds)?", 300)
    """How often (in seconds) should we look for new files"""
    #To-Fix: Standardize minutes of seconds between these two variables.
    STABLE_CHECKS_THRESHOLD = get_input_or_accept_default("Stable Time (in minutes?", 2)
    """How long, in minutes, does a file need to stay the same size"""

    return get_config(MONITOR_DIR, DEST_BASE_DIR, DEST_SUBDIR_NAME, FILE_EXTENSIONS, CHECK_INTERVAL_SECONDS, STABLE_CHECKS_THRESHOLD)