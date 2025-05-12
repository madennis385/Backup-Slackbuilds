# test_file_monitor.py

import time
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from file_monitor import FileMonitor


@pytest.fixture
def temp_dirs():
    with TemporaryDirectory() as tmpdir:
        monitor_dir = Path(tmpdir)
        dest_dir_name = "processed"
        dest_dir = monitor_dir / dest_dir_name
        yield {
            "monitor_dir": monitor_dir,
            "dest_dir_name": dest_dir_name,
            "dest_dir": dest_dir
        }

def create_dummy_file(path: Path, size: int = 100):
    with open(path, "wb") as f:
        f.write(b"x" * size)
    return path

def test_file_monitor_detects_and_copies_stable_file(temp_dirs):
    # Setup
    monitor_dir = temp_dirs["monitor_dir"]
    dest_subdir_name = temp_dirs["dest_dir_name"]
    file_path = monitor_dir / "example.tgz"

    monitor = FileMonitor(
        monitor_dir=monitor_dir,
        file_extension=".tgz",
        dest_subdir_name=dest_subdir_name,
        check_interval=0.1,  # Fast for tests
        stable_threshold=2
    )

    # Simulate: Add file to be monitored
    create_dummy_file(file_path, 100)

    # Manually simulate scanning loop twice with no size change
    current_files = {file_path}
    monitor.handle_new_files(current_files)
    monitor.handle_existing_files(current_files)
    time.sleep(0.1)
    monitor.handle_existing_files(current_files)

    # Assertions
    copied_file = monitor.dest_dir / file_path.name
    assert copied_file.exists()
    assert copied_file.read_bytes() == file_path.read_bytes()
    assert file_path not in monitor.monitored_files

def test_file_monitor_skips_unreadable_file(temp_dirs):
    monitor_dir = temp_dirs["monitor_dir"]
    dest_subdir_name = temp_dirs["dest_dir_name"]
    invalid_path = monitor_dir / "bad.tgz"

    monitor = FileMonitor(
        monitor_dir=monitor_dir,
        file_extension=".tgz",
        dest_subdir_name=dest_subdir_name,
        check_interval=0.1,
        stable_threshold=2
    )

    # Create and remove the file immediately
    create_dummy_file(invalid_path)
    invalid_path.unlink()

    # Run detection
    monitor.handle_new_files({invalid_path})
    assert invalid_path not in monitor.monitored_files
