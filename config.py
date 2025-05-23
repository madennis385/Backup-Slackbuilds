# config.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional
import configparser # For INI file handling
import os # For expanding user paths like ~
import logging
import sys # For sys.exit in case of critical errors

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
    try:
        with filepath.open("w", encoding="utf-8") as f:
            f.write("# File Type Categories Configuration\n")
            f.write("# Format: Category Name,.ext1,.ext2,...\n")
            f.write("# Lines starting with # are comments.\n")
            f.write("# Example: My Custom Files,.dat,.bak\n")
            for name, exts in categories.items():
                f.write(f"{name},{','.join(exts)}\n")
        logging.info(f"Created/Updated file type categories configuration at: {filepath}")
    except IOError as e:
        logging.error(f"Could not write categories file to {filepath}: {e}")


def load_file_type_categories_from_file(filepath: Path) -> Dict[str, List[str]]:
    global FILE_TYPE_CATEGORIES
    loaded_categories: Dict[str, List[str]] = {}
    created_default = False
    if not filepath.exists():
        logging.info(f"Categories file not found at {filepath}. Creating it with default categories.")
        logging.info(f"You can edit this file ({filepath}) later to customize categories and extensions.")
        save_categories_to_file(filepath, DEFAULT_FILE_TYPE_CATEGORIES)
        created_default = True
        loaded_categories = DEFAULT_FILE_TYPE_CATEGORIES.copy()

    if filepath.exists() and not created_default:
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
                         logging.warning(f"Duplicate category name '{category_name}' on line {line_num} in {filepath}. Overwriting with later definition.")
                    loaded_categories[category_name] = extensions
            if not loaded_categories and not created_default:
                 logging.warning(f"No valid categories loaded from {filepath}. Check its format.")
        except IOError as e:
            logging.error(f"Could not read categories file {filepath}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error parsing categories file {filepath}: {e}")

    if not loaded_categories:
        logging.warning(f"Using internal default file type categories as a fallback because {filepath} was empty or loading failed.")
        FILE_TYPE_CATEGORIES = DEFAULT_FILE_TYPE_CATEGORIES.copy()
        return FILE_TYPE_CATEGORIES

    FILE_TYPE_CATEGORIES = loaded_categories
    return loaded_categories


