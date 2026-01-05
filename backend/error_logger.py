"""Error logging for LLM Council Plus."""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import asyncio

# In-memory buffer for recent errors (for UI display)
_recent_errors: List[Dict[str, Any]] = []
MAX_RECENT_ERRORS = 100
_last_cleanup = None

# Session-based log file path cache (keyed by log level)
# Each session (app start) gets a unique timestamp, and each level gets its own file
_session_log_paths: Dict[str, Path] = {}
_session_start_time: Optional[str] = None

# Concurrency locks
_file_lock = asyncio.Lock()
_buffer_lock = asyncio.Lock()

# Track background tasks for error handling
_pending_cleanup_tasks = set()

# Sensitive key patterns (comprehensive)
SANITIZE_KEYS = {
    "api_key",
    "apikey",
    "api-key",
    "api_key",
    "secret",
    "secret_key",
    "secretkey",
    "secret-key",
    "token",
    "access_token",
    "accesstoken",
    "access-token",
    "credential",
    "credentials",
    "auth",
    "authorization",
    "bearer",
    "auth_token",
    "key",
    "private_key",
    "privatekey",
    "private-key",
    "password",
    "passwd",
    "pwd",
    "signature",
    "sign",
}

# Fallback log file for when primary logging fails
FALLBACK_LOG = Path("data/logs/fallback.log")


def _append_to_file(path: Path, line: str) -> None:
    """Helper function for synchronous file append (runs in thread pool)."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def _sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive keys from dictionary."""
    return {
        k: v
        for k, v in data.items()
        if not any(san_key in k.lower() for san_key in SANITIZE_KEYS)
    }


async def cleanup_old_logs(retention_days: int = 7) -> None:
    """Delete log files older than retention_days."""
    global _last_cleanup
    now = datetime.now(timezone.utc)

    # Run cleanup at most once per hour
    if _last_cleanup and (now - _last_cleanup).total_seconds() < 3600:
        return

    from .settings import get_settings

    settings = get_settings()

    folder = Path(settings.logging_folder)
    if not folder.exists():
        return

    cutoff = now - timedelta(days=retention_days)

    # Match all log file patterns: errors_council_*, all_council_*, debug_council_*, council_*
    patterns = [
        "errors_council_*.log",
        "all_council_*.log",
        "debug_council_*.log",
        "council_*.log",
    ]
    for pattern in patterns:
        for log_file in folder.glob(pattern):
            try:
                # Parse date from filename: {prefix}_council_2026-01-01_18-30-45.log
                # or legacy: council_2026-01-01.log
                stem = log_file.stem

                # Extract date portion (YYYY-MM-DD)
                # New format: errors_council_2026-01-05_18-30-45 -> extract 2026-01-05
                # Legacy format: council_2026-01-01 or council_2026-01-01_1
                if "_council_" in stem:
                    # New format: prefix_council_YYYY-MM-DD_HH-MM-SS
                    date_part = stem.split("_council_")[1][:10]  # Get YYYY-MM-DD
                else:
                    # Legacy format: council_YYYY-MM-DD
                    date_part = stem.replace("council_", "").split("_")[0]

                file_date = datetime.strptime(date_part, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )

                if file_date < cutoff:
                    try:
                        log_file.unlink()
                    except Exception as e:
                        # Fallback log for cleanup errors
                        _log_to_fallback(f"Failed to delete old log {log_file}: {e}")
            except Exception:
                pass  # Ignore files with bad names

    _last_cleanup = now


def get_log_path(level: Optional[str] = None) -> Path:
    """
    Get the log file path based on settings with session-based naming.

    Each logging session (app start) creates a new log file with timestamp including seconds.
    Each log level gets its own file prefix:
    - errors_only -> errors_council_2026-01-05_18-30-45.log
    - all -> all_council_2026-01-05_18-30-45.log
    - debug -> debug_council_2026-01-05_18-30-45.log
    """
    global _session_log_paths, _session_start_time

    from .settings import get_settings

    settings = get_settings()

    # Determine the level prefix based on settings or override
    log_level = level or settings.logging_level

    # Map log level to filename prefix
    level_prefix_map = {"errors_only": "errors", "all": "all", "debug": "debug"}
    prefix = level_prefix_map.get(log_level, "all")

    # Initialize session start time if not set (once per app lifetime)
    if _session_start_time is None:
        _session_start_time = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

    # Check if we already have a path for this level in this session
    cache_key = f"{prefix}_{_session_start_time}"
    if cache_key in _session_log_paths:
        return _session_log_paths[cache_key]

    folder = Path(settings.logging_folder)
    folder.mkdir(parents=True, exist_ok=True)

    # Create filename with level prefix and session timestamp
    # Format: {level}_council_{date}_{time}.log
    # Example: errors_council_2026-01-05_18-30-45.log
    filename = f"{prefix}_council_{_session_start_time}.log"
    log_path = folder / filename

    # Cache the path for this session/level combination
    _session_log_paths[cache_key] = log_path

    # Trigger cleanup opportunistically (with error tracking)
    try:
        task = asyncio.create_task(_safe_cleanup_old_logs())
        if task:
            _pending_cleanup_tasks.add(task)
            task.add_done_callback(_pending_cleanup_tasks.discard)
    except RuntimeError:
        # No event loop running (sync context), skip cleanup
        pass

    return log_path


