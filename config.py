# config.py
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict

try:
    import questionary
except ImportError:
    questionary = None

# --- Configuration for External File Type Categories ---
CATEGORIES_FILENAME = "file_type_presets.conf"
# Determine the directory of the config.py script to locate CATEGORIES_FILENAME nearby
CONFIG_SCRIPT_DIR = Path(__file__).resolve().parent
CATEGORIES_FILE_PATH = CONFIG_SCRIPT_DIR / CATEGORIES_FILENAME

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
        with filepath.open("w", encoding="utf-8") as f:
            f.write("# File Type Categories Configuration\n")
            f.write("# Format: Category Name,.ext1,.ext2,...\n")
            f.write("# Lines starting with # are comments and will be ignored.\n")
            f.write("# Blank lines are also ignored.\n\n")
            for name, exts in categories.items():
                f.write(f"{name},{','.join(exts)}\n")
        print(f"INFO: Created default file type categories configuration at: {filepath}")
    except IOError as e:
        print(f"ERROR: Could not write default categories file to {filepath}: {e}")

def load_file_type_categories_from_file(filepath: Path) -> Dict[str, List[str]]:
    """
    Loads file type categories from a comma-delimited text file.
    If the file doesn't exist, it attempts to create it with default categories.
    """
    loaded_categories: Dict[str, List[str]] = {}
    if not filepath.exists():
        print(f"INFO: Categories file not found at {filepath}.")
        save_categories_to_file(filepath, DEFAULT_FILE_TYPE_CATEGORIES)
        # After saving, we expect the file to exist, so we can proceed to load it.
        # If save_categories_to_file failed, it would have printed an error,
        # and this load attempt might yield an empty dict or an error.

    if filepath.exists():
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

                    extensions = [ext.strip() for ext in extensions_str.split(',') if ext.strip().startswith(".")]
                    
                    if not extensions:
                        print(f"WARNING: No valid extensions found for category '{category_name}' on line {line_num} in {filepath}: '{line}'. Skipping category.")
                        continue
                        
                    if category_name in loaded_categories:
                         print(f"WARNING: Duplicate category name '{category_name}' found on line {line_num} in {filepath}. Overwriting previous entry.")
                    loaded_categories[category_name] = extensions
            if not loaded_categories and DEFAULT_FILE_TYPE_CATEGORIES: # File was empty or all lines invalid
                 print(f"WARNING: No valid categories loaded from {filepath}. Consider checking its format.")
        except IOError as e:
            print(f"ERROR: Could not read categories file {filepath}: {e}")
        except Exception as e: # Catch other potential parsing errors
            print(f"ERROR: Unexpected error parsing {filepath}: {e}")
    
    if not loaded_categories: # If still no categories (e.g., file creation failed, or file is empty/unreadable)
        print(f"INFO: Using hardcoded default file type categories as a fallback.")
        return DEFAULT_FILE_TYPE_CATEGORIES # Fallback to hardcoded defaults
        
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
        user_input = input(f"File extensions to watch for (comma-separated) [{default_extensions_str}]: ")
        user_input = user_input or default_extensions_str
        return [ext.strip() for ext in user_input.split(",") if ext.strip().startswith(".")]

    selected_extensions = set()
    try:
        if not FILE_TYPE_CATEGORIES:
            print("WARNING: No file type categories are defined. Please check your categories configuration file or the script defaults.")
            # Fallback to simple text input if no categories defined
            custom_ext_str = questionary.text(
                "No predefined categories found. Enter custom extensions, comma-separated (must start with '.'):",
                validate=lambda text: True if all(t.strip().startswith(".") for t in text.split(',')) or not text.strip() else "All extensions must start with a dot."
            ).ask()
            if custom_ext_str:
                return sorted(list({ext.strip() for ext in custom_ext_str.split(',') if ext.strip().startswith(".")}))
            return []


        choices = []
        default_set = set(ext.strip() for ext in default_extensions_str.split(","))
        
        for category_name, extensions_in_category in FILE_TYPE_CATEGORIES.items():
            is_default_category = default_set == set(extensions_in_category) # Check if this whole category matches the simple default string
            display_text = f"{category_name} ({', '.join(extensions_in_category)})"
            choices.append(questionary.Choice(title=display_text, value=category_name, checked=is_default_category))

        if not choices: # Should not happen if FILE_TYPE_CATEGORIES is populated
            print("WARNING: No categories available to select.") # Should be caught by the FILE_TYPE_CATEGORIES check above

        selected_categories = questionary.checkbox(
            "Select file type categories to monitor (Space to toggle, Enter to confirm):",
            choices=choices
        ).ask()

        if selected_categories:
            for category_name in selected_categories:
                selected_extensions.update(FILE_TYPE_CATEGORIES[category_name])

        if questionary.confirm("Add custom file extensions (e.g., .log, .dat)?", default=False).ask():
            custom_ext_str = questionary.text(
                "Enter custom extensions, comma-separated (must start with '.'):",
                validate=lambda text: True if all(t.strip().startswith(".") for t in text.split(',')) or not text.strip() else "All extensions must start with a dot. Example: .log,.data"
            ).ask()
            if custom_ext_str:
                custom_extensions = {ext.strip() for ext in custom_ext_str.split(',') if ext.strip().startswith(".")}
                selected_extensions.update(custom_extensions)
        
        if not selected_extensions:
            if questionary.confirm(f"No extensions selected. Use default Slackware packages ({','.join(DEFAULT_FILE_TYPE_CATEGORIES.get('Slackware Packages', []))})?", default=True).ask():
                return DEFAULT_FILE_TYPE_CATEGORIES.get("Slackware Packages", []) # Use a known default key
            else:
                print("Warning: No file extensions selected for monitoring.")
                return []
        
        return sorted(list(selected_extensions))

    except Exception as e:
        print(f"An error occurred during interactive extension selection: {e}")
        print("Falling back to manual text input for file extensions.")
        user_input = input(f"File extensions to watch for (comma-separated) [{default_extensions_str}]: ")
        user_input = user_input or default_extensions_str
        return [ext.strip() for ext in user_input.split(",") if ext.strip().startswith(".")]


