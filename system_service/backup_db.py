# backup_db.py
import sqlite3
import logging
import shutil
from pathlib import Path
from datetime import datetime

# Determine the directory where this script (backup_db.py) is located.
APP_SCRIPT_DIR = Path(__file__).resolve().parent
# Define a 'data' subdirectory within the application's installation directory.
DATA_DIR = APP_SCRIPT_DIR / "data"
DB_DISK_PATH = DATA_DIR / "backup_state.sqlite"

class BackupDB:
    def __init__(self):
        # Ensure the data directory exists.
        # The setup script should primarily handle creation and permissions.
        # This is a fallback or for direct script execution.
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Log an error if directory creation fails here, but don't raise
            # as the main script might run into permission issues if not set up.
            logging.error(f"Could not ensure data directory {DATA_DIR} from BackupDB: {e}")


        self.conn = sqlite3.connect(":memory:") # Start with an in-memory DB
        self.init_schema()
        self._loaded = False
        if DB_DISK_PATH.exists():
            # Only attempt to load if the service user can access/read this path.
            # Permissions are handled by the setup script.
            self.load_from_disk()
        else:
            logging.info(f"Backup database {DB_DISK_PATH} not found. Will be created on first save.")


    def init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS backed_up_files (
                path TEXT PRIMARY KEY,
                md5 TEXT NOT NULL,
                backed_up_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def load_from_disk(self):
        try:
            disk_conn = sqlite3.connect(DB_DISK_PATH)
            with disk_conn:
                for row in disk_conn.iterdump():
                    self.conn.execute(row)
            self.conn.commit()
            disk_conn.close()
            self._loaded = True
            logging.info("Loaded backup state from disk.")
        except Exception as e:
            logging.error(f"Failed to load backup DB from disk: {e}")

    def save_to_disk(self):
        try:
            tmp_path = Path("backup_state_tmp.sqlite")
            disk_conn = sqlite3.connect(tmp_path)
            with disk_conn:
                for line in self.conn.iterdump():
                    disk_conn.execute(line)
            disk_conn.commit()
            disk_conn.close()
            shutil.move(tmp_path, DB_DISK_PATH)
            logging.info("Saved backup state to disk.")
        except Exception as e:
            logging.error(f"Failed to save backup DB to disk: {e}")

    def record_backup(self, path: str, md5: str):
        self.conn.execute(
            "REPLACE INTO backed_up_files (path, md5, backed_up_at) VALUES (?, ?, ?)",
            (path, md5, datetime.utcnow().isoformat())
        )
        self.conn.commit()

    def is_already_backed_up(self, path: str, md5: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM backed_up_files WHERE path = ? AND md5 = ?",
            (path, md5)
        )
        return cur.fetchone() is not None
