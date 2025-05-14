# backup_db.py
import sqlite3
import logging
import shutil
from pathlib import Path
from datetime import datetime

DB_DISK_PATH = Path("backup_state.sqlite")

class BackupDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.init_schema()
        self._loaded = False
        if DB_DISK_PATH.exists():
            self.load_from_disk()

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
