"""Log session manager for unified log organization.

This module provides a centralized way to manage log files across all modules,
ensuring all outputs (txt, json, etc.) are saved in a single session directory.
"""

import time
from pathlib import Path
from datetime import datetime
from typing import Optional


class LogSessionManager:
    """Manages a single log session with a dedicated directory.

    Each session creates a unique directory under logs/log/{timestamp}/
    where all related files (txt, json, etc.) are saved.
    """

    def __init__(self, session_name: Optional[str] = None, base_dir: str = "logs/log"):
        """Initialize log session manager.

        Args:
            session_name: Optional custom session name (default: timestamp)
            base_dir: Base directory for all logs (default: logs/log)
        """
        self.base_dir = Path(base_dir)
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create session directory name
        if session_name:
            self.session_name = f"{self.session_timestamp}_{session_name}"
        else:
            self.session_name = self.session_timestamp

        # Create session directory
        self.session_dir = self.base_dir / self.session_name
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Track created files
        self._created_files = []

    def get_session_dir(self) -> Path:
        """Get the session directory path.

        Returns:
            Path to session directory
        """
        return self.session_dir

    def get_file_path(self, filename: str, subdir: Optional[str] = None) -> Path:
        """Get a file path within the session directory.

        Args:
            filename: Name of the file
            subdir: Optional subdirectory within session dir

        Returns:
            Full path to the file
        """
        if subdir:
            target_dir = self.session_dir / subdir
            target_dir.mkdir(parents=True, exist_ok=True)
            file_path = target_dir / filename
        else:
            file_path = self.session_dir / filename

        return file_path

    def save_text_file(self, filename: str, content: str, subdir: Optional[str] = None) -> Path:
        """Save a text file in the session directory.

        Args:
            filename: Name of the file
            content: Text content to save
            subdir: Optional subdirectory

        Returns:
            Path to saved file
        """
        file_path = self.get_file_path(filename, subdir)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        self._created_files.append(str(file_path))
        return file_path

    def save_json_file(self, filename: str, data: dict, subdir: Optional[str] = None) -> Path:
        """Save a JSON file in the session directory.

        Args:
            filename: Name of the file
            data: Dictionary to save as JSON
            subdir: Optional subdirectory

        Returns:
            Path to saved file
        """
        import json

        file_path = self.get_file_path(filename, subdir)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        self._created_files.append(str(file_path))
        return file_path

    def get_created_files(self) -> list:
        """Get list of all files created in this session.

        Returns:
            List of file paths
        """
        return self._created_files.copy()

    def get_session_info(self) -> dict:
        """Get session information.

        Returns:
            Dict with session metadata
        """
        return {
            "session_name": self.session_name,
            "session_dir": str(self.session_dir),
            "timestamp": self.session_timestamp,
            "created_files": self._created_files,
            "total_files": len(self._created_files)
        }


# Global session manager (singleton pattern)
_global_session: Optional[LogSessionManager] = None


def get_current_session() -> Optional[LogSessionManager]:
    """Get the current global log session.

    Returns:
        Current LogSessionManager instance, or None if not initialized
    """
    return _global_session


def start_log_session(session_name: Optional[str] = None, base_dir: str = "logs/log") -> LogSessionManager:
    """Start a new log session (or return existing one).

    Args:
        session_name: Optional custom session name
        base_dir: Base directory for all logs

    Returns:
        LogSessionManager instance
    """
    global _global_session

    if _global_session is None:
        _global_session = LogSessionManager(session_name=session_name, base_dir=base_dir)

    return _global_session


def end_log_session() -> Optional[dict]:
    """End the current log session and return summary.

    Returns:
        Session info dict, or None if no session was active
    """
    global _global_session

    if _global_session is None:
        return None

    session_info = _global_session.get_session_info()
    _global_session = None

    return session_info


def get_session_file_path(filename: str, subdir: Optional[str] = None) -> Path:
    """Get a file path within the current session directory.

    If no session is active, creates one automatically.

    Args:
        filename: Name of the file
        subdir: Optional subdirectory

    Returns:
        Full path to the file
    """
    session = get_current_session()
    if session is None:
        session = start_log_session()

    return session.get_file_path(filename, subdir)


def save_session_text_file(filename: str, content: str, subdir: Optional[str] = None) -> Path:
    """Save a text file in the current session directory.

    If no session is active, creates one automatically.

    Args:
        filename: Name of the file
        content: Text content to save
        subdir: Optional subdirectory

    Returns:
        Path to saved file
    """
    session = get_current_session()
    if session is None:
        session = start_log_session()

    return session.save_text_file(filename, content, subdir)


def save_session_json_file(filename: str, data: dict, subdir: Optional[str] = None) -> Path:
    """Save a JSON file in the current session directory.

    If no session is active, creates one automatically.

    Args:
        filename: Name of the file
        data: Dictionary to save as JSON
        subdir: Optional subdirectory

    Returns:
        Path to saved file
    """
    session = get_current_session()
    if session is None:
        session = start_log_session()

    return session.save_json_file(filename, data, subdir)