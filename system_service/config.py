# config.py
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union # Added Union for type hinting

try:
    import questionary
except ImportError:
    questionary = None

# --- Configuration for External File Type Categories ---
# Determine the directory of the config.py script
CONFIG_SCRIPT_DIR = Path(__file__).resolve().parent
# Define a 'data' subdirectory within the application's installation directory
# for storing configuration files like presets.
DATA_DIR = CONFIG_SCRIPT_DIR / "data"
CATEGORIES_FILENAME = "file_type_presets.conf"
# Path to categories file within the 'data' subdirectory
CATEGORIES_FILE_PATH = DATA_DIR / CATEGORIES_FILENAME

# Default categories, used if the file is missing or to create it initially.
DEFAULT_FILE_TYPE_CATEGORIES: Dict[str, List[str]] = {
    "Slackware Packages": [".tgz", ".tbz", ".tlz", ".txz"],
    "Disk Images": [".iso", ".img", ".raw", ".qcow2", ".vdi", ".vmdk"],
    "Documents": [".pdf", ".txt", ".md", ".odt", ".doc", ".docx", ".rtf"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".heic"],
    "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg"],
    "Video": [".mp4", ".mkv", ".avi", ".mov", ".webm"],
    "Archives (General)": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Source Code": [".py", ".c", ".cpp", ".java", ".js", ".html", ".css", ".sh"],
}
# --- End of Configuration for External File Type Categories ---

@dataclass
class Config:
    monitor_dir: Path
    dest_base_dir: Path
    dest_subdir_name: str
    file_extensions: List[str]
    check_interval: int  # in seconds
    stable_threshold: int  # in seconds (total time file must be stable)

def save_categories_to_file(filepath: Path, categories: Dict[str, List[str]]):
    """Saves the given categories to the specified file."""
    try:
        # Ensure the parent directory (DATA_DIR) exists before writing the file.
        # The setup script should primarily handle its creation and permissions,
        # but this provides a fallback if config.py is used independently.
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with filepath.open("w", encoding="utf-8") as f:
            f.write("# File Type Categories Configuration\n")
            f.write("# Format: Category Name,.ext1,.ext2,...\n")
            f.write("# Lines starting with # are comments and will be ignored.\n")
            f.write("# Blank lines are also ignored.\n\n")
            for name, exts in categories.items():
                f.write(f"{name},{','.join(exts)}\n")
        print(f"INFO: Created/updated file type categories configuration at: {filepath}")
    except IOError as e:
        print(f"ERROR: Could not write categories file to {filepath}: {e}")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while saving categories to {filepath}: {e}")

