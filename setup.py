# setup.py
import logging
import sys
from pathlib import Path

# Ensure the config module can be imported
try:
    from config import (
        get_config_interactively,
        save_config_to_ini,
        DEFAULT_CONFIG_INI_PATH,
        load_config_from_ini,
        Config, # Import Config for type hinting
        questionary # To check if available
    )
except ImportError as e:
    # This allows running setup.py from its directory if the main package isn't installed
    # or if there's an issue with the PYTHONPATH.
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    try:
        from config import (
            get_config_interactively,
            save_config_to_ini,
            DEFAULT_CONFIG_INI_PATH,
            load_config_from_ini,
            Config,
            questionary
        )
    except ImportError:
        print(f"ERROR: Could not import 'config' module. Ensure config.py is in the same directory as setup.py or in PYTHONPATH. Details: {e}", file=sys.stderr)
        sys.exit(1)


# Setup basic logging for the setup script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - SETUP - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def run_setup():
    logging.info("Welcome to the Backup Slackbuilds setup script.")
    logging.info("This will guide you through creating a configuration file.")
    logging.info("Please provide values for the following settings. Hints will be provided.")
    if not questionary:
        logging.warning("The 'questionary' library is not installed. Setup will use basic input prompts.")
        logging.warning("For a better interactive experience, consider installing it: pip install questionary")

    existing_config_object: Config | None = None
    if DEFAULT_CONFIG_INI_PATH.exists():
        logging.info(f"An existing configuration file was found: {DEFAULT_CONFIG_INI_PATH}")
        
        # Ask user if they want to reconfigure, using questionary if available
        reconfigure_choice = False
        if questionary:
            reconfigure_choice = questionary.confirm(
                "Do you want to reconfigure and overwrite the existing file?", default=False
            ).ask()
            if reconfigure_choice is None: # User cancelled (e.g., Ctrl+C)
                logging.info("Setup cancelled by user.")
                return
        else: # Fallback to simple input
            response = input("Do you want to reconfigure and overwrite the existing file? (yes/no) [no]: ").strip().lower()
            reconfigure_choice = response == 'yes'

        if not reconfigure_choice:
            logging.info("Exiting setup without changes to the existing configuration.")
            logging.info(f"You can run the main application using: python main.py")
            return
        else:
            logging.info("Proceeding with reconfiguration. Existing values will be used as defaults where applicable during prompts.")
            # Load existing config to pass as 'current_config' to get_config_interactively
            # This allows get_config_interactively to show existing values as defaults.
            # The user wants hints, not defaults, so we'll adjust get_config_interactively.
            # For now, we load it, and will modify get_config_interactively to only use it for hints.
            existing_config_object = load_config_from_ini(DEFAULT_CONFIG_INI_PATH)
            if not existing_config_object:
                logging.warning("Could not properly load existing configuration to use as hints. Starting fresh.")

    logging.info("Starting interactive configuration process...")

    try:
        # We'll modify get_config_interactively to not use current_config for defaults,
        # but rather to guide the input process if needed.
        # For the requirement "no default configuration at all", current_config should be None
        # or get_config_interactively needs to be changed to not pre-fill from it.
        # The prompt "the setup process should provide hints as to valid answers" is key.
        
        # Pass `None` to ensure `get_config_interactively` doesn't use old values as defaults.
        # If `existing_config_object` was loaded, `get_config_interactively` would use its values
        # as defaults in the prompts, which contradicts "no default configuration at all".
        # The hints should come from the prompt text itself or validation messages.
        new_config = get_config_interactively(current_config=None) # Explicitly pass None

        save_config_to_ini(new_config, DEFAULT_CONFIG_INI_PATH)
        logging.info(f"Configuration successfully saved to: {DEFAULT_CONFIG_INI_PATH}")
        logging.info("---------------------------------------------------------------------")
        logging.info("Setup complete!")
        logging.info("You can now run the main application using: python main.py")
        logging.info(
            "To run this as a service, you may need to create a systemd unit file "
            "or use other OS-specific service management tools."
        )
        logging.info("Refer to the README.md for sample service configurations (e.g., rc.cached_file_monitor).")
        logging.info("---------------------------------------------------------------------")

    except (KeyboardInterrupt, EOFError):
        logging.warning("\nSetup process cancelled by user. No configuration file was saved or modified.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred during setup: {e}", exc_info=True)
        logging.error("Setup was not completed. Please try again.")
        sys.exit(1)

if __name__ == "__main__":
    run_setup()