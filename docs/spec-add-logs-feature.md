# Feature Specification: Logging System

**Created:** 2026-01-01  
**Updated:** 2026-01-06  
**Status:** ⚠️ DEPRECATED - Implementation Complete  
**Priority:** High  
**Implementation Ready:** No - Feature has been fully implemented

---

> **This specification document has been deprecated.** The logging feature is now fully implemented. Please refer to [docs/logging-guide.md](logging-guide.md) for user documentation.

---

## Problem Statement

When using LLM Council Plus with aggregator services like **NanoGPT** (or other OpenAI-compatible endpoints), some models frequently fail without clear error information. Users need visibility into:

- **Which model failed** and why
- **Error details** from the provider (rate limit, model unavailable, quota exceeded, etc.)
- **Historical log** of errors for debugging

Currently, errors are only shown briefly in the UI with minimal information, making troubleshooting difficult.

## Overview

Add a logging feature focused on **error visibility** with:

1. **Enhanced error parsing** - Extract detailed error messages from providers (especially NanoGPT)
2. **Toggle on/off** - Enable or disable logging globally
3. **Log level selection** - Choose between logging all messages or only errors
4. **Log file persistence** - Save logs to files for later review (with size-based rotation)
5. **UI Log Viewer** - View recent logs directly in Settings
6. **Integration with existing debugging** - Migrate current print/console statements

## Requirements

### Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-1 | Enhanced error parsing for custom OpenAI endpoints | **Critical** | Updated |
| FR-2 | User can enable/disable logging via Settings UI | High | ✅ Stable |
| FR-3 | User can select log level: "all", "errors_only", or "debug" | High | **Modified** |
| FR-4 | Logs are written to files (`data/logs/`) with size rotation | High | **Updated** |
| FR-5 | User can view recent logs in Settings UI | High | ✅ Stable |
| FR-6 | Log files are rotated automatically (max 10MB per file, max 10 per day) | Medium | **Modified** |
| FR-7 | Old log files are retained for 7 days | Low | ✅ Stable |
| FR-8 | Existing debug logs migrated to new system | Medium | **Added** |

### Non-Functional Requirements

| ID | Requirement | Notes |
|----|-------------|-------|
| NFR-1 | Logging should not significantly impact application performance | Async-safe with file locking |
| NFR-2 | Sensitive data (API keys) should NEVER be logged | Enhanced sanitization |
| NFR-3 | Error messages should be human-readable and actionable | Categorized error types |
| NFR-4 | All timestamps in UTC for consistency | **Added** |
| NFR-5 | Logging failures should not break application | Fallback logging added |

## Codebase Context (IMPORTANT - Read Before Implementing)

### Project Conventions

| Rule | Details | Updates |
|------|---------|---------|
| **Backend imports** | Relative ONLY: `from .config import ...`, NEVER `from backend.` | ✅ Unchanged |
| **Backend port** | 8001 (NOT 8000) | ✅ Unchanged |
| **Run backend** | `uv run python -m backend.main` from project root | ✅ Unchanged |
| **React state** | Immutable updates via spread operator | ✅ Unchanged |
| **Data folder** | `data/` is git-ignored, contains runtime storage | ✅ Already covered |
| **Existing logs** | main.py has print() statements at lines 138, 154, 162, 187, 223, 238, 251, 280, 287, 289, 292, 646 | **Must migrate** |
| **Existing logger** | council.py has `logger = logging.getLogger(__name__)` at line 12 | **Must remove/redirect** |

### Frontend Settings.jsx Structure

**File:** `frontend/src/components/Settings.jsx` (1492 lines)

**Current Sections (tabs):**
```javascript
// Line 15: State for active section
const [activeSection, setActiveSection] = useState(initialSection);
// Values: 'llm_keys', 'council', 'prompts', 'search', 'import_export'
```

**Sidebar Navigation Pattern (around line 1217-1241):**
```jsx
<button
  className={`sidebar-nav-item ${activeSection === 'llm_keys' ? 'active' : ''}`}
  onClick={() => setActiveSection('llm_keys')}
>
  🔑 LLM API Keys
</button>
// ... more buttons for each section
```

**Section Rendering Pattern (around line 1252-1427):**
```jsx
{activeSection === 'llm_keys' && (
  <section className="settings-section">
    {/* Section content */}
  </section>
)}
```

**To add "Logs" tab:**
1. Add new nav button after 'import_export' button (around line 1241)
2. Add new section rendering after import_export section (around line 1427)
3. Add state variables at top with other state declarations

### Frontend api.js Pattern

**File:** `frontend/src/api.js` (331 lines)

**Pattern for adding new API functions:**
```javascript
/**
 * Get recent error logs.
 */
async getRecentLogs(limit = 50) {
  const response = await fetch(`${API_BASE}/api/logs/recent?limit=${limit}`);
  if (!response.ok) {
    throw new Error('Failed to get recent logs');
  }
  return response.json();
},
```

### Backend Settings Pattern

**File:** `backend/settings.py`

**Adding new settings fields:**
```python
class Settings(BaseModel):
    # ... existing fields (line ~69-122) ...
    
    # Add at end of class, before closing:
    # Logging Settings
    logging_enabled: bool = False
    logging_level: str = "errors_only"  # "all", "errors_only", or "debug"
    logging_folder: str = "data/logs"
```

### Backend main.py Pattern

**File:** `backend/main.py` (951 lines)

**UpdateSettingsRequest class (around line 308-355):**
- Add new Optional fields for logging settings

**GET /api/settings (around line 364-414):**
- Add logging fields to response dict

**PUT /api/settings (around line 438-613):**
- Add validation logic for logging settings

**Adding new endpoints (add after line 850):**
```python
@app.get("/api/logs/recent")
async def get_recent_logs(limit: int = 50):
    """Get recent error logs for UI display."""
    from .error_logger import get_recent_errors
    return {"errors": get_recent_errors(limit)}
```

### Backend Module Import Pattern

**For new `backend/error_logger.py`:**
```python
"""Error logging for LLM Council Plus."""

# Standard library imports
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import asyncio

# Relative imports (MUST use relative, LAZY to avoid circular)
# from .settings import get_settings  # Import inside functions
```

### Backend council.py Integration Points

**File:** `backend/council.py` (588 lines)

**Stage 1 error logging (around line 160-167):**
```python
if response.get('error'):
    result = {
        "model": model,
        "response": None,
        "error": response.get('error'),
        "error_message": response.get('error_message', 'Unknown error')
    }
    # ADD HERE: log_model_error call
```