def get_config(auto=False):
    def get_input_or_accept_default(prompt, default, validator=None, is_path=False):
        if auto:
            return default
        while True:
            user_input_str = input(f"{prompt} [{default}]: ")
            user_input_str = user_input_str or str(default)
            value_to_validate = Path(user_input_str) if is_path else user_input_str
            if validator and not validator(value_to_validate):
                print("Invalid input or path does not exist. Please try again.")
            else:
                return user_input_str

    default_monitor_dir = "/tmp"
    MONITOR_DIR_STR = get_input_or_accept_default(
        "Path to be monitored?", default_monitor_dir,
        lambda x: Path(x).exists() and Path(x).is_dir(), is_path=True
    )
    DEST_BASE_DIR_STR = get_input_or_accept_default(
        "Base Backup Directory?", str(Path.home()),
        lambda x: Path(x).exists() and Path(x).is_dir(), is_path=True
    )
    DEST_SUBDIR_NAME = get_input_or_accept_default("Destination Subdirectory Name?", "SavedCachedFiles")

    # Use the 'Slackware Packages' from the (potentially file-loaded) FILE_TYPE_CATEGORIES as the basis for the default string
    # This makes the displayed default consistent with what might be in the file.
    default_slackware_extensions = FILE_TYPE_CATEGORIES.get("Slackware Packages", [".tgz",".tbz",".tlz",".txz"])
    default_extensions_str = ",".join(default_slackware_extensions)

    if auto:
        FILE_EXTENSIONS = [ext.strip() for ext in default_extensions_str.split(",") if ext.strip().startswith(".")]
    else:
        print("\n--- Configure File Extensions ---")
        # Pass the potentially dynamic default_extensions_str to the interactive selector
        FILE_EXTENSIONS = get_extensions_interactively(default_extensions_str)
        print("--- End of File Extension Configuration ---\n")

    if not FILE_EXTENSIONS:
        if not auto:
             print(f"Warning: No valid file extensions were configured. Using default: {default_extensions_str}")
        FILE_EXTENSIONS = [ext.strip() for ext in default_extensions_str.split(",") if ext.strip().startswith(".")]
        if not FILE_EXTENSIONS and auto: # Should only happen if default_slackware_extensions was empty AND it was auto mode
            raise ValueError("Default file extensions are invalid or empty. Check categories file or script defaults.")

    CHECK_INTERVAL_MINUTES_STR = get_input_or_accept_default(
        "Monitor time (in minutes)?", "5", lambda x: x.isdigit() and int(x) > 0
    )
    STABLE_THRESHOLD_MINUTES_STR = get_input_or_accept_default(
        "File considered stable after how many minutes of no changes?", "2", lambda x: x.isdigit() and int(x) >= 0
    )

    monitor_dir_path = Path(MONITOR_DIR_STR)
    dest_base_dir_path = Path(DEST_BASE_DIR_STR)
    check_interval_seconds = int(CHECK_INTERVAL_MINUTES_STR) * 60
    stable_threshold_seconds = int(STABLE_THRESHOLD_MINUTES_STR) * 60

    return (
        monitor_dir_path, dest_base_dir_path, DEST_SUBDIR_NAME,
        FILE_EXTENSIONS, check_interval_seconds, stable_threshold_seconds
    )