# test_file_monitor_run_multiple_files.py

import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from unittest import mock

from file_monitor import FileMonitor


@pytest.fixture
def setup_monitor_env():
    with TemporaryDirectory() as tmpdir:
        monitor_dir = Path(tmpdir)
        dest_subdir_name = "processed"
        dest_dir = monitor_dir / dest_subdir_name
        yield {
            "monitor_dir": monitor_dir,
            "dest_subdir_name": dest_subdir_name,
            "dest_dir": dest_dir
        }

def write_file(path: Path, content: bytes):
    with open(path, "wb") as f:
        f.write(content)


def test_run_with_stable_and_changing_files(setup_monitor_env):
    monitor_dir = setup_monitor_env["monitor_dir"]
    dest_subdir_name = setup_monitor_env["dest_subdir_name"]
    dest_dir = setup_monitor_env["dest_dir"]

    # File 1 will be stable
    stable_file = monitor_dir / "stable.tgz"
    write_file(stable_file, b"x" * 100)

    # File 2 will change size mid-loop
    changing_file = monitor_dir / "changing.tgz"
    write_file(changing_file, b"a" * 50)

    monitor = FileMonitor(
        monitor_dir=monitor_dir,
        file_extension=".tgz",
        dest_subdir_name=dest_subdir_name,
        check_interval=0.1,
        stable_threshold=2
    )

    call_count = {"count": 0}

    def custom_sleep(duration):
        call_count["count"] += 1
        # After 2 checks, change the size of `changing_file`
        if call_count["count"] == 2:
            write_file(changing_file, b"a" * 75)
        if call_count["count"] >= 4:
            raise KeyboardInterrupt()  # Stop monitor after 4 loops

    with mock.patch("time.sleep", side_effect=custom_sleep):
        thread = threading.Thread(target=monitor.run)
        thread.start()
        thread.join(timeout=2)

    # Verify `stable_file` was copied
    stable_dest = dest_dir / stable_file.name
    assert stable_dest.exists()
    assert stable_dest.read_bytes() == stable_file.read_bytes()

    # Verify `changing_file` was NOT copied
    changing_dest = dest_dir / changing_file.name
    assert not changing_dest.exists()