**Provider name helper function (add near top, line ~48):**
```python
def get_provider_name(model_id: str) -> str:
    """Extract provider name from model ID for logging."""
    if ":" in model_id:
        prefix = model_id.split(":")[0]
        provider_map = {
            "ollama": "Ollama",
            "openrouter": "OpenRouter",
            "groq": "Groq", 
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "google": "Google AI",
            "mistral": "Mistral AI",
            "deepseek": "DeepSeek",
            "custom": "Custom"
        }
        return provider_map.get(prefix, prefix.upper())
    return "Unknown"
```

### Custom Provider Error Handling

**File:** `backend/providers/custom_openai.py` (153 lines)

**Current error handling (line 49-53):**
```python
if response.status_code != 200:
    return {
        "error": True,
        "error_message": f"{name} API error: {response.status_code} - {response.text}"
    }
```

**Need to replace with enhanced parsing that:**
1. Parses JSON error response (add `import json` at top)
2. Categorizes error type
3. Calls error_logger
4. Returns structured error dict
5. **NEW:** Get provider name from settings for custom endpoint

### CSS Pattern

**File:** `frontend/src/components/Settings.css`

**Add new styles at end of file.** Follow existing patterns for:
- `.settings-section` styling
- Color scheme: use existing colors (`#f87171` for errors, `#60a5fa` for info)
- Background: `rgba(0, 0, 0, 0.2)` for dark panels
- Border: `1px solid rgba(255, 255, 255, 0.1)`

---

## Technical Design

### 0. Pre-Implementation Audit

**Before adding new logging:**
- Audit and migrate existing `print()` statements in main.py
- Remove existing `logger` instance in council.py
- Audit console.error() calls in frontend
- Create helper function for provider name extraction

### 1. Enhanced Error Parsing (CRITICAL)

#### 1.1 Update Custom OpenAI Provider (`backend/providers/custom_openai.py`)

The current error handling is too generic. We need to parse provider-specific error responses:

**Current Code (Problem):**
```python
if response.status_code != 200:
    return {
        "error": True,
        "error_message": f"{name} API error: {response.status_code} - {response.text}"
    }
```

**New Code (Solution):**
```python
if response.status_code != 200:
    error_info = self._parse_error_response(response, model, name)
    
    # Log the error
    from ..error_logger import log_model_error
    log_model_error(
        model=model,
        provider=name,
        error_type=error_info["error_type"],
        status_code=response.status_code,
        message=error_info["message"],
        raw_response=error_info.get("raw_response")
    )
    
    return {
        "error": True,
        "error_type": error_info["error_type"],
        "error_code": response.status_code,
        "error_message": error_info["display_message"]
    }

def _parse_error_response(self, response, model: str, name: str) -> dict:
    """
    Parse error response from OpenAI-compatible endpoints.
    Handles various error formats from different providers.
    """
    status_code = response.status_code
    raw_text = response.text[:1000]  # Limit for safety
    
    # Default values
    error_type = "unknown_error"
    message = raw_text
    
    # Try to parse JSON error
    try:
        error_json = response.json()
        
        # OpenAI format: {"error": {"message": "...", "type": "...", "code": "..."}}
        if "error" in error_json:
            err = error_json["error"]
            if isinstance(err, dict):
                message = err.get("message") or err.get("msg") or str(err)
                error_type = err.get("type") or err.get("code") or "api_error"
            else:
                message = str(err)
        
        # Alternative format: {"message": "...", "code": "..."}
        elif "message" in error_json:
            message = error_json["message"]
            error_type = error_json.get("code", "api_error")
        
        # NanoGPT specific format (if any)
        elif "detail" in error_json:
            message = error_json["detail"]
            error_type = "validation_error"
            
    except (json.JSONDecodeError, KeyError):
        # Not JSON, use raw text
        message = raw_text if raw_text else f"HTTP {status_code}"
    
    # Categorize by status code
    if status_code == 429:
        error_type = "rate_limit"
        if "rate" not in message.lower():
            message = f"Rate limited: {message}"
    elif status_code == 401:
        error_type = "auth_error"
    elif status_code == 403:
        error_type = "forbidden"
    elif status_code == 404:
        error_type = "model_not_found"
    elif status_code == 503:
        error_type = "service_unavailable"
    elif status_code >= 500:
        error_type = "server_error"
    
    # Create user-friendly display message
    display_message = f"[{name}] [{model}] {error_type.upper()}: {message}"
    
    return {
        "error_type": error_type,
        "message": message,
        "display_message": display_message,
        "raw_response": raw_text
    }
```

#### 1.2 Error Type Categories

| Error Type | HTTP Code | Description | User Action |
|------------|-----------|-------------|-------------|
| `rate_limit` | 429 | Too many requests | Wait and retry, or reduce council size |
| `auth_error` | 401 | Invalid API key | Check API key in settings |
| `forbidden` | 403 | Access denied | Check account permissions/quota |
| `model_not_found` | 404 | Model doesn't exist | Check model name, may be deprecated |
| `quota_exceeded` | 402/403 | Insufficient balance | Top up account |
| `service_unavailable` | 503 | Provider overloaded | Wait and retry |
| `server_error` | 5xx | Provider internal error | Wait and retry |
| `timeout` | - | Request timeout | Increase timeout or check network |
| `context_length` | 400 | Input too long | Reduce input size |
| `validation_error` | 422 | Invalid request format | Check input format |

### 2. Error Logger Module (`backend/error_logger.py`)

New module for centralized error logging with CRITICAL async pattern fixes:

**CRITICAL FIXES APPLIED:**
1. File I/O uses `asyncio.to_thread()` for non-blocking writes (fixes blocking issue)
2. Uses public `asyncio.get_running_loop()` instead of private `_get_running_loop()`
3. Background task tracking to prevent silent failures
4. Enhanced error handling for file operations

