
# config.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional
import configparser # For INI file handling
import os # For expanding user paths like ~
import logging
try:
    import questionary
except ImportError:
    questionary = None # Fallback if questionary is not installed

# --- Script and Default File Locations ---
CONFIG_SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_INI_PATH = CONFIG_SCRIPT_DIR / "config.ini"
DEFAULT_CATEGORIES_FILENAME = "file_type_presets.conf"

# --- Default File Type Categories (used if file is missing or to create it) ---
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

@dataclass
class Config:
    monitor_dir: Path
    dest_base_dir: Path
    dest_subdir_name: str
    file_extensions: List[str]
    check_interval: int  # in seconds
    stable_threshold: int  # in seconds (total time file must be stable)
    categories_file_path: Path # Path to the file_type_presets.conf

# Global variable to hold loaded categories, initialized by get_config
FILE_TYPE_CATEGORIES: Dict[str, List[str]] = {}

def save_categories_to_file(filepath: Path, categories: Dict[str, List[str]]):
    # ... (This function remains the same as in your original config.py)
    try:
        with filepath.open("w", encoding="utf-8") as f:
            f.write("# File Type Categories Configuration\n")
            f.write("# Format: Category Name,.ext1,.ext2,...\n")
            # ... (rest of the save logic) ...
            for name, exts in categories.items():
                f.write(f"{name},{','.join(exts)}\n")
        logging.info(f"Created/Updated file type categories configuration at: {filepath}")
    except IOError as e:
        logging.error(f"Could not write categories file to {filepath}: {e}")


