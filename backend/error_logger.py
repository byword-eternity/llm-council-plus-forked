"""Error logging for LLM Council Plus."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import asyncio
import re

# In-memory buffer for recent errors (for UI display)
_recent_errors: List[Dict[str, Any]] = []
MAX_RECENT_ERRORS = 100
_last_cleanup = None

# Conversation-based log file path cache (keyed by conversation_id)
# Each conversation gets its own log file with timestamp
_conversation_log_paths: Dict[str, Path] = {}

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
    now = datetime.now()  # Use local time

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
                # Parse date from filename: {prefix}_council_{conversation_id}_{date}_{time}.log
                # or legacy: council_2026-01-01.log
                stem = log_file.stem

                # Extract date portion (YYYY-MM-DD)
                # New format: debug_council_{uuid}_2026-01-05_18-30-45 -> extract 2026-01-05
                # Legacy format: council_2026-01-01 or council_2026-01-01_1
                if "_council_" in stem:
                    # New format: prefix_council_{uuid}_{date}_{time}
                    # Find the date part after the last underscore pattern
                    parts = stem.split("_council_")
                    if len(parts) >= 2:
                        # Get everything after "prefix_council_"
                        after_council = parts[1]
                        # Try to find date pattern YYYY-MM-DD
                        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", after_council)
                        if date_match:
                            date_part = date_match.group(1)
                        else:
                            continue
                    else:
                        continue
                else:
                    # Legacy format: council_YYYY-MM-DD
                    date_part = stem.replace("council_", "").split("_")[0]

                file_date = datetime.strptime(date_part, "%Y-%m-%d")

                if file_date < cutoff:
                    try:
                        log_file.unlink()
                    except Exception as e:
                        # Fallback log for cleanup errors
                        _log_to_fallback(f"Failed to delete old log {log_file}: {e}")
            except Exception:
                pass  # Ignore files with bad names

    _last_cleanup = now


def get_log_path(
    conversation_id: Optional[str] = None, level: Optional[str] = None
) -> Path:
    """
    Get the log file path based on settings with conversation-based naming.

    Each conversation creates its own log file with timestamp including seconds.
    Each log level gets its own file prefix:
    - errors_only -> errors_council_{uuid}_2026-01-05_18-30-45.log
    - all -> all_council_{uuid}_2026-01-05_18-30-45.log
    - debug -> debug_council_{uuid}_2026-01-05_18-30-45.log

    Args:
        conversation_id: Optional conversation UUID. If not provided, uses a generic session log.
        level: Log level override (errors_only, all, debug)
    """
    global _conversation_log_paths

    from .settings import get_settings

    settings = get_settings()

    # Determine the level prefix based on settings or override
    log_level = level or settings.logging_level

    # Map log level to filename prefix
    level_prefix_map = {"errors_only": "errors", "all": "all", "debug": "debug"}
    prefix = level_prefix_map.get(log_level, "all")

    # Generate cache key based on conversation_id or use "session" as fallback
    cache_key = f"{prefix}_{conversation_id or 'session'}"

    # Check if we already have a path for this conversation/level combination
    if cache_key in _conversation_log_paths:
        return _conversation_log_paths[cache_key]

    folder = Path(settings.logging_folder)
    folder.mkdir(parents=True, exist_ok=True)

    # Get local timestamp
    local_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Create filename with level prefix, conversation_id (or 'session'), and local timestamp
    # Format: {level}_council_{conversation_id}_{date}_{time}.log
    # Example: debug_council_abc123-def456_2026-01-05_18-30-45.log
    if conversation_id:
        filename = f"{prefix}_council_{conversation_id}_{local_timestamp}.log"
    else:
        filename = f"{prefix}_council_session_{local_timestamp}.log"
    log_path = folder / filename

    # Cache the path for this conversation/level combination
    _conversation_log_paths[cache_key] = log_path

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
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Local time
        with open(FALLBACK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} | {message}\n")
    except Exception:
        pass  # Last resort: silent failure


async def log_model_error(
    conversation_id: Optional[str],
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
        conversation_id: Optional conversation UUID for conversation-based logging
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

    timestamp = datetime.now()  # Local time
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

    # Add conversation_id if provided
    if conversation_id:
        error_entry["conversation_id"] = conversation_id

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
        # Increase raw output limit for detailed debugging
        limit = 2000 if "debug" in settings.logging_level.lower() else 500
        log_line += f"\n    Raw: {raw_response[:limit]}"

    log_line += "\n"

    try:
        log_path = get_log_path(conversation_id=conversation_id)
        # CRITICAL FIX: Use asyncio.to_thread for non-blocking file I/O
        await asyncio.to_thread(_append_to_file, log_path, log_line)
    except Exception as e:
        _log_to_fallback(f"Failed to write log: {e}")


async def log_event(
    conversation_id: Optional[str],
    event_type: str,
    data: Dict[str, Any],
    level: str = "INFO",
) -> None:
    """
    Log a general event (stage complete, search, etc.).

    Only logs if logging_enabled=True and logging_level="all"/"debug"

    Args:
        conversation_id: Optional conversation UUID for conversation-based logging
        event_type: Type of event (e.g., "stage1_complete")
        data: Event data dictionary
        level: Log level (INFO, WARN, ERROR, DEBUG)
    """
    from .settings import get_settings

    settings = get_settings()

    if not settings.logging_enabled:
        return

    # Level filtering
    if settings.logging_level == "errors_only" and level != "ERROR":
        return

    # If level is 'all', we log ERROR and INFO, but skipping DEBUG unless level is explicitly 'debug'
    if settings.logging_level == "all" and level == "DEBUG":
        return

    # If settings.logging_level is 'debug', we log everything (no return)

    timestamp = datetime.now()  # Local time
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

    # Add conversation_id to data if provided
    if conversation_id:
        data = {**data, "conversation_id": conversation_id}

    # Check for special log_content key (multiline content for human readability)
    if "log_content" in data and isinstance(data["log_content"], str):
        # Write multiline content directly for human readability
        log_content = data["log_content"]
        # Create a clean header
        header = f"{timestamp_str} | {level:5} | [{event_type}]"

        # Write header line
        log_lines = [header]
        # Add each line of the log content with proper indentation
        for line in log_content.split("\n"):
            if line.strip():
                log_lines.append(f"  {line}")
            else:
                log_lines.append("")

        log_line = "\n".join(log_lines) + "\n"
    else:
        # Standard format - sanitize and JSON encode
        sanitized = _sanitize_dict(data)
        log_line = (
            f"{timestamp_str} | {level:5} | "
            f"[{event_type}] {json.dumps(sanitized, default=str)}\n"
        )

    try:
        log_path = get_log_path(conversation_id=conversation_id)
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
                # Use local time for modified timestamp
                modified_local = datetime.fromtimestamp(stat.st_mtime)
                files.append(
                    {
                        "name": f.name,
                        "size": stat.st_size,
                        "modified": modified_local.isoformat(),
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