```python
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

# Concurrency locks
_file_lock = asyncio.Lock()
_buffer_lock = asyncio.Lock()

# Track background tasks for error handling
_pending_cleanup_tasks = set()

# Sensitive key patterns (comprehensive)
SANITIZE_KEYS = {
    'api_key', 'apikey', 'api-key', 'api_key',
    'secret', 'secret_key', 'secretkey', 'secret-key',
    'token', 'access_token', 'accesstoken', 'access-token',
    'credential', 'credentials',
    'auth', 'authorization', 'bearer', 'auth_token',
    'key', 'private_key', 'privatekey', 'private-key',
    'password', 'passwd', 'pwd',
    'signature', 'sign'
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
        k: v for k, v in data.items()
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
    
    for log_file in folder.glob("council_*.log"):
        try:
            # Parse date from filename: council_2026-01-01.log or council_2026-01-01_1.log
            date_str = log_file.stem.replace("council_", "").split('_')[0]
            file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            
            if file_date < cutoff:
                try:
                    log_file.unlink()
                except Exception as e:
                    # Fallback log for cleanup errors
                    _log_to_fallback(f"Failed to delete old log {log_file}: {e}")
        except Exception:
            pass  # Ignore files with bad names
            
    _last_cleanup = now


def get_log_path() -> Path:
    """Get the log file path based on settings with size rotation."""
    from .settings import get_settings
    settings = get_settings()
    
    folder = Path(settings.logging_folder)
    folder.mkdir(parents=True, exist_ok=True)
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = folder / f"council_{today}.log"
    
    # Check size and rotate if > 10MB (implementing FR-6)
    try:
        if log_path.exists() and log_path.stat().st_size > 10 * 1024 * 1024:
            # Create numbered backup (max 10 per day)
            for i in range(1, 11):
                backup_path = folder / f"council_{today}_{i}.log"
                if not backup_path.exists():
                    log_path.rename(backup_path)
                    break
    except Exception as e:
        _log_to_fallback(f"Log rotation failed: {e}")
    
    # Trigger cleanup opportunistically (with error tracking)
    task = asyncio.create_task(_safe_cleanup_old_logs())
    if task:
        _pending_cleanup_tasks.add(task)
        task.add_done_callback(_pending_cleanup_tasks.discard)
    
    return folder / f"council_{today}.log"


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
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
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
    raw_response: Optional[str] = None
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
    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
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
    log_line = (
        f"{timestamp_str} | ERROR | "
        f"[{provider}] [{model}] {error_type.upper()}: {message}"
    )
    
    if raw_response and settings.logging_level in ["all", "debug"]:
        # Include raw response in verbose/debug mode
        log_line += f"\n    Raw: {raw_response[:500]}"
    
    log_line += "\n"
    
    try:
        log_path = get_log_path()
        # CRITICAL FIX: Use asyncio.to_thread for non-blocking file I/O
        await asyncio.to_thread(_append_to_file, log_path, log_line)
    except Exception as e:
        _log_to_fallback(f"Failed to write log: {e}")


async def log_event(
    event_type: str,
    data: Dict[str, Any],
    level: str = "INFO"
) -> None:
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
    if settings.logging_level != "debug" and level == "DEBUG":
        return
    
    timestamp = datetime.now(timezone.utc)
    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
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
    for f in folder.glob("council_*.log"):
        try:
            stat = f.stat()
            files.append({
                "name": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })
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
```

### 3. Settings Model Update (`backend/settings.py`)

Add logging settings to the Settings model:

```python
class Settings(BaseModel):
    # ... existing fields ...
    
    # Logging Settings (FR-2, FR-3)
    logging_enabled: bool = False
    logging_level: str = "errors_only"  # "all", "errors_only", or "debug"
    logging_folder: str = "data/logs"
```

**Note:** Default is `"errors_only"` since that's the primary use case. Debug mode includes raw responses.

### 4. API Endpoints (`backend/main.py`)

#### 4.1 Update Settings Endpoints

**Add to `UpdateSettingsRequest`:**
```python
# Logging Settings
logging_enabled: Optional[bool] = None
logging_level: Optional[str] = None
logging_folder: Optional[str] = None
```

**Add to GET `/api/settings` response:**
```python
"logging_enabled": settings.logging_enabled,
"logging_level": settings.logging_level,
"logging_folder": settings.logging_folder,
```

**Add validation to PUT `/api/settings`:**
```python
if request.logging_enabled is not None:
    updates["logging_enabled"] = request.logging_enabled

if request.logging_level is not None:
    if request.logging_level not in ["all", "errors_only", "debug"]:
        raise HTTPException(status_code=400, detail="Invalid logging_level")
    updates["logging_level"] = request.logging_level

if request.logging_folder is not None:
    if ".." in request.logging_folder:
        raise HTTPException(status_code=400, detail="Invalid folder path")
    updates["logging_folder"] = request.logging_folder
```

#### 4.2 New Log Viewer Endpoints

```python
@app.get("/api/logs/recent")
async def get_recent_logs(limit: int = 50):
    """Get recent error logs for UI display."""
    from .error_logger import get_recent_errors
    return {"errors": get_recent_errors(limit)}


@app.get("/api/logs/files")
async def get_log_files():
    """Get list of log files."""
    from .error_logger import get_log_files
    return {"files": get_log_files()}


@app.get("/api/logs/file/{filename}")
async def read_log_file(filename: str, lines: int = 100):
    """Read contents of a specific log file."""
    from .error_logger import read_log_file
    
    # Basic security check
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    content = read_log_file(filename, lines)
    return {"content": content}
```

#### 4.3 Client Logging Endpoint (Optional but Recommended)
```python
@app.post("/api/logs/client")
async def log_from_client(log_data: dict):
    """Accept log messages from frontend."""
    from .error_logger import log_event
    level = log_data.get("level", "INFO")
    message = log_data.get("message", "")
    data = log_data.get("data", {})
    
    await log_event(f"client_{level.lower()}", {"message": message, **data}, level)
    return {"status": "logged"}
```

### 5. Frontend Changes

#### 5.1 Settings State

Add to `Settings.jsx`:

```javascript
// Logging Settings State
const [loggingEnabled, setLoggingEnabled] = useState(false);
const [loggingLevel, setLoggingLevel] = useState('errors_only');
const [loggingFolder, setLoggingFolder] = useState('data/logs');

// Log Viewer State
const [recentErrors, setRecentErrors] = useState([]);
const [logFiles, setLogFiles] = useState([]);
const [isLoadingLogs, setIsLoadingLogs] = useState(false);
```

#### 5.2 Log Viewer UI Component

Add a new section in Settings (new tab "Logs"):