def get_extensions_interactively(current_config_extensions: Optional[List[str]] = None) -> List[str]:
    global FILE_TYPE_CATEGORIES

    if not FILE_TYPE_CATEGORIES:
        logging.warning("FILE_TYPE_CATEGORIES is not populated. Attempting to load/create now.")
        categories_path = CONFIG_SCRIPT_DIR / DEFAULT_CATEGORIES_FILENAME
        load_file_type_categories_from_file(categories_path)
        if not FILE_TYPE_CATEGORIES:
            logging.error("Failed to load or create any file type categories. Manual text input for extensions will be required if questionary is not used.")

    default_selections_set = set(current_config_extensions or [])
    selected_extensions_set = set()

    if not questionary:
        logging.warning("Optional 'questionary' library not found. Falling back to manual text input for file extensions.")
        while True:
            user_input_str = input(
                "Enter file extensions to watch, comma-separated (e.g., .tgz,.zip,.iso): "
            ).strip()
            if not user_input_str:
                print("Input cannot be empty. Please provide at least one extension.")
                continue
            selected_extensions_list = [
                ext.strip() for ext in user_input_str.split(",") if ext.strip().startswith(".") and len(ext.strip()) > 1
            ]
            if not selected_extensions_list:
                print("No valid extensions entered. Ensure they start with '.' and are not empty (e.g., .txt).")
                continue
            return sorted(list(set(selected_extensions_list)))

    choices = []
    if FILE_TYPE_CATEGORIES:
        for category_name, extensions_in_category in FILE_TYPE_CATEGORIES.items():
            is_category_pre_checked = default_selections_set.issuperset(set(extensions_in_category))
            display_text = f"{category_name} ({', '.join(extensions_in_category)})"
            choices.append(questionary.Choice(
                title=display_text,
                value=category_name,
                checked=is_category_pre_checked
            ))
    else:
        logging.warning("No file type categories are loaded. Category selection will be skipped.")

    if choices:
        logging.info("Select file type categories. Use Spacebar to select/deselect, Enter to confirm.")
        selected_categories = questionary.checkbox(
            "Which categories of files do you want to monitor?",
            choices=choices
        ).ask()

        if selected_categories is None:
            logging.warning("Category selection cancelled.")
            raise EOFError("User cancelled category selection.")

        for cat_name in selected_categories:
            selected_extensions_set.update(FILE_TYPE_CATEGORIES.get(cat_name, []))
    else:
        logging.info("No categories available to select. Proceeding to custom extension input.")

    logging.info("You can also add custom file extensions.")
    while True:
        custom_extensions_str = questionary.text(
            "Add any other comma-separated extensions? (e.g., .dat,.log) (Leave blank to skip):",
            default=""
        ).ask()

        if custom_extensions_str is None:
             raise EOFError("User cancelled custom extension input.")

        custom_extensions_str = custom_extensions_str.strip()
        if not custom_extensions_str:
            break

        custom_list = [
            ext.strip() for ext in custom_extensions_str.split(',')
            if ext.strip().startswith(".") and len(ext.strip()) > 1
        ]

        if not custom_list and custom_extensions_str:
            logging.warning("Invalid format for custom extensions. Ensure they start with '.' (e.g., .log). Please try again or leave blank.")
        else:
            selected_extensions_set.update(custom_list)
            break

    if not selected_extensions_set:
        logging.warning("No file extensions were selected overall.")
        if questionary.confirm("No extensions selected. This means no files will be monitored. Do you want to try configuring extensions again?", default=True).ask():
            return get_extensions_interactively(current_config_extensions)
        else:
            logging.error("Proceeding without any file extensions. The application will not monitor any files.")
            return []

    return sorted(list(selected_extensions_set))


def _get_path_from_input(prompt_message: str, example_hint: str, is_dir: bool = True, ensure_exists: bool = True, default_val: str = "") -> Path:
    if not questionary:
        while True:
            user_input_str = input(f"{prompt_message} (e.g., {example_hint}) [{default_val}]: ").strip()
            path_str_to_resolve = user_input_str or default_val

            if not path_str_to_resolve:
                print("Path cannot be empty if no default is provided or used. Please enter a valid path.")
                continue

            try:
                resolved_path = Path(os.path.expanduser(path_str_to_resolve)).resolve()
            except Exception as e:
                print(f"Error resolving path '{path_str_to_resolve}': {e}. Please enter a valid path format.")
                continue

            if ensure_exists:
                if not resolved_path.exists():
                    print(f"Path '{resolved_path}' does not exist. Please enter an existing path.")
                    continue
                if is_dir and not resolved_path.is_dir():
                    print(f"Path '{resolved_path}' is not a directory. Please enter a directory path.")
                    continue
            return resolved_path
    else:
        while True:
            user_input_str = questionary.path(
                message=prompt_message + f" (Hint: {example_hint})",
                default=default_val,
                validate=lambda text: True if (text.strip() or default_val) else "Path cannot be empty if no default is provided.",
                only_directories=is_dir if ensure_exists else False
            ).ask()

            if user_input_str is None:
                raise EOFError("User cancelled path input.")

            path_str_to_resolve = user_input_str.strip() or default_val
            if not path_str_to_resolve:
                logging.warning("Path input was effectively empty. Please try again.")
                continue

            try:
                resolved_path = Path(os.path.expanduser(path_str_to_resolve)).resolve()
            except Exception as e:
                logging.error(f"Error resolving path '{path_str_to_resolve}': {e}. Please try again.")
                continue

            if ensure_exists:
                if not resolved_path.exists():
                    logging.warning(f"Path '{resolved_path}' does not exist. Please enter an existing path.")
                    continue
                if is_dir and not resolved_path.is_dir():
                    logging.warning(f"Path '{resolved_path}' is not a directory. Please enter a directory path.")
                    continue
            return resolved_path


