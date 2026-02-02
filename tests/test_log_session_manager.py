"""Test script for unified log session manager.

This script tests the LogSessionManager functionality to ensure:
1. Session directories are created with timestamps
2. Files are saved to the correct session directory
3. Session info is correctly tracked
"""

import sys
from pathlib import Path
import tempfile
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.log_session_manager import (
    start_log_session,
    get_current_session,
    end_log_session,
    LogSessionManager
)


def test_basic_session():
    """Test basic session creation and file saving."""
    print("Test 1: Basic Session Creation")
    print("-" * 60)

    # Use temp directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Start session
        session = start_log_session(session_name="test", base_dir=temp_dir)

        print(f"✓ Session created: {session.session_name}")
        print(f"  Session dir: {session.get_session_dir()}")

        # Verify directory was created
        assert session.get_session_dir().exists()
        print(f"✓ Session directory exists")

        # Save a text file
        text_path = session.save_text_file("test.txt", "Hello World!")
        assert text_path.exists()
        assert text_path.read_text() == "Hello World!"
        print(f"✓ Text file saved: {text_path}")

        # Save a JSON file
        json_data = {"key": "value", "number": 42}
        json_path = session.save_json_file("test.json", json_data)
        assert json_path.exists()
        print(f"✓ JSON file saved: {json_path}")

        # Get session info
        info = session.get_session_info()
        assert info["total_files"] == 2
        print(f"✓ Session tracked {info['total_files']} files")

        print()


def test_subdirectories():
    """Test saving files to subdirectories."""
    print("Test 2: Subdirectory Support")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        session = LogSessionManager(session_name="subdir_test", base_dir=temp_dir)

        # Save to subdirectory
        file_path = session.save_text_file("data.txt", "test", subdir="reports")

        # Verify subdirectory was created
        assert file_path.parent.name == "reports"
        assert file_path.exists()
        print(f"✓ File saved to subdirectory: {file_path}")

        # Save another file to different subdirectory
        file_path2 = session.save_json_file("config.json", {"a": 1}, subdir="configs")
        assert file_path2.parent.name == "configs"
        print(f"✓ File saved to different subdirectory: {file_path2}")

        # Verify both are tracked
        info = session.get_session_info()
        assert info["total_files"] == 2
        print(f"✓ Both files tracked: {info['created_files']}")

        print()


def test_global_session():
    """Test global session management."""
    print("Test 3: Global Session Management")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Start global session
        session1 = start_log_session(session_name="global", base_dir=temp_dir)
        print(f"✓ Global session started: {session1.session_name}")

        # Get current session
        session2 = get_current_session()
        assert session2 is not None
        assert session2.session_name == session1.session_name
        print(f"✓ Retrieved current session: {session2.session_name}")

        # End session
        info = end_log_session()
        assert info is not None
        assert info["session_name"] == session1.session_name
        print(f"✓ Session ended, returned info: {info['session_name']}")

        # Verify no active session
        session3 = get_current_session()
        assert session3 is None
        print(f"✓ No active session after end")

        print()


def test_session_name_format():
    """Test session name formatting."""
    print("Test 4: Session Name Format")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Without custom name
        session1 = LogSessionManager(base_dir=temp_dir)
        print(f"✓ Auto name: {session1.session_name}")
        assert len(session1.session_name) == 15  # YYYYMMDD_HHMMSS

        # With custom name
        session2 = LogSessionManager(session_name="my_test", base_dir=temp_dir)
        print(f"✓ Custom name: {session2.session_name}")
        assert session2.session_name.endswith("_my_test")
        assert len(session2.session_name) == 15 + 8  # timestamp_my_test

        print()


def test_multiple_files():
    """Test tracking multiple files."""
    print("Test 5: Multiple File Tracking")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        session = LogSessionManager(session_name="multi", base_dir=temp_dir)

        # Save multiple files
        files = []
        for i in range(5):
            path = session.save_text_file(f"file_{i}.txt", f"Content {i}")
            files.append(path)

        print(f"✓ Saved {len(files)} text files")

        # Save multiple JSON files
        for i in range(3):
            path = session.save_json_file(f"data_{i}.json", {"id": i})
            files.append(path)

        print(f"✓ Saved 3 JSON files")

        # Verify all tracked
        created = session.get_created_files()
        assert len(created) == 8
        print(f"✓ All {len(created)} files tracked")

        # Verify all exist
        for file_path in files:
            assert file_path.exists()
        print(f"✓ All files exist on disk")

        print()


def run_all_tests():
    """Run all tests."""
    print()
    print("=" * 60)
    print("UNIFIED LOG SESSION MANAGER TESTS")
    print("=" * 60)
    print()

    try:
        test_basic_session()
        test_subdirectories()
        test_global_session()
        test_session_name_format()
        test_multiple_files()

        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        return 0

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        print()
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ ERROR: {e}")
        print("=" * 60)
        print()
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