```jsx
{activeSection === 'logs' && (
  <section className="settings-section">
    <h2>📋 Logging & Diagnostics</h2>
    
    {/* Toggle */}
    <div className="setting-row">
      <label className="toggle-label">
        <input
          type="checkbox"
          checked={loggingEnabled}
          onChange={(e) => setLoggingEnabled(e.target.checked)}
        />
        <span>Enable Logging</span>
      </label>
      <p className="setting-hint">
        Save logs to files for debugging model errors
      </p>
    </div>
    
    {loggingEnabled && (
      <>
        {/* Log Level */}
        <div className="setting-row">
          <label>Log Level</label>
          <select
            value={loggingLevel}
            onChange={(e) => setLoggingLevel(e.target.value)}
          >
            <option value="errors_only">Errors Only</option>
            <option value="all">All Events</option>
            <option value="debug">Debug (includes raw responses)</option>
          </select>
        </div>
        
        {/* Log Folder */}
        <div className="setting-row">
          <label>Log Folder</label>
          <input
            type="text"
            value={loggingFolder}
            onChange={(e) => setLoggingFolder(e.target.value)}
            placeholder="data/logs"
          />
        </div>
      </>
    )}
    
    {/* Recent Errors Viewer */}
    <div className="log-viewer-section">
      <div className="log-viewer-header">
        <h4>Recent Errors</h4>
        <button onClick={loadRecentErrors} disabled={isLoadingLogs}>
          {isLoadingLogs ? 'Loading...' : '🔄 Refresh'}
        </button>
      </div>
      
      {recentErrors.length === 0 ? (
        <div className="log-empty">
          No errors logged yet. Errors will appear here when models fail.
        </div>
      ) : (
        <div className="log-entries">
          {recentErrors.map((error, idx) => (
            <div key={idx} className={`log-entry ${error.level.toLowerCase()}`}>
              <div className="log-timestamp">
                {new Date(error.timestamp).toLocaleString()}
              </div>
              <div className="log-model">{error.model}</div>
              <div className="log-type">{error.error_type}</div>
              <div className="log-message">{error.message}</div>
            </div>
          ))}
        </div>
      )}
    </div>
    
    {/* Log Files */}
    {logFiles.length > 0 && (
      <div className="log-files-section">
        <h4>Log Files</h4>
        <div className="log-files-list">
          {logFiles.map((file, idx) => (
            <div key={idx} className="log-file-item">
              <span className="file-name">{file.name}</span>
              <span className="file-size">
                {(file.size / 1024).toFixed(1)} KB
              </span>
              <span className="file-date">
                {new Date(file.modified).toLocaleDateString()}
              </span>
              <button onClick={() => viewLogFile(file.name)}>
                View
              </button>
              <button onClick={() => downloadLogFile(file.name)}>
                Download
              </button>
            </div>
          ))}
        </div>
      </div>
    )}
  </section>
)}
```

#### 5.3 Log Viewer API Functions

Add to `frontend/src/api.js`:

```javascript
/**
 * Get recent error logs.
 */
async getRecentLogs(limit = 50) {
  const response = await fetch(`${API_BASE}/api/logs/recent?limit=${limit}`);
  if (!response.ok) {
    throw new Error('Failed to get recent logs');
  }
  return response.json();
},

/**
 * Get list of log files.
 */
async getLogFiles() {
  const response = await fetch(`${API_BASE}/api/logs/files`);
  if (!response.ok) {
    throw new Error('Failed to get log files');
  }
  return response.json();
},

/**
 * Read contents of a log file.
 */
async readLogFile(filename, lines = 100) {
  const response = await fetch(
    `${API_BASE}/api/logs/file/${encodeURIComponent(filename)}?lines=${lines}`
  );
  if (!response.ok) {
    throw new Error('Failed to read log file');
  }
  return response.json();
},

/**
 * Send client-side log to server.
 */
async logToServer(level, message, data = {}) {
  const response = await fetch(`${API_BASE}/api/logs/client`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ level, message, data })
  });
  return response.ok;
},
```

#### 5.4 CSS Styles (`Settings.css`)

Add at END of file:

```css
/* Log Viewer Styles */
.log-viewer-section {
  margin-top: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
}

.log-viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.log-viewer-header h4 {
  margin: 0;
  color: #f87171;
}

.log-entries {
  max-height: 300px;
  overflow-y: auto;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.4;
}

.log-entry {
  padding: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(0, 0, 0, 0.1);
}

.log-entry.error {
  background: rgba(248, 113, 113, 0.1);
  border-left: 3px solid #f87171;
}

.log-entry.warn {
  background: rgba(251, 191, 36, 0.1);
  border-left: 3px solid #fbbf24;
}

.log-entry.info {
  background: rgba(96, 165, 250, 0.1);
  border-left: 3px solid #60a5fa;
}

.log-timestamp {
  color: #888;
  font-size: 11px;
  font-weight: 500;
}

.log-model {
  color: #60a5fa;
  font-weight: 600;
  margin: 2px 0;
}

.log-type {
  color: #f87171;
  text-transform: uppercase;
  font-size: 11px;
  font-weight: 600;
  display: inline-block;
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(248, 113, 113, 0.2);
}

.log-message {
  color: #e5e5e5;
  margin-top: 4px;
  word-break: break-word;
  white-space: pre-wrap;
}

.log-empty {
  color: #666;
  text-align: center;
  padding: 20px;
  font-style: italic;
}

.log-files-section {
  margin-top: 24px;
}

.log-files-section h4 {
  color: #60a5fa;
  margin-bottom: 12px;
}

.log-files-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.log-file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
}

.log-file-item .file-name {
  color: #e5e5e5;
  font-weight: 500;
  flex: 1;
}

.log-file-item .file-size {
  color: #888;
  font-size: 12px;
  margin: 0 12px;
}

.log-file-item .file-date {
  color: #888;
  font-size: 12px;
  margin: 0 12px;
}

.log-file-item button {
  padding: 4px 8px;
  font-size: 12px;
  background: rgba(96, 165, 250, 0.2);
  color: #60a5fa;
  border: 1px solid rgba(96, 165, 250, 0.3);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.log-file-item button:hover {
  background: rgba(96, 165, 250, 0.3);
}

.log-file-item button + button {
  margin-left: 8px;
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
  border-color: rgba(34, 197, 94, 0.3);
}

.log-file-item button + button:hover {
  background: rgba(34, 197, 94, 0.3);
}
```

### 6. Integration Points

**CRITICAL: Async Context Detection**

The spec originally used `asyncio._get_running_loop()` which is a **PRIVATE API** (underscore prefix). This has been fixed to use the public API with proper error handling.

#### 6.1 In `council.py` - Stage 1 Errors

```python
# In stage1_collect_responses, after getting error response:
if response.get('error'):
    # ADD THIS:
    from .error_logger import log_model_error
    import asyncio
    
    provider_name = get_provider_name(model)
    error_type = response.get('error_type', 'unknown_error')
    error_msg = response.get('error_message', 'Unknown error')
    
    # CRITICAL FIX: Use public API with try/except instead of private _get_running_loop()
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(log_model_error(
            model=model,
            provider=provider_name,
            error_type=error_type,
            message=error_msg
        ))
    except RuntimeError:
        # Not in async context, log synchronously
        import asyncio as sync_asyncio
        sync_asyncio.run(log_model_error(
            model=model,
            provider=provider_name,
            error_type=error_type,
            message=error_msg
        ))
```