def load_file_type_categories_from_file(filepath: Path) -> Dict[str, List[str]]:
    """
    Loads file type categories from a comma-delimited text file.
    If the file doesn't exist, it attempts to create it with default categories.
    """
    loaded_categories: Dict[str, List[str]] = {}
    if not filepath.exists():
        print(f"INFO: Categories file not found at {filepath}.")
        # Attempt to create the 'data' directory if it doesn't exist before saving.
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            print(f"INFO: Ensured data directory exists: {filepath.parent}")
        except Exception as e:
            print(f"WARNING: Could not create data directory {filepath.parent}: {e}. Default categories might not be saved.")
        save_categories_to_file(filepath, DEFAULT_FILE_TYPE_CATEGORIES)
        # After saving, we expect the file to exist, so we can proceed to load it.
        # If save_categories_to_file failed, it would have printed an error.

    if filepath.exists(): # Re-check existence after attempting to save defaults
        try:
            with filepath.open("r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue  # Skip empty lines and comments

                    parts = line.split(',', 1) # Split only on the first comma
                    if len(parts) < 2:
                        print(f"WARNING: Malformed line {line_num} in {filepath}: '{line}'. Skipping.")
                        continue

                    category_name = parts[0].strip()
                    extensions_str = parts[1].strip()
                    
                    if not category_name:
                        print(f"WARNING: Missing category name on line {line_num} in {filepath}: '{line}'. Skipping.")
                        continue

                    # Ensure extensions are valid (start with a dot)
                    extensions = [ext.strip() for ext in extensions_str.split(',') if ext.strip().startswith(".")]
                    
                    if not extensions:
                        print(f"WARNING: No valid extensions (starting with '.') found for category '{category_name}' on line {line_num} in {filepath}: '{line}'. Skipping category.")
                        continue
                        
                    if category_name in loaded_categories:
                         print(f"WARNING: Duplicate category name '{category_name}' found on line {line_num} in {filepath}. Overwriting previous entry.")
                    loaded_categories[category_name] = extensions
            
            if not loaded_categories and DEFAULT_FILE_TYPE_CATEGORIES: # File was empty or all lines invalid
                 print(f"WARNING: No valid categories loaded from {filepath}. Consider checking its format or content.")
        except IOError as e:
            print(f"ERROR: Could not read categories file {filepath}: {e}")
        except Exception as e: # Catch other potential parsing errors
            print(f"ERROR: Unexpected error parsing {filepath}: {e}")
    
    if not loaded_categories: # If still no categories (e.g., file creation failed, or file is empty/unreadable)
        print(f"INFO: Using hardcoded default file type categories as a fallback because {filepath} could not be loaded or was empty.")
        return DEFAULT_FILE_TYPE_CATEGORIES.copy() # Return a copy to prevent modification of defaults
        
    return loaded_categories

# Load categories when the module is imported.
# This makes FILE_TYPE_CATEGORIES available globally within this module.
FILE_TYPE_CATEGORIES = load_file_type_categories_from_file(CATEGORIES_FILE_PATH)


def get_extensions_interactively(default_extensions_str: str) -> List[str]:
    """
    Prompts the user to select file extensions interactively using questionary.
    Uses FILE_TYPE_CATEGORIES loaded from the external file or defaults.
    """
    if not questionary:
        print("Warning: 'questionary' library not found. Falling back to manual text input for file extensions.")
        print(f"You can install it with: pip install questionary")
        user_input_str = input(f"File extensions to watch for (comma-separated, e.g., .tgz,.iso) [{default_extensions_str}]: ")
        user_input_str = user_input_str or default_extensions_str
        return [ext.strip() for ext in user_input_str.split(",") if ext.strip().startswith(".")]

    selected_extensions: set[str] = set() # Use set for efficient addition
    try:
        if not FILE_TYPE_CATEGORIES:
            print("WARNING: No file type categories are defined. Please check your categories configuration file or the script defaults.")
            custom_ext_str = questionary.text(
                "No predefined categories found. Enter custom extensions, comma-separated (must start with '.'):",
                validate=lambda text: True if all(t.strip().startswith(".") for t in text.split(',')) or not text.strip() else "All extensions must start with a dot. Example: .log,.data"
            ).ask()
            if custom_ext_str:
                return sorted(list({ext.strip() for ext in custom_ext_str.split(',') if ext.strip().startswith(".")}))
            return [] # Return empty list if no custom extensions provided

        # Prepare choices for questionary
        choices = []
        # Convert default_extensions_str to a set for easier comparison if needed,
        # though direct category match is more robust here.
        # default_selected_extensions_set = set(ext.strip() for ext in default_extensions_str.split(","))
        
        for category_name, extensions_in_category in FILE_TYPE_CATEGORIES.items():
            # Check if this category's extensions exactly match the default_extensions_str
            # This is a simple check; more complex default selection logic might be needed
            # if defaults can span multiple categories or be partial.
            is_default_category_selected = (",".join(extensions_in_category) == default_extensions_str)
            
            display_text = f"{category_name} ({', '.join(extensions_in_category)})"
            choices.append(questionary.Choice(title=display_text, value=category_name, checked=is_default_category_selected))

        if not choices:
             print("WARNING: No categories available to select from FILE_TYPE_CATEGORIES.")
             # Fallback similar to when FILE_TYPE_CATEGORIES is empty
             custom_ext_str = questionary.text(
                "No categories to display. Enter custom extensions, comma-separated (must start with '.'):",
                validate=lambda text: True if all(t.strip().startswith(".") for t in text.split(',')) or not text.strip() else "All extensions must start with a dot."
             ).ask()
             if custom_ext_str:
                return sorted(list({ext.strip() for ext in custom_ext_str.split(',') if ext.strip().startswith(".")}))
             return []


        selected_categories = questionary.checkbox(
            "Select file type categories to monitor (Space to toggle, Enter to confirm):",
            choices=choices
        ).ask()

        if selected_categories: # selected_categories can be None if user cancels
            for category_name in selected_categories:
                selected_extensions.update(FILE_TYPE_CATEGORIES.get(category_name, []))

        # Ask for custom extensions
        if questionary.confirm("Add custom file extensions (e.g., .log, .dat)?", default=False).ask():
            custom_ext_str = questionary.text(
                "Enter custom extensions, comma-separated (must start with '.'):",
                validate=lambda text: True if all(t.strip().startswith(".") for t in text.split(',')) or not text.strip() else "All extensions must start with a dot. Example: .log,.data"
            ).ask()
            if custom_ext_str: # custom_ext_str can be None if user cancels
                custom_extensions = {ext.strip() for ext in custom_ext_str.split(',') if ext.strip().startswith(".")}
                selected_extensions.update(custom_extensions)
        
        if not selected_extensions:
            # Fallback to a known default if nothing was selected
            default_slackware_key = "Slackware Packages"
            default_slackware_exts = DEFAULT_FILE_TYPE_CATEGORIES.get(default_slackware_key, [])
            if questionary.confirm(f"No extensions selected. Use default '{default_slackware_key}' ({','.join(default_slackware_exts)})?", default=True).ask():
                return default_slackware_exts
            else:
                print("Warning: No file extensions selected for monitoring.")
                return [] # Return empty list if user explicitly refuses default
        
        return sorted(list(selected_extensions))

    except Exception as e: # Catch potential errors from questionary (e.g., if not fully installed/functional)
        print(f"An error occurred during interactive extension selection: {e}")
        print("Falling back to manual text input for file extensions.")
        user_input_str = input(f"File extensions to watch for (comma-separated) [{default_extensions_str}]: ")
        user_input_str = user_input_str or default_extensions_str
        return [ext.strip() for ext in user_input_str.split(",") if ext.strip().startswith(".")]


def get_config(auto: bool = False) -> tuple[Path, Path, str, List[str], int, int]:
    """
    Collects configuration from the user or uses defaults.
    Returns a tuple: (monitor_dir, dest_base_dir, dest_subdir_name, 
                      file_extensions, check_interval_seconds, stable_threshold_seconds)
    """
    def get_input_or_accept_default(prompt: str, default: Union[str, int, Path], validator=None, is_path: bool = False) -> str:
        if auto:
            return str(default) # Return string representation of default in auto mode
        while True:
            user_input_str = input(f"{prompt} [{default}]: ").strip()
            user_input_str = user_input_str or str(default)
            
            value_to_validate: Union[Path, str] = Path(user_input_str) if is_path else user_input_str
            
            if validator:
                validation_result = validator(value_to_validate)
                if validation_result is True: # Validator returns True for valid
                    return user_input_str
                else: # Validator returns error message string for invalid
                    print(f"Invalid input: {validation_result}. Please try again.")
            else: # No validator, accept the input
                return user_input_str

    # Path Validators
    def dir_exists_validator(p: Path) -> Union[bool, str]:
        if p.exists() and p.is_dir():
            return True
        return f"Path '{p}' does not exist or is not a directory."

    def base_dir_validator(p: Path) -> Union[bool, str]:
        # For base backup dir, it's okay if it doesn't exist yet if user intends to create it,
        # but it should be possible to create it (e.g., parent exists and is writable).
        # For simplicity here, we'll just check if it exists or if its parent exists.
        if p.exists() and p.is_dir():
            return True
        if p.parent.exists() and p.parent.is_dir():
            print(f"Note: Base directory '{p}' does not exist but parent '{p.parent}' does. It may be created by the application.")
            return True # Allow if parent exists, assuming it can be created.
        return f"Base directory '{p}' or its parent does not exist or is not a directory."

    # Numeric Validators
    def positive_int_validator(s: str) -> Union[bool, str]:
        if s.isdigit() and int(s) > 0:
            return True
        return "Must be a positive integer."

    def non_negative_int_validator(s: str) -> Union[bool, str]:
        if s.isdigit() and int(s) >= 0:
            return True
        return "Must be a non-negative integer."

    default_monitor_dir = "/tmp"
    monitor_dir_str = get_input_or_accept_default(
        "Path to be monitored?", default_monitor_dir,
        dir_exists_validator, is_path=True
    )
    
    # Default base directory to user's home directory.
    default_dest_base_dir = Path.home()
    dest_base_dir_str = get_input_or_accept_default(
        "Base Backup Directory?", str(default_dest_base_dir),
        base_dir_validator, is_path=True # Looser validation for base dir
    )
    
    dest_subdir_name_str = get_input_or_accept_default("Destination Subdirectory Name?", "SavedCachedFiles")

    # Default extensions based on "Slackware Packages" from loaded categories
    default_slackware_extensions = FILE_TYPE_CATEGORIES.get("Slackware Packages", [".tgz",".tbz",".tlz",".txz"])
    default_extensions_str = ",".join(default_slackware_extensions)

    file_extensions: List[str]
    if auto:
        print(f"INFO: Using default file extensions for 'auto' mode: {default_extensions_str}")
        file_extensions = [ext.strip() for ext in default_extensions_str.split(",") if ext.strip().startswith(".")]
    else:
        print("\n--- Configure File Extensions ---")
        file_extensions = get_extensions_interactively(default_extensions_str)
        print("--- End of File Extension Configuration ---\n")

    if not file_extensions:
        print(f"Warning: No valid file extensions were configured. Using default: {default_extensions_str}")
        file_extensions = [ext.strip() for ext in default_extensions_str.split(",") if ext.strip().startswith(".")]
        if not file_extensions: # This should only happen if default_slackware_extensions was empty
            # This is a critical failure if no extensions can be determined.
            raise ValueError("FATAL: No file extensions configured, and default extensions are also empty or invalid. Check categories file or script defaults.")

    check_interval_minutes_str = get_input_or_accept_default(
        "Monitor check interval (in minutes)?", "5", positive_int_validator
    )
    stable_threshold_minutes_str = get_input_or_accept_default(
        "File considered stable after how many minutes of no changes?", "2", non_negative_int_validator
    )

    # Convert to final types
    monitor_dir_path = Path(monitor_dir_str)
    dest_base_dir_path = Path(dest_base_dir_str)
    check_interval_seconds = int(check_interval_minutes_str) * 60
    stable_threshold_seconds = int(stable_threshold_minutes_str) * 60

    print(f"\nConfiguration Summary:")
    print(f"  Monitoring: {monitor_dir_path}")
    print(f"  Backup Base: {dest_base_dir_path}")
    print(f"  Backup Subdir: {dest_subdir_name_str}")
    print(f"  Extensions: {', '.join(file_extensions)}")
    print(f"  Check Interval: {check_interval_seconds}s ({check_interval_minutes_str} min)")
    print(f"  Stable Threshold: {stable_threshold_seconds}s ({stable_threshold_minutes_str} min)\n")

    return (
        monitor_dir_path, dest_base_dir_path, dest_subdir_name_str,
        file_extensions, check_interval_seconds, stable_threshold_seconds
    )