def load_file_type_categories_from_file(filepath: Path) -> Dict[str, List[str]]:
    # ... (This function remains largely the same as in your original config.py)
    # ... (It should use logging instead of print for consistency if possible)
    global FILE_TYPE_CATEGORIES # Ensure it updates the global var
    loaded_categories: Dict[str, List[str]] = {}
    if not filepath.exists():
        logging.info(f"Categories file not found at {filepath}. Will attempt to create with defaults if interactive, or use hardcoded defaults.")
        save_categories_to_file(filepath, DEFAULT_FILE_TYPE_CATEGORIES) # Create it if missing

    if filepath.exists():
        try:
            with filepath.open("r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(',', 1)
                    if len(parts) < 2:
                        logging.warning(f"Malformed line {line_num} in {filepath}: '{line}'. Skipping.")
                        continue
                    category_name = parts[0].strip()
                    extensions_str = parts[1].strip()
                    if not category_name:
                        logging.warning(f"Missing category name on line {line_num} in {filepath}: '{line}'. Skipping.")
                        continue
                    extensions = [ext.strip() for ext in extensions_str.split(',') if ext.strip().startswith(".")]
                    if not extensions:
                        logging.warning(f"No valid extensions for category '{category_name}' on line {line_num} in {filepath}: '{line}'. Skipping.")
                        continue
                    if category_name in loaded_categories:
                         logging.warning(f"Duplicate category name '{category_name}' on line {line_num} in {filepath}. Overwriting.")
                    loaded_categories[category_name] = extensions
            if not loaded_categories:
                 logging.warning(f"No valid categories loaded from {filepath}. Check format.")
        except IOError as e:
            logging.error(f"Could not read categories file {filepath}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error parsing categories file {filepath}: {e}")

    if not loaded_categories:
        logging.info(f"Using hardcoded default file type categories as a fallback.")
        FILE_TYPE_CATEGORIES = DEFAULT_FILE_TYPE_CATEGORIES.copy()
        return FILE_TYPE_CATEGORIES

    FILE_TYPE_CATEGORIES = loaded_categories
    return loaded_categories


def get_extensions_interactively(current_default_extensions: List[str]) -> List[str]:
    # ... (This function remains largely the same as in your original config.py)
    # ... (It should use the global FILE_TYPE_CATEGORIES loaded by load_file_type_categories_from_file)
    global FILE_TYPE_CATEGORIES
    if not questionary:
        logging.warning("'questionary' library not found. Falling back to manual text input for file extensions.")
        default_extensions_str = ",".join(current_default_extensions)
        user_input_str = input(f"File extensions to watch for (comma-separated) [{default_extensions_str}]: ")
        user_input_str = user_input_str or default_extensions_str
        return [ext.strip() for ext in user_input_str.split(",") if ext.strip().startswith(".")]

    selected_extensions = set()
    # ... (rest of the interactive logic using questionary and FILE_TYPE_CATEGORIES)
    # Example snippet (you'll need to adapt your full logic here):
    if not FILE_TYPE_CATEGORIES:
        logging.warning("No file type categories available for interactive selection.")
        # Fallback to simple input
        default_extensions_str = ",".join(current_default_extensions)
        user_input_str = input(f"File extensions (comma-separated) [{default_extensions_str}]: ")
        user_input_str = user_input_str or default_extensions_str
        return [ext.strip() for ext in user_input_str.split(",") if ext.strip().startswith(".")]

    choices = []
    # Convert current_default_extensions to a set for easier checking
    default_set = set(current_default_extensions)

    for category_name, extensions_in_category in FILE_TYPE_CATEGORIES.items():
        # Check if all extensions in this category are part of the default set
        is_default_category_checked = default_set.issuperset(set(extensions_in_category))
        display_text = f"{category_name} ({', '.join(extensions_in_category)})"
        choices.append(questionary.Choice(title=display_text, value=category_name, checked=is_default_category_checked))

    # ... (the rest of your questionary logic for checkboxes, custom input etc.)
    # For brevity, I'm not reproducing the entire questionary flow.
    # Ensure it returns a list of selected extension strings.
    # This is a placeholder for your detailed interactive extension selection.
    logging.info("Interactive extension selection placeholder. Implement full logic or fallback.")
    selected_categories = questionary.checkbox("Select categories:", choices=choices).ask()
    if selected_categories:
        for cat_name in selected_categories:
            selected_extensions.update(FILE_TYPE_CATEGORIES[cat_name])
    # Add custom extension logic too
    if not selected_extensions:
        return current_default_extensions # Fallback if nothing selected
    return sorted(list(selected_extensions))


def _get_path_from_input(prompt: str, default_path: str, is_dir: bool = True) -> Path:
    while True:
        user_input_str = input(f"{prompt} [{default_path}]: ").strip()
        path_str = user_input_str or default_path
        resolved_path = Path(os.path.expanduser(path_str)).resolve()
        if is_dir:
            if resolved_path.is_dir():
                return resolved_path
            else:
                logging.error(f"Path '{resolved_path}' is not a valid directory or does not exist. Please try again.")
        else: # is_file or generic path
            # For categories file, it might not exist yet if we're creating it.
            # So we might just accept the path and let file creation handle it.
            return resolved_path # Or add specific checks like .parent.exists()

def get_config_interactively(current_config: Optional[Config] = None) -> Config:
    """Gets configuration interactively, using current_config for defaults if provided."""
    global FILE_TYPE_CATEGORIES # Ensure we use the global categories

    # --- Set up defaults for prompts ---
    if current_config:
        default_monitor_dir = str(current_config.monitor_dir)
        default_dest_base_dir = str(current_config.dest_base_dir)
        default_dest_subdir_name = current_config.dest_subdir_name
        default_file_extensions = current_config.file_extensions # list
        default_check_interval_min = str(current_config.check_interval // 60)
        default_stable_threshold_min = str(current_config.stable_threshold // 60)
        default_categories_path_str = str(current_config.categories_file_path)
    else: # Absolute defaults if no current config
        default_monitor_dir = "/tmp"
        default_dest_base_dir = "/opt/stor0"
        default_dest_subdir_name = "SavedCachedFiles"
        default_file_extensions = DEFAULT_FILE_TYPE_CATEGORIES.get("Slackware Packages", [".tgz",".tbz",".tlz",".txz"])
        default_check_interval_min = "5"
        default_stable_threshold_min = "2"
        default_categories_path_str = str(CONFIG_SCRIPT_DIR / DEFAULT_CATEGORIES_FILENAME)

    # --- Interactive Prompts ---
    monitor_dir = _get_path_from_input("Path to be monitored?", default_monitor_dir, is_dir=True)
    dest_base_dir = _get_path_from_input("Base Backup Directory?", default_dest_base_dir, is_dir=True)
    dest_subdir_name = input(f"Destination Subdirectory Name? [{default_dest_subdir_name}]: ").strip() or default_dest_subdir_name

    # Categories file path
    categories_file_input_str = input(f"Path to file type categories configuration? [{default_categories_path_str}]: ").strip()
    categories_file_path_interactive = Path(os.path.expanduser(categories_file_input_str or default_categories_path_str)).resolve()

    # (Re)Load categories based on potentially new path before prompting for extensions
    FILE_TYPE_CATEGORIES = load_file_type_categories_from_file(categories_file_path_interactive)

    logging.info("\n--- Configure File Extensions ---")
    file_extensions_list = get_extensions_interactively(default_file_extensions) # Pass current defaults
    logging.info("--- End of File Extension Configuration ---\n")

    if not file_extensions_list: # Ensure we have some extensions
        logging.warning(f"No valid file extensions configured. Using default: {','.join(default_file_extensions)}")
        file_extensions_list = default_file_extensions

    while True:
        check_interval_min_str = input(f"Monitor time (in minutes)? [{default_check_interval_min}]: ").strip() or default_check_interval_min
        if check_interval_min_str.isdigit() and int(check_interval_min_str) > 0:
            break
        logging.error("Invalid input. Monitor time must be a positive integer.")

    while True:
        stable_threshold_min_str = input(f"File stable after how many minutes? [{default_stable_threshold_min}]: ").strip() or default_stable_threshold_min
        if stable_threshold_min_str.isdigit() and int(stable_threshold_min_str) >= 0:
            break
        logging.error("Invalid input. Stable threshold must be a non-negative integer.")

    return Config(
        monitor_dir=monitor_dir,
        dest_base_dir=dest_base_dir,
        dest_subdir_name=dest_subdir_name,
        file_extensions=file_extensions_list,
        check_interval=int(check_interval_min_str) * 60,
        stable_threshold=int(stable_threshold_min_str) * 60,
        categories_file_path=categories_file_path_interactive
    )

def load_config_from_ini(ini_path: Path) -> Optional[Config]:
    parser = configparser.ConfigParser()
    if not ini_path.exists():
        logging.info(f"Configuration file {ini_path} not found.")
        return None

    try:
        parser.read(ini_path)

        # Paths section
        monitor_dir_str = parser.get('Paths', 'monitor_dir', fallback='/tmp')
        monitor_dir = Path(os.path.expanduser(monitor_dir_str)).resolve()
        if not monitor_dir.is_dir():
            logging.error(f"INI Error: monitor_dir '{monitor_dir}' is not a valid directory. Using fallback.")
            monitor_dir = Path("/tmp").resolve() # Fallback if invalid

        dest_base_dir_str = parser.get('Paths', 'dest_base_dir', fallback=str("/opt/stor0"))
        dest_base_dir = Path(os.path.expanduser(dest_base_dir_str)).resolve()
        if not dest_base_dir.is_dir():
            logging.error(f"INI Error: dest_base_dir '{dest_base_dir}' is not a valid directory. Using fallback.")
            dest_base_dir = Path("/opt/stor0").resolve() # Fallback
            dest_base_dir.mkdir(parents=True, exist_ok=True) # Attempt to create fallback

        dest_subdir_name = parser.get('Paths', 'dest_subdir_name', fallback='SavedCachedFiles')

        # Settings section
        extensions_str = parser.get('Settings', 'file_extensions', fallback='.tgz,.tbz,.tlz,.txz')
        file_extensions = [ext.strip() for ext in extensions_str.split(',') if ext.strip().startswith('.')]
        if not file_extensions: # Ensure fallback if parsing results in empty list
            logging.warning(f"No valid file extensions in INI. Using default Slackware packages.")
            file_extensions = DEFAULT_FILE_TYPE_CATEGORIES.get("Slackware Packages", [".tgz",".tbz",".tlz",".txz"])

        check_interval_minutes = parser.getint('Settings', 'check_interval_minutes', fallback=5)
        stable_threshold_minutes = parser.getint('Settings', 'stable_threshold_minutes', fallback=2)
        if check_interval_minutes <= 0: check_interval_minutes = 5
        if stable_threshold_minutes < 0: stable_threshold_minutes = 2

        # Presets section for categories_file
        raw_categories_file = parser.get('Presets', 'categories_file', fallback=DEFAULT_CATEGORIES_FILENAME)
        categories_file_p = Path(raw_categories_file)
        if not categories_file_p.is_absolute():
            categories_file_path = (CONFIG_SCRIPT_DIR / categories_file_p).resolve()
        else:
            categories_file_path = categories_file_p.resolve()

        return Config(
            monitor_dir=monitor_dir,
            dest_base_dir=dest_base_dir,
            dest_subdir_name=dest_subdir_name,
            file_extensions=file_extensions,
            check_interval=check_interval_minutes * 60,
            stable_threshold=stable_threshold_minutes * 60,
            categories_file_path=categories_file_path
        )
    except Exception as e:
        logging.error(f"Error parsing configuration from {ini_path}: {e}", exc_info=True)
        return None

def save_config_to_ini(config: Config, ini_path: Path):
    parser = configparser.ConfigParser()
    parser['Paths'] = {
        'monitor_dir': str(config.monitor_dir),
        'dest_base_dir': str(config.dest_base_dir),
        'dest_subdir_name': config.dest_subdir_name
    }
    parser['Settings'] = {
        'file_extensions': ','.join(config.file_extensions),
        'check_interval_minutes': str(config.check_interval // 60),
        'stable_threshold_minutes': str(config.stable_threshold // 60)
    }

    # Store relative path for categories_file if it's within CONFIG_SCRIPT_DIR, else absolute
    try:
        relative_categories_path = config.categories_file_path.relative_to(CONFIG_SCRIPT_DIR)
        parser['Presets'] = {'categories_file': str(relative_categories_path)}
    except ValueError: # Not relative (e.g. different drive or not a subpath), store absolute
        parser['Presets'] = {'categories_file': str(config.categories_file_path)}

    try:
        with ini_path.open('w', encoding='utf-8') as configfile:
            parser.write(configfile)
        logging.info(f"Configuration saved to {ini_path}")
    except IOError as e:
        logging.error(f"Could not save configuration to {ini_path}: {e}")

def get_config(auto: bool = False, config_ini_path: Path = DEFAULT_CONFIG_INI_PATH) -> Config:
    """
    Main function to get configuration.
    Prioritizes INI file, then interactive, then defaults for auto mode.
    Ensures FILE_TYPE_CATEGORIES is loaded based on the determined categories_file_path.
    """
    global FILE_TYPE_CATEGORIES # Allow modification of the global

    loaded_config_from_ini = load_config_from_ini(config_ini_path)
    final_config: Optional[Config] = None

    if loaded_config_from_ini:
        if auto:
            logging.info(f"Using configuration from {config_ini_path}")
            final_config = loaded_config_from_ini
        else: # Interactive mode, but INI exists
            if questionary and questionary.confirm(f"Configuration found in {config_ini_path}. Use these settings?", default=True).ask():
                final_config = loaded_config_from_ini
            else:
                logging.info("Overriding INI configuration with interactive setup.")
                # Pass INI config as defaults for interactive session
                final_config = get_config_interactively(current_config=loaded_config_from_ini)
                if questionary and questionary.confirm(f"Save this new configuration to {config_ini_path}?", default=True).ask():
                    save_config_to_ini(final_config, config_ini_path)
    else: # No INI found or error loading it
        if auto:
            logging.info("No valid INI found, and --auto specified. Using hardcoded defaults.")
            default_cat_path = CONFIG_SCRIPT_DIR / DEFAULT_CATEGORIES_FILENAME
            final_config = Config(
                monitor_dir=Path("/tmp").resolve(),
                dest_base_dir=Path("/opt/stor0/").resolve(),
                dest_subdir_name="SavedCachedFiles",
                file_extensions=DEFAULT_FILE_TYPE_CATEGORIES.get("Slackware Packages", [".tgz",".tbz",".tlz",".txz"]),
                check_interval=5 * 60,
                stable_threshold=2 * 60,
                categories_file_path=default_cat_path
            )
            # Ensure default dest_base_dir exists if using hardcoded defaults in auto mode
            final_config.dest_base_dir.mkdir(parents=True, exist_ok=True)
        else: # Interactive setup because no INI or user chose not to use it
            logging.info(f"Starting interactive configuration (config.ini not found or error loading).")
            final_config = get_config_interactively(current_config=None) # No base from INI
            if questionary and questionary.confirm(f"Save this new configuration to {config_ini_path}?", default=True).ask():
                save_config_to_ini(final_config, config_ini_path)

    # After final_config is determined, load its specified categories file
    # This ensures FILE_TYPE_CATEGORIES is correctly populated for the rest of the application
    if final_config:
        FILE_TYPE_CATEGORIES = load_file_type_categories_from_file(final_config.categories_file_path)
    else:
        # This case should ideally not be reached if get_config_interactively or defaults provide a config
        logging.error("Failed to determine a valid configuration. Using emergency defaults for categories.")
        emergency_cat_path = CONFIG_SCRIPT_DIR / DEFAULT_CATEGORIES_FILENAME
        FILE_TYPE_CATEGORIES = load_file_type_categories_from_file(emergency_cat_path)
        # And create an emergency config
        final_config = Config(
        monitor_dir=Path("/tmp").resolve(), dest_base_dir=Path("/opt/stor0").resolve(),
        dest_subdir_name="EmergencySaved", file_extensions=[".tgz"],
        check_interval=300, stable_threshold=120, categories_file_path=emergency_cat_path
        )
        final_config.dest_base_dir.mkdir(parents=True, exist_ok=True)


    # Ensure the Config object has the categories_file_path properly set before returning
    # This should be handled by the Config object creation paths above.
    return final_config

# It's good practice to initialize logging for standalone testing of this module
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Example of how to use:
    # To test interactive mode (will prompt to save to config.ini):
    # my_config = get_config(auto=False)
    # logging.info(f"Final Config obtained: {my_config}")

    # To test auto mode (will use config.ini if present, else defaults):
    my_config_auto = get_config(auto=True)
    logging.info(f"Final Auto Config obtained: {my_config_auto}")
    logging.info(f"Loaded file type categories: {FILE_TYPE_CATEGORIES}")