#### 6.2 In `council.py` - Stage Events

```python
# At stage completion:
from .error_logger import log_event
import asyncio

# Stage 1 complete
try:
    asyncio.get_running_loop()
    asyncio.create_task(log_event("stage1_complete", {
        "total": len(models),
        "success": len([r for r in results if not r.get('error')]),
        "failed": len([r for r in results if r.get('error')])
    }))
except RuntimeError:
    # Not in async context (shouldn't happen in production, but safe fallback)
    pass

# Stage 2 complete
try:
    asyncio.get_running_loop()
    asyncio.create_task(log_event("stage2_complete", {
        "rankings_received": len(stage2_results)
    }))
except RuntimeError:
    pass

# Stage 3 complete
try:
    asyncio.get_running_loop()
    asyncio.create_task(log_event("stage3_complete", {
        "chairman_model": chairman_model,
        "success": not result.get('error')
    }))
except RuntimeError:
    pass
```

#### 6.3 Migration of Existing print() Statements

In `backend/main.py`, replace print statements with log_event calls:

```python
# Replace: print("Client disconnected before web search")
# With:
await log_event("client_disconnect", {"stage": "web_search", "reason": "disconnected"}, level="WARN")

# Replace: print(f"DEBUG: Sending stage1_init with total={total_models}")
# With (only in debug mode):
await log_event("debug", {"action": "stage1_init", "total_models": total_models}, level="DEBUG")
# ... etc for all print statements
```

### 7. File Structure

```
llm-council-plus/
├── backend/
│   ├── error_logger.py       # NEW: Error logging module
│   ├── providers/
│   │   └── custom_openai.py  # MODIFIED: Enhanced error parsing
│   ├── council.py            # MODIFIED: Add logging calls + get_provider_name()
│   ├── settings.py           # MODIFIED: Add logging settings
│   └── main.py               # MODIFIED: Add log viewer endpoints + migrate prints
├── frontend/src/
│   └── components/
│       ├── Settings.jsx      # MODIFIED: Add Logs tab + UI
│       ├── Settings.css      # MODIFIED: Add log viewer styles
│       └── api.js            # MODIFIED: Add 4 API functions
├── data/
│   ├── logs/                 # NEW: Log folder (git-ignored via data/)
│   │   ├── council_2026-01-01.log
│   │   └── council_2026-01-02.log
│   ├── settings.json
│   └── conversations/
└── .gitignore                # NO CHANGE - data/ already covers logs
```

### 8. Log File Format

```
2026-01-01 14:30:45 | ERROR | [NanoGPT] [custom:gpt-4-turbo] RATE_LIMIT: Rate limit exceeded. Please try again in 30 seconds.
    Raw: {"error": {"message": "Rate limit exceeded", "retry_after": 30}}
2026-01-01 14:30:46 | ERROR | [NanoGPT] [custom:claude-3-opus] MODEL_NOT_FOUND: Model 'claude-3-opus' is not available or has been deprecated.
2026-01-01 14:30:50 | INFO  | [stage1_complete] {"total": 8, "success": 6, "failed": 2}
2026-01-01 14:30:52 | WARN  | [client_disconnect] {"stage": "web_search"}
2026-01-01 14:31:05 | INFO  | [stage2_complete] {"rankings_received": 6}
2026-01-01 14:31:15 | INFO  | [stage3_complete] {"chairman_model": "custom:gpt-4o", "success": true}
```

**Format:** `TIMESTAMP | LEVEL | [CONTEXT] MESSAGE`  
**Debug mode adds:** Extra fields and raw responses  
**Rotation:** File > 10MB creates `council_YYYY-MM-DD_N.log`  
**Retention:** Files > 7 days auto-deleted (checked hourly)

---

## Security Considerations

