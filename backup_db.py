# backup_db.py
import sqlite3
import logging
import shutil
from pathlib import Path
from datetime import datetime

# Determine the directory of the current script
SCRIPT_DIR = Path(__file__).resolve().parent
# Define the database path relative to the script's directory
DB_DISK_PATH = SCRIPT_DIR / "backup_state.sqlite"

class BackupDB:
    def __init__(self):
        # Ensure the directory for the database exists (though SCRIPT_DIR should always exist)
        # This is more for consistency if DB_DISK_PATH were in a subdirectory of SCRIPT_DIR
        DB_DISK_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(":memory:") # Continue using in-memory for operations
        self.init_schema()
        self._loaded = False
        if DB_DISK_PATH.exists():
            self.load_from_disk()
        else:
            logging.info(f"Database file not found at {DB_DISK_PATH}, a new one will be created on save.")


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
            # Connect directly to the on-disk database for loading
            disk_conn = sqlite3.connect(DB_DISK_PATH)
            with disk_conn:
                # Efficiently dump the on-disk database to the in-memory database
                for line in disk_conn.iterdump():
                    # Prevent trying to execute "BEGIN IMMEDIATE;" or "COMMIT;" which can cause issues
                    if 'COMMIT;' not in line and 'BEGIN IMMEDIATE;' not in line:
                        try:
                            self.conn.execute(line)
                        except sqlite3.OperationalError as e:
                            logging.debug(f"Skipping line during load due to operational error (likely harmless): {line} - {e}")
            self.conn.commit() # Commit all loaded data to memory
            disk_conn.close()
            self._loaded = True
            logging.info(f"Loaded backup state from disk: {DB_DISK_PATH}")
        except Exception as e:
            logging.error(f"Failed to load backup DB from disk ({DB_DISK_PATH}): {e}")

    def save_to_disk(self):
        # Save the in-memory database to a temporary file first, then replace the actual DB file
        # This is safer and helps prevent DB corruption if the script is interrupted.
        tmp_path = DB_DISK_PATH.with_suffix(DB_DISK_PATH.suffix + ".tmp")
        try:
            # Connect to the temporary on-disk database
            disk_conn = sqlite3.connect(tmp_path)
            with disk_conn:
                # Dump the in-memory database to the temporary on-disk database
                for line in self.conn.iterdump():
                    disk_conn.execute(line)
            disk_conn.commit() # Commit all data to the temporary file
            disk_conn.close()
            
            # Replace the actual database file with the temporary one
            shutil.move(tmp_path, DB_DISK_PATH)
            logging.info(f"Saved backup state to disk: {DB_DISK_PATH}")
        except Exception as e:
            logging.error(f"Failed to save backup DB to disk ({DB_DISK_PATH}): {e}")
            if tmp_path.exists():
                try:
                    tmp_path.unlink() # Attempt to clean up the temporary file on failure
                except OSError as oe:
                    logging.error(f"Could not remove temporary database file {tmp_path}: {oe}")
        finally:
            # Ensure temporary file is removed if it still exists for some reason (e.g. shutil.move failed before unlink)
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError: # nosemgrep: general-exception-escape
                    pass # If it still can't be removed, log and move on.

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