async def _safe_cleanup_old_logs() -> None:
    """Wrapper for cleanup with error handling."""
    try:
        await cleanup_old_logs()
    except Exception as e:
        _log_to_fallback(f"Cleanup failed: {e}")


def _log_to_fallback(message: str) -> None:
    """Emergency logging when primary logging fails."""
    try:
        FALLBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with open(FALLBACK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} | {message}\n")
    except Exception:
        pass  # Last resort: silent failure


async def log_model_error(
    model: str,
    provider: str,
    error_type: str,
    status_code: Optional[int] = None,
    message: str = "",
    raw_response: Optional[str] = None,
) -> None:
    """
    Log a model error to file and memory buffer.

    Args:
        model: Model ID that failed
        provider: Provider name (e.g., "NanoGPT", "OpenRouter")
        error_type: Categorized error type
        status_code: HTTP status code if applicable
        message: Human-readable error message
        raw_response: Raw response from provider (for debugging)
    """
    from .settings import get_settings

    settings = get_settings()

    if not settings.logging_enabled:
        return

    timestamp = datetime.now(timezone.utc)
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

    error_entry = {
        "timestamp": timestamp.isoformat(),
        "level": "ERROR",
        "model": model,
        "provider": provider,
        "error_type": error_type,
        "status_code": status_code,
        "message": message,
    }

    # Add to recent errors buffer (for UI) - with lock
    async with _buffer_lock:
        _recent_errors.insert(0, error_entry)
        if len(_recent_errors) > MAX_RECENT_ERRORS:
            _recent_errors.pop()

    # Write to file - with lock
    # Format: TIMESTAMP | LEVEL | [PROVIDER] [MODEL] (HTTP STATUS) ERROR_TYPE: MESSAGE
    status_str = f"(HTTP {status_code}) " if status_code else ""
    log_line = (
        f"{timestamp_str} | ERROR | "
        f"[{provider}] [{model}] {status_str}{error_type.upper()}: {message}"
    )

    # Always include raw response for errors (helpful for debugging)
    if raw_response:
        log_line += f"\n    Raw: {raw_response[:500]}"

    log_line += "\n"

    try:
        log_path = get_log_path()
        # CRITICAL FIX: Use asyncio.to_thread for non-blocking file I/O
        await asyncio.to_thread(_append_to_file, log_path, log_line)
    except Exception as e:
        _log_to_fallback(f"Failed to write log: {e}")


async def log_event(event_type: str, data: Dict[str, Any], level: str = "INFO") -> None:
    """
    Log a general event (stage complete, search, etc.).

    Only logs if logging_enabled=True and logging_level="all"/"debug"
    """
    from .settings import get_settings

    settings = get_settings()

    if not settings.logging_enabled:
        return

    # Level filtering
    if settings.logging_level == "errors_only" and level != "ERROR":
        return

    # If level is 'all', we log ERROR and INFO, but skipping DEBUG unless level is explicitly 'debug'
    # Actually, 'all' usually implies everything, but typically excludes verbose DEBUG.
    # Let's align with plan:
    # errors_only -> ERROR
    # all -> ERROR, INFO, WARN (everything except DEBUG)
    # debug -> ERROR, INFO, WARN, DEBUG

    if settings.logging_level == "all" and level == "DEBUG":
        return

    # If settings.logging_level is 'debug', we log everything (no return)

    timestamp = datetime.now(timezone.utc)
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

    # Sanitize data - remove any sensitive keys
    sanitized = _sanitize_dict(data)

    log_line = (
        f"{timestamp_str} | {level:5} | "
        f"[{event_type}] {json.dumps(sanitized, default=str)}\n"
    )

    try:
        log_path = get_log_path()
        # CRITICAL FIX: Use asyncio.to_thread for non-blocking file I/O
        await asyncio.to_thread(_append_to_file, log_path, log_line)
    except Exception as e:
        _log_to_fallback(f"Failed to write log: {e}")


def get_recent_errors(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent errors from memory buffer for UI display."""
    return _recent_errors[:limit]


def get_log_files() -> List[Dict[str, Any]]:
    """Get list of log files with metadata."""
    from .settings import get_settings

    settings = get_settings()

    folder = Path(settings.logging_folder)
    if not folder.exists():
        return []

    files = []
    # Match all log file patterns: errors_council_*, all_council_*, debug_council_*, council_*
    patterns = [
        "errors_council_*.log",
        "all_council_*.log",
        "debug_council_*.log",
        "council_*.log",
    ]
    seen_files = set()  # Avoid duplicates

    for pattern in patterns:
        for f in folder.glob(pattern):
            if f.name in seen_files:
                continue
            seen_files.add(f.name)
            try:
                stat = f.stat()
                files.append(
                    {
                        "name": f.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ).isoformat(),
                    }
                )
            except Exception:
                pass  # Skip files that can't be read

    return sorted(files, key=lambda x: x["modified"], reverse=True)


def read_log_file(filename: str, lines: int = 100) -> str:
    """Read last N lines from a log file."""
    from .settings import get_settings

    settings = get_settings()

    folder = Path(settings.logging_folder)
    filepath = folder / filename

    # Security: prevent path traversal
    if ".." in filename or not filepath.is_relative_to(folder):
        return "Invalid filename"

    if not filepath.exists():
        return "File not found"

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])
    except Exception as e:
        return f"Error reading file: {e}"