def get_config_interactively(current_config: Optional[Config] = None) -> Config:
    global FILE_TYPE_CATEGORIES

    monitor_dir = _get_path_from_input(
        prompt_message="Enter the full path to the directory to be monitored",
        example_hint="/var/log/my_app_logs",
        is_dir=True,
        ensure_exists=True
    )
    dest_base_dir = _get_path_from_input(
        prompt_message="Enter the full path to the base directory where backups will be stored",
        example_hint="/mnt/backup_drive/my_cached_files",
        is_dir=True,
        ensure_exists=False
    )

    dest_subdir_name_prompt = "Enter a name for the subdirectory within the base backup directory (e.g., 'daily_cache')"
    if questionary:
        dest_subdir_name = questionary.text(
            dest_subdir_name_prompt,
            validate=lambda text: True if text.strip() else "Subdirectory name cannot be empty."
        ).ask()
        if dest_subdir_name is None: raise EOFError("User cancelled input.")
        dest_subdir_name = dest_subdir_name.strip()
    else:
        while True:
            dest_subdir_name = input(f"{dest_subdir_name_prompt}: ").strip()
            if dest_subdir_name: break
            print("Subdirectory name cannot be empty.")

    default_categories_path_suggestion = str(CONFIG_SCRIPT_DIR / DEFAULT_CATEGORIES_FILENAME)
    categories_file_path_interactive = _get_path_from_input(
        prompt_message=f"Enter path for file type categories configuration",
        example_hint=f"e.g., {DEFAULT_CATEGORIES_FILENAME} in script dir, or /etc/myapp/file_types.conf",
        is_dir=False,
        ensure_exists=False,
        default_val=default_categories_path_suggestion
    )

    FILE_TYPE_CATEGORIES = load_file_type_categories_from_file(categories_file_path_interactive)

    logging.info("\n--- Configure File Extensions ---")
    extensions_from_old_config = current_config.file_extensions if current_config else None
    file_extensions_list = get_extensions_interactively(current_config_extensions=extensions_from_old_config)
    logging.info(f"Selected extensions: {', '.join(file_extensions_list) if file_extensions_list else 'None'}")
    logging.info("--- End of File Extension Configuration ---\n")

    if not file_extensions_list:
        logging.error("No file extensions configured. This is mandatory for the application to function.")
        raise ValueError("Configuration failed: At least one file extension must be specified.")

    time_prompt_hint = " (integer, e.g., 5 for 5 minutes)"
    if questionary:
        check_interval_min_str = questionary.text(
            "Monitoring check interval (in minutes)?" + time_prompt_hint,
            validate=lambda val: (val.isdigit() and int(val) > 0) or "Must be a positive integer."
        ).ask()
        if check_interval_min_str is None: raise EOFError("User cancelled input.")

        stable_threshold_min_str = questionary.text(
            "How long should a file remain unchanged to be considered 'stable' (in minutes)?" + time_prompt_hint,
            validate=lambda val: (val.isdigit() and int(val) >= 0) or "Must be a non-negative integer."
        ).ask()
        if stable_threshold_min_str is None: raise EOFError("User cancelled input.")
    else:
        while True:
            check_interval_min_str = input(f"Monitoring check interval (in minutes)?{time_prompt_hint}: ").strip()
            if check_interval_min_str.isdigit() and int(check_interval_min_str) > 0:
                break
            print("Invalid input. Monitor time must be a positive integer.")
        while True:
            stable_threshold_min_str = input(f"File stable after how many minutes?{time_prompt_hint}: ").strip()
            if stable_threshold_min_str.isdigit() and int(stable_threshold_min_str) >= 0:
                break
            print("Invalid input. Stable threshold must be a non-negative integer.")

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
        logging.debug(f"Configuration file {ini_path} not found.")
        return None

    try:
        parser.read(ini_path)

        def get_mandatory_ini_value(section, key):
            if not parser.has_option(section, key):
                logging.error(f"CRITICAL: Missing mandatory key '{key}' in section '[{section}]' of {ini_path}.")
                raise ValueError(f"Missing mandatory key '{key}' in INI file: section '[{section}]', key '{key}'")
            
            # Correctly get the value using two arguments
            value = parser.get(section, key) 
            
            # Then check if the retrieved value is empty after stripping
            if not value.strip():
                logging.error(f"CRITICAL: Mandatory key '{key}' in section '[{section}]' of {ini_path} is present but empty.")
                raise ValueError(f"Mandatory key '{key}' in section '[{section}]' is empty.")
            return value

        # Paths section
        monitor_dir_str = get_mandatory_ini_value('Paths', 'monitor_dir')
        monitor_dir = Path(os.path.expanduser(monitor_dir_str)).resolve()
        if not monitor_dir.is_dir():
            logging.error(f"INI Error: monitor_dir '{monitor_dir}' from {ini_path} is not a valid directory.")
            raise ValueError(f"Invalid monitor_dir '{monitor_dir}' in INI file.")

        dest_base_dir_str = get_mandatory_ini_value('Paths', 'dest_base_dir')
        dest_base_dir = Path(os.path.expanduser(dest_base_dir_str)).resolve()

        dest_subdir_name = get_mandatory_ini_value('Paths', 'dest_subdir_name')

        # Settings section
        extensions_str = get_mandatory_ini_value('Settings', 'file_extensions')
        file_extensions = [ext.strip() for ext in extensions_str.split(',') if ext.strip().startswith('.') and len(ext.strip()) > 1]
        if not file_extensions:
            logging.error(f"INI Error: No valid 'file_extensions' found in {ini_path}.")
            raise ValueError("No valid file_extensions in INI file.")

        check_interval_minutes_str = get_mandatory_ini_value('Settings', 'check_interval_minutes')
        stable_threshold_minutes_str = get_mandatory_ini_value('Settings', 'stable_threshold_minutes')

        if not (check_interval_minutes_str.isdigit() and int(check_interval_minutes_str) > 0):
            raise ValueError("check_interval_minutes must be a positive integer in INI.")
        if not (stable_threshold_minutes_str.isdigit() and int(stable_threshold_minutes_str) >= 0):
            raise ValueError("stable_threshold_minutes must be a non-negative integer in INI.")

        check_interval_minutes = int(check_interval_minutes_str)
        stable_threshold_minutes = int(stable_threshold_minutes_str)

        # Presets section for categories_file
        raw_categories_file = get_mandatory_ini_value('Presets', 'categories_file')
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
    except ValueError as ve:
        logging.error(f"Configuration error in {ini_path}: {ve}")
        return None # Indicates an error in loading
    except Exception as e: # Catch other potential errors like configparser.Error
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

    try:
        relative_categories_path = config.categories_file_path.relative_to(CONFIG_SCRIPT_DIR)
        parser['Presets'] = {'categories_file': str(relative_categories_path)}
    except ValueError:
        parser['Presets'] = {'categories_file': str(config.categories_file_path)}

    try:
        ini_path.parent.mkdir(parents=True, exist_ok=True)
        with ini_path.open('w', encoding='utf-8') as configfile:
            parser.write(configfile)
        logging.info(f"Configuration saved to {ini_path}")
    except IOError as e:
        logging.error(f"Could not save configuration to {ini_path}: {e}")

def get_config(config_ini_path: Path = DEFAULT_CONFIG_INI_PATH) -> Config:
    global FILE_TYPE_CATEGORIES

    final_config = load_config_from_ini(config_ini_path)

    if not final_config:
        # This message will be logged by main.py if it calls this.
        # Raising an error ensures main.py knows something went wrong.
        raise FileNotFoundError(f"Configuration missing or invalid at {config_ini_path}. Run setup.py.")

    # After final_config is determined (must be from INI), load its specified categories file.
    FILE_TYPE_CATEGORIES = load_file_type_categories_from_file(final_config.categories_file_path)

    return final_config

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    print("This script (config.py) is not intended to be run directly for application configuration anymore.")
    print("Please run 'python setup.py' for interactive configuration.")
    print("Or run 'python main.py' if configuration is already complete.")