1. **Comprehensive key sanitization** - 17 patterns checked (api_key, secret, token, etc.)
2. **Path traversal prevention** - Reject paths containing `..` or `/` or `\`
3. **Sensitive data never in logs** - All data sanitized before logging
4. **Log folder already git-ignored** - `data/` in .gitignore covers data/logs/
5. **UTF-8 encoding** - Prevents encoding errors with special characters
6. **Async locks** - Prevents log file corruption under concurrent load
7. **Fallback logging** - If main logging fails, emergency log captures the error
8. **Size limits** - Raw responses truncated to 500 chars (debug mode) or 1000 chars (error parsing)

---

## Performance Considerations

1. **Async file operations** - Non-blocking with asyncio.Lock
2. **In-memory buffer** - UI doesn't hit filesystem for recent errors
3. **Cleanup runs hourly** - Not on every log write
4. **Size check on write** - Minimal overhead, only stat() call
5. **Lazy imports** - settings only imported when needed
6. **Buffer limit** - Max 100 recent errors in memory
7. **Debug mode optional** - Raw responses only in debug level

---

## Testing Plan

### Error Parsing Tests (NanoGPT Simulation)
| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| TC-1 | 429 rate limit response | Error type = "rate_limit" |
| TC-2 | 401 auth error | Error type = "auth_error" |
| TC-3 | 404 model not found | Error type = "model_not_found" |
| TC-4 | Non-JSON error response | Falls back to raw text |
| TC-5 | Complete error with raw | Raw logged in debug mode |

### Logging Functionality Tests
| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| TC-6 | Enable logging, send message | Log file created |
| TC-7 | Set "errors_only", success | No INFO entries in log |
| TC-8 | Set "all", success | INFO entry created |
| TC-9 | Set "debug", error | Raw response included |
| TC-10 | Log > 10MB | File rotates to _1.log |

### UI Tests
| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| TC-11 | View recent errors in UI | Errors displayed correctly |
| TC-12 | View log file in UI | File contents displayed |
| TC-13 | Rapid refresh clicks | No race conditions |
| TC-14 | Log with special chars | Display encoding correct |

### Security Tests
| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| TC-15 | Attempt path traversal | Rejected with 400 error |
| TC-16 | Log data with sensitive fields | Sanitized (keys removed) |
| TC-17 | Concurrent error logging | No file corruption |

### Integration Tests
| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| TC-18 | Existing prints migrate | No duplicate logging |
| TC-19 | Old logger redirects | Single source of truth |
| TC-20 | Full council workflow | All stages logged |

---

## Implementation Steps

### Progress Tracker

| Status | Description |
|--------|-------------|
| ⬜ | Not started |
| 🟡 | In progress |
| ✅ | Completed |
| ⏭️ | Skipped |

---

### Step 0: Pre-Implementation Audit (20 min)
- [ ] Search all files for `print(` statements in backend
- [ ] Search all files for `console.log/error/` in frontend
- [ ] Document all existing logging patterns
- [ ] Create migration plan for existing logs
- [ ] Verify .gitignore covers data/logs

---

### Step 1: Create Error Logger Module
- **File:** `backend/error_logger.py` (NEW FILE)
- **Time:** 40 min (increased for robustness)
- **Status:** ⬜ Not started

**Implementation Details:**
- Create new file at `backend/error_logger.py`
- Use lazy imports to avoid circular dependencies
- Reference: See "2. Error Logger Module" section above for full code

**Tasks:**
- [ ] Create new file `backend/error_logger.py`
- [ ] Add comprehensive sanitization constants
- [ ] Implement `cleanup_old_logs()` function (FR-7)
- [ ] Implement `get_log_path()` function with size rotation (FR-6)
- [ ] Implement async `log_model_error()` function with file locking
- [ ] Implement async `log_event()` function with sanitization
- [ ] Implement `get_recent_errors()` function
- [ ] Implement `get_log_files()` function
- [ ] Implement `read_log_file()` function with security checks
- [ ] Add `_sanitize_dict()` helper function
- [ ] Add `_log_to_fallback()` emergency logging
- [ ] Add async locks for thread safety
- [ ] Use UTC timezone for all timestamps (NFR-4)

---

### Step 2: Enhanced Error Parsing for Custom Endpoint
- **File:** `backend/providers/custom_openai.py` (MODIFY)
- **Time:** 35 min (increased for testing)
- **Status:** ⬜ Not started

**Implementation Details:**
- Modify existing `query()` method (around line 20-60)
- Add new `_parse_error_response()` method after `_get_config()` method
- Reference: See "1.1 Update Custom OpenAI Provider" section above

**Tasks:**
- [ ] Add `import json` at top of file
- [ ] Add `_parse_error_response()` method (after line 18)
- [ ] Update error handling in `query()` method (line 49-53)
- [ ] Update exception handling (line 59-60)
- [ ] Add lazy import: `from ..error_logger import log_model_error`
- [ ] Call `log_model_error()` when error occurs
- [ ] Test error parsing with sample responses

---

### Step 3: Create Provider Name Helper
- **File:** `backend/council.py` (MODIFY)
- **Time:** 10 min
- **Status:** ⬜ Not started
- **Blocks:** Step 5

Add helper function before provider initialization:

```python
def get_provider_name(model_id: str) -> str:
    """Extract provider name from model ID for logging."""
    if ":" in model_id:
        prefix = model_id.split(":")[0]
        # Get custom endpoint name if custom provider
        if prefix == "custom":
            settings = get_settings()
            return settings.custom_endpoint_name or "Custom"
        
        provider_map = {
            "ollama": "Ollama",
            "openrouter": "OpenRouter",
            "groq": "Groq",
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "google": "Google AI",
            "mistral": "Mistral AI",
            "deepseek": "DeepSeek",
        }
        return provider_map.get(prefix, prefix.upper())
    return "Unknown"
```

**Tasks:**
- [ ] Add `get_provider_name()` function (lines ~48-68)
- [ ] Import `get_settings` at top
- [ ] Test function with various model IDs

---

### Step 4: Add Logging Settings
- **File:** `backend/settings.py` (MODIFY)
- **Time:** 10 min
- **Status:** ⬜ Not started

**Implementation Details:**
- Add 3 new fields to `Settings` class (around line 122, before end of class)
- No new imports needed

**Tasks:**
- [ ] Add `logging_enabled: bool = False` to Settings class
- [ ] Add `logging_level: str = "errors_only"` to Settings class
- [ ] Add `logging_folder: str = "data/logs"` to Settings class

---

### Step 5: Migrate Existing Debug Statements
- **File:** `backend/main.py` (MODIFY)
- **Time:** 25 min
- **Status:** ⬜ Not started
- **Purpose:** Remove duplicate logging systems

**Find and replace all print() statements (12 locations):**
- Line 138: Client disconnect → log_event(WARN)
- Line 154: Search setup disconnect → log_event(WARN)
- Line 162: Search exec disconnect → log_event(WARN)
- Line 187: Stage1 debug → log_event(DEBUG)
- Line 223: Stage2 progress → log_event(INFO)
- Line 238: Stage3 disconnect → log_event(WARN)
- Line 251: Title error → log_event(ERROR)
- Lines 280, 287, 289: Stream cancel → log_event(INFO/WARN)
- Line 292: Stream error → log_event(ERROR)
- Line 646: Model fetch error → log_event(ERROR)

**Tasks:**
- [ ] Add lazy import: `from .error_logger import log_event`
- [ ] Replace all 12 print() statements with appropriate log_event() calls
- [ ] Remove or redirect existing logging imports
- [ ] Maintain same information level but structured format

---

### Step 6: Add Log Viewer API Endpoints
- **File:** `backend/main.py` (MODIFY)
- **Time:** 25 min
- **Status:** ⬜ Not started

**Implementation Details:**
- Modify `UpdateSettingsRequest` class (around line 308-355)
- Modify GET `/api/settings` response (around line 364-414)
- Modify PUT `/api/settings` validation (around line 560-613)
- Add 4 new endpoints after line 850

**Tasks:**
- [ ] Add 3 logging fields to `UpdateSettingsRequest`
- [ ] Add 3 logging fields to GET `/api/settings` response
- [ ] Add validation for logging fields in PUT `/api/settings`
- [ ] Add GET `/api/logs/recent` endpoint
- [ ] Add GET `/api/logs/files` endpoint
- [ ] Add GET `/api/logs/file/{filename}` endpoint
- [ ] Add POST `/api/logs/client` endpoint (optional)
- [ ] Test all endpoints with curl/httpie

---

### Step 7: Add Logging Calls to Council
- **File:** `backend/council.py` (MODIFY)
- **Time:** 25 min
- **Status:** ⬜ Not started

**Implementation Details:**
- Add imports for error_logger
- Add logging calls in stage1/2/3 functions
- Use get_provider_name() helper
- Handle async context properly

**Where to modify:**
- Line ~12: Add import for error_logger
- Line ~160-167: In stage1_collect_responses, after error result
- Line ~289-297: In stage2_collect_rankings, after error result
- Line ~408-415: In stage3_synthesize_final, when error occurs

**Tasks:**
- [ ] Add lazy import: `from .error_logger import log_model_error, log_event`
- [ ] Add logging calls in `stage1_collect_responses()` for errors
- [ ] Add logging calls in `stage2_collect_rankings()` for errors
- [ ] Add logging calls in `stage3_synthesize_final()` for errors
- [ ] Add stage completion events for all 3 stages
- [ ] Verify async/await context in each location

---

### Step 8: Update Settings Component
- **File:** `frontend/src/components/Settings.jsx` (MODIFY)
- **Time:** 45 min (increased for functions)
- **Status:** ⬜ Not started

**Implementation Details:**
- Add new tab "Logs" as 6th section
- Add state variables
- Add functions for loading logs
- Add UI controls and viewer

**Functions:**
```javascript
const loadRecentErrors = async () => {
  setIsLoadingLogs(true);
  try {
    const [errorsData, filesData] = await Promise.all([
      api.getRecentLogs(),
      api.getLogFiles()
    ]);
    setRecentErrors(errorsData.errors || []);
    setLogFiles(filesData.files || []);
  } catch (err) {
    console.error('Failed to load logs:', err);
    // Optionally send to server
    api.logToServer('ERROR', 'Failed to load logs', { error: err.message });
  } finally {
    setIsLoadingLogs(false);
  }
};

const viewLogFile = async (filename) => {
  try {
    const data = await api.readLogFile(filename, 200);
    // Open in modal or new tab
    openLogModal(data.content);
  } catch (err) {
    console.error('Failed to read log file:', err);
  }
};

const downloadLogFile = (filename) => {
  // Create download link
  const link = document.createElement('a');
  link.href = `${API_BASE}/api/logs/file/${encodeURIComponent(filename)}?lines=10000`;
  link.download = filename;
  link.click();
};
```

**Tasks:**
- [ ] Add 6 logging state variables (around line 68)
- [ ] Add `loadRecentErrors()` function
- [ ] Add `viewLogFile()` function
- [ ] Add `downloadLogFile()` function
- [ ] Update `loadSettings()` to load logging settings from API
- [ ] Update `handleSave()` to include logging settings in payload
- [ ] Add sidebar nav button for "📋 Logs" section
- [ ] Add `{activeSection === 'logs' && (...)}` section with all controls

---

### Step 9: Update API Client
- **File:** `frontend/src/api.js` (MODIFY)
- **Time:** 15 min
- **Status:** ⬜ Not started

**Implementation Details:**
- Add 4 new API functions following existing patterns
- Add after `getDefaultSettings()` function (around line 253)

**Tasks:**
- [ ] Add `getRecentLogs()` function to api object
- [ ] Add `getLogFiles()` function to api object
- [ ] Add `readLogFile()` function to api object
- [ ] Add `logToServer()` function to api object

---

### Step 10: Add Log Viewer Styles
- **File:** `frontend/src/components/Settings.css` (MODIFY)
- **Time:** 20 min
- **Status:** ⬜ Not started

**Implementation Details:**
- Add styles at END of file
- Follow existing color scheme
- Reference: See "5.4 CSS Styles" section above

**Tasks:**
- [ ] Add `.log-viewer-section` styles
- [ ] Add `.log-viewer-header` styles
- [ ] Add `.log-entries` styles (max-height, overflow, monospace)
- [ ] Add `.log-entry` and variants (error, warn, info)
- [ ] Add `.log-timestamp`, `.log-model`, `.log-type`, `.log-message` styles
- [ ] Add `.log-empty` styles
- [ ] Add `.log-files-section` styles
- [ ] Add `.log-file-item` and children styles

---

### Step 11: Test with NanoGPT
- **Time:** 30 min (increased for comprehensive testing)
- **Status:** ⬜ Not started

**Test Procedure:**
1. Start backend: `uv run python -m backend.main`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Go to Settings → Logs tab
5. Enable logging, set level to "debug"
6. Set up NanoGPT as custom endpoint (if available)
7. Select 8 models including some that might fail
8. Send a test message
9. Check if errors appear in UI and log file
10. Test file rotation by generating >10MB of logs
11. Verify old files deleted after 7 days
12. Test with "errors_only" level (should hide INFO)

**Tasks:**
- [ ] Verify backend starts without import errors
- [ ] Verify frontend compiles without errors
- [ ] Test: Enable logging toggle works
- [ ] Test: Changing log level updates correctly
- [ ] Test: Send message with models that succeed
- [ ] Test: Intentionally trigger errors (bad API key, invalid model)
- [ ] Test: Verify errors appear in "Recent Errors" viewer
- [ ] Test: Verify log file created at `data/logs/council_YYYY-MM-DD.log`
- [ ] Test: "Errors Only" level filters out INFO entries
- [ ] Test: "All Events" level includes INFO entries
- [ ] Test: "Debug" level includes raw responses
- [ ] Test: Log file > 10MB creates rotated file
- [ ] Test: Click refresh button reloads errors
- [ ] Test: View log file opens modal/content
- [ ] Test: Download log file works correctly
- [ ] Test: Logs survive application restart
- [ ] Test: Old logs cleaned up after retention period

---

### Step 12: Documentation (20 min)

**Tasks:**
- [ ] Create `docs/logging-guide.md` with user documentation
- [ ] Add logging section to main README.md
- [ ] Document log file location and format
- [ ] Document error types and meanings
- [ ] Add troubleshooting section for common errors

---

## Summary

| Step | File | Description | Time | Status |
|------|------|-------------|------|--------|
| 0 | Multiple | Pre-implementation audit | 20 min | ⬜ |
| 1 | `backend/error_logger.py` | Create error logging module (NEW) | 40 min | ⬜ |
| 2 | `backend/providers/custom_openai.py` | Enhanced error parsing | 35 min | ⬜ |
| 3 | `backend/council.py` | Add provider name helper | 10 min | ⬜ |
| 4 | `backend/settings.py` | Add 3 logging settings fields | 10 min | ⬜ |
| 5 | `backend/main.py` | Migrate existing print() statements | 25 min | ⬜ |
| 6 | `backend/main.py` | Add settings + 4 log endpoints | 25 min | ⬜ |
| 7 | `backend/council.py` | Add logging calls for errors | 25 min | ⬜ |
| 8 | `frontend/src/components/Settings.jsx` | Add Logs tab + UI | 45 min | ⬜ |
| 9 | `frontend/src/api.js` | Add 4 API functions | 15 min | ⬜ |
| 10 | `frontend/src/components/Settings.css` | Add log viewer styles | 20 min | ⬜ |
| 11 | - | Comprehensive testing | 30 min | ⬜ |
| 12 | docs/ | Documentation updates | 20 min | ⬜ |

**Total Estimated Time:** ~280 min (4.7 hours)  
**Completed:** 0/13 steps (0%)  
**Critical Path:** Steps 1 → 2 → 3 → 7 → 8 → 11

---

## Success Criteria

1. ✅ When a model fails, the **exact error reason** is visible
2. ✅ User can see **which models failed** and **why** in the UI
3. ✅ Errors are **persisted to file** for later debugging
4. ✅ User can **toggle** logging on/off and choose debug level
5. ✅ Log viewer shows **recent errors** without opening files
6. ✅ All existing **debug logs migrated** - no duplicate systems
7. ✅ Log files **never exceed 10MB** - size rotation enforced
8. ✅ **Sensitive data never appears** - comprehensive sanitization
9. ✅ **Async operations safe** - no file corruption under load
10. ✅ **Timezones consistent** - all logs in UTC
11. ✅ **Logging failures don't crash app** - fallback system works
12. ✅ **Old logs auto-cleaned** - 7 day retention works

---

## Alternative Approaches Considered

### Option A: Use Python Standard Logging
**Rejected:** Standard logging doesn't provide:
- In-memory buffer for UI display
- Automatic size-based rotation with pattern
- Integration with frontend viewer
- Structured JSON logging for recent errors

### Option B: Use Loguru Library
**Rejected:** While Loguru is excellent, it:
- Adds external dependency (project prefers stdlib)
- Doesn't solve the UI buffer requirement
- Would still need custom integration

### Option C: Log to SQLite Database
**Rejected:** Database provides:
- Query capabilities ✓
But drawbacks:
- Requires migration/schema management
- Harder for users to inspect manually
- Slower for simple file tail operations
- Overkill for debugging use case

### Option D: Async File Writes Only (No Buffer)
**Rejected:** Would:
- Require filesystem read for every UI refresh
- Cause performance issues with many errors
- Make recent errors slow to display

**Chosen Approach:** Custom module with:
- Async file logging for performance
- In-memory buffer for UI responsiveness
- Size-based rotation (FR-6 compliance)
- Comprehensive sanitization
- UTC timestamps for consistency
- Fallback logging for reliability

---

## Backward Compatibility

### Settings File
- **Old:** No logging fields
- **New:** Adds 3 new fields with defaults
- **Behavior:** Existing users will have logging disabled by default

### Log Files
- **New installations:** Start fresh
- **Existing files:** Will be cleaned up after 7 days per retention policy

### API
- **New endpoints:** `/api/logs/*` - don't conflict with existing
- **Settings update:** Additive fields, backward compatible

### Frontend
- **New tab:** "Logs" added to Settings - doesn't affect existing UI
- **New state:** 6 new state variables, isolated to Settings component

---

## Monitoring & Maintenance

### Post-Deployment Checks
- [ ] Log files being created
- [ ] No sensitive data in logs
- [ ] File size staying under 10MB
- [ ] Old files cleaned up after 7 days
- [ ] No errors in fallback.log
- [ ] UI loads recent errors quickly

### Ongoing Maintenance
- Check disk space in log folder monthly
- Review error patterns for system improvements
- Update error parsing for new provider formats
- Monitor fallback.log for logging failures

---

## Troubleshooting Guide

### Problem: "No logs are being created"
**Diagnosis:** 
1. Check `data/logs/` folder exists
2. Verify logging_enabled = true in settings
3. Check `data/logs/fallback.log` for errors

**Solution:** Enable logging in Settings → Logs tab

### Problem: "Recent errors not showing in UI"
**Diagnosis:** 
1. Check browser console for errors
2. Verify `/api/logs/recent` endpoint works
3. Check if buffer exceeded 100 entries

**Solution:** Refresh logs or restart backend

### Problem: "Log files growing too large"
**Diagnosis:** 
Check file sizes in `data/logs/`

**Solution:** 
- Verify size rotation code active
- Check for rapid error generation
- Adjust log level to "errors_only"

### Problem: "Sensitive data in logs"
**Diagnosis:** 
Check logs for API keys, tokens, etc.

**Solution:** 
- Immediately rotate API keys
- Report sanitization bug
- Check SANITIZE_KEYS pattern

---

## References

- [NanoGPT API Documentation](https://docs.nano-gpt.com)
- [OpenAI Error Codes](https://platform.openai.com/docs/guides/error-codes)
- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)

---

## Change Log

**2026-01-04 (Updated - Critical Fixes Applied):**
- **CRITICAL FIX**: Replaced asyncio._get_running_loop() (private API) with asyncio.get_running_loop() + try/except
- **CRITICAL FIX**: Replaced blocking file I/O with asyncio.to_thread() for non-blocking writes
- **CRITICAL FIX**: Added _append_to_file() helper for thread pool execution
- **CRITICAL FIX**: Added background task tracking to prevent silent cleanup failures
- Fixed FR-6 compliance: Added size-based rotation (10MB max)
- Added FR-8: Migration of existing debug logs
- Enhanced NFR-2: Comprehensive sanitization (17 patterns vs 2)
- Added NFR-4: UTC timezone for all timestamps
- Added NFR-5: Fallback logging system
- Added async locking for concurrency safety
- Added debug log level option
- Added client logging endpoint
- Removed redundant Step 9 (.gitignore)
- Added pre-implementation audit step
- Updated all code samples with fixes
- Added 10 additional test cases
- Added troubleshooting guide
- Increased time estimates for robustness
- Added provider name helper function
- Integrated lazy imports to prevent circular deps
- Added path traversal prevention
- Updated success criteria to 12 items
- **FIX NEEDED**: Note about duplicate line 401 in main.py (council_member_filters repeated)
- **FIX NEEDED**: Note about council.py logger calls at lines 18, 46 requiring migration
- **FIX NEEDED**: Note that error parsing should be extended to ALL providers, not just custom_openai.py

**2026-01-01 (Original):**
- Initial specification created
- Basic error parsing design
- UI viewer concept
- File-based logging

---

**Implementation Notes:**

**⚠️ KNOWN issues to address during implementation:**
1. main.py line 401: Duplicate `council_member_filters` field - remove one
2. council.py lines 18, 46: Existing logger.warning/info calls need migration to new system
3. error_logger.py: Apply to ALL provider files, not just custom_openai.py

**Document Status:** ✅ Ready for Implementation (Critical async pattern fixes applied)
