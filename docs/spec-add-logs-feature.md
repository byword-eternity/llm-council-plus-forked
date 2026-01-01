# Feature Specification: Logging System

**Created:** 2026-01-01  
**Updated:** 2026-01-01  
**Status:** Draft  
**Priority:** High

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
4. **Log file persistence** - Save logs to files for later review
5. **UI Log Viewer** - View recent logs directly in Settings

## Requirements

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Enhanced error parsing for custom OpenAI endpoints | **Critical** |
| FR-2 | User can enable/disable logging via Settings UI | High |
| FR-3 | User can select log level: "all" or "errors_only" | High |
| FR-4 | Logs are written to files (`data/logs/`) | High |
| FR-5 | User can view recent logs in Settings UI | High |
| FR-6 | Log files are rotated automatically (max 10MB per file) | Medium |
| FR-7 | Old log files are retained for 7 days | Low |

### Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Logging should not significantly impact application performance |
| NFR-2 | Sensitive data (API keys) should NEVER be logged |
| NFR-3 | Error messages should be human-readable and actionable |

## Codebase Context (IMPORTANT - Read Before Implementing)

This section contains all the patterns and conventions needed for implementation.
Reference: `AGENTS.md` for general project conventions.

### Project Conventions

| Rule | Details |
|------|---------|
| **Backend imports** | Relative ONLY: `from .config import ...`, NEVER `from backend.` |
| **Backend port** | 8001 (NOT 8000) |
| **Run backend** | `uv run python -m backend.main` from project root |
| **React state** | Immutable updates via spread operator |
| **Data folder** | `data/` is git-ignored, contains runtime storage |

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
    logging_level: str = "errors_only"
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
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Relative imports (MUST use relative)
from .settings import get_settings
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
1. Parses JSON error response
2. Categorizes error type
3. Calls error_logger
4. Returns structured error dict

### CSS Pattern

**File:** `frontend/src/components/Settings.css`

**Add new styles at end of file.** Follow existing patterns for:
- `.settings-section` styling
- Color scheme: use existing colors (`#f87171` for errors, `#60a5fa` for info)
- Background: `rgba(0, 0, 0, 0.2)` for dark panels
- Border: `1px solid rgba(255, 255, 255, 0.1)`

### .gitignore Update

**File:** `.gitignore`

**Add line:**
```
data/logs/
```

---

## Technical Design

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
    error_info = self._parse_error_response(response, model)
    
    # Log the error
    from .error_logger import log_model_error
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

def _parse_error_response(self, response, model: str) -> dict:
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
    display_message = f"[{model}] {error_type.upper()}: {message}"
    
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

### 2. Error Logger Module (`backend/error_logger.py`)

New module for centralized error logging:

```python
"""Error logging for LLM Council Plus."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from .settings import get_settings

# In-memory buffer for recent errors (for UI display)
_recent_errors: List[Dict[str, Any]] = []
MAX_RECENT_ERRORS = 100
_last_cleanup = None


def cleanup_old_logs(retention_days: int = 7) -> None:
    """Delete log files older than retention_days."""
    global _last_cleanup
    now = datetime.now()
    
    # Run cleanup at most once per hour
    if _last_cleanup and (now - _last_cleanup).total_seconds() < 3600:
        return
        
    settings = get_settings()
    folder = Path(settings.logging_folder)
    if not folder.exists():
        return
    
    cutoff = now - timedelta(days=retention_days)
    
    for log_file in folder.glob("council_*.log"):
        try:
            # Parse date from filename: council_2026-01-01.log
            date_str = log_file.stem.replace("council_", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            if file_date < cutoff:
                try:
                    log_file.unlink()
                except Exception as e:
                    print(f"Failed to delete old log {log_file}: {e}")
        except Exception:
            pass # Ignore files with bad names
            
    _last_cleanup = now


def get_log_path() -> Path:
    """Get the log file path based on settings."""
    settings = get_settings()
    folder = Path(settings.logging_folder)
    folder.mkdir(parents=True, exist_ok=True)
    
    # Trigger cleanup opportunistically
    cleanup_old_logs()
    
    today = datetime.now().strftime("%Y-%m-%d")
    return folder / f"council_{today}.log"


def log_model_error(
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
    settings = get_settings()
    
    if not settings.logging_enabled:
        return
    
    timestamp = datetime.now()
    
    error_entry = {
        "timestamp": timestamp.isoformat(),
        "level": "ERROR",
        "model": model,
        "provider": provider,
        "error_type": error_type,
        "status_code": status_code,
        "message": message,
    }
    
    # Add to recent errors buffer (for UI)
    _recent_errors.insert(0, error_entry)
    if len(_recent_errors) > MAX_RECENT_ERRORS:
        _recent_errors.pop()
    
    # Write to file
    log_line = (
        f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} | ERROR | "
        f"[{provider}] [{model}] {error_type.upper()}: {message}"
    )
    
    if raw_response and settings.logging_level == "all":
        # Include raw response in verbose mode
        log_line += f"\n    Raw: {raw_response[:500]}"
    
    log_line += "\n"
    
    try:
        log_path = get_log_path()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"Failed to write log: {e}")


def log_event(
    event_type: str,
    data: Dict[str, Any],
    level: str = "INFO"
) -> None:
    """
    Log a general event (stage complete, search, etc.).
    
    Only logs if logging_enabled=True and logging_level="all"
    """
    settings = get_settings()
    
    if not settings.logging_enabled:
        return
    
    if settings.logging_level == "errors_only" and level != "ERROR":
        return
    
    timestamp = datetime.now()
    
    # Sanitize data - remove any API keys
    sanitized = {
        k: v for k, v in data.items()
        if "api_key" not in k.lower() and "key" not in k.lower()
    }
    
    log_line = (
        f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {level:5} | "
        f"[{event_type}] {json.dumps(sanitized, default=str)}\n"
    )
    
    try:
        log_path = get_log_path()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"Failed to write log: {e}")


def get_recent_errors(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent errors from memory buffer for UI display."""
    return _recent_errors[:limit]


def get_log_files() -> List[Dict[str, Any]]:
    """Get list of log files with metadata."""
    settings = get_settings()
    folder = Path(settings.logging_folder)
    
    if not folder.exists():
        return []
    
    files = []
    for f in folder.glob("council_*.log"):
        stat = f.stat()
        files.append({
            "name": f.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    
    return sorted(files, key=lambda x: x["modified"], reverse=True)


def read_log_file(filename: str, lines: int = 100) -> str:
    """Read last N lines from a log file."""
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
    
    # Logging Settings
    logging_enabled: bool = False
    logging_level: str = "errors_only"  # "all" or "errors_only"
    logging_folder: str = "data/logs"
```

**Note:** Default is `"errors_only"` since that's the primary use case.

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
    if request.logging_level not in ["all", "errors_only"]:
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
const [selectedLogContent, setSelectedLogContent] = useState('');
const [isLoadingLogs, setIsLoadingLogs] = useState(false);
```

#### 5.2 Log Viewer UI Component

Add a new section in Settings (or a new tab "Logs"):

```jsx
{/* Logging Settings & Viewer */}
<div className="settings-section">
  <h3>📋 Logging</h3>
  
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
          <div key={idx} className="log-entry error">
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
            <button onClick={() => viewLogFile(file.name)}>
              View
            </button>
          </div>
        ))}
      </div>
    </div>
  )}
</div>
```

#### 5.3 CSS Styles (`Settings.css`)

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
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
}

.log-entry {
  padding: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.log-entry.error {
  background: rgba(248, 113, 113, 0.1);
  border-left: 3px solid #f87171;
}

.log-timestamp {
  color: #888;
  font-size: 11px;
}

.log-model {
  color: #60a5fa;
  font-weight: 500;
}

.log-type {
  color: #f87171;
  text-transform: uppercase;
  font-size: 11px;
  font-weight: 600;
}

.log-message {
  color: #e5e5e5;
  margin-top: 4px;
  word-break: break-word;
}

.log-empty {
  color: #666;
  text-align: center;
  padding: 20px;
  font-style: italic;
}
```

### 6. Integration Points

Add logging calls throughout the codebase:

#### 6.1 In `council.py` - Stage 1 Errors

```python
# In stage1_collect_responses, after getting error response:
if response.get('error'):
    from .error_logger import log_model_error
    log_model_error(
        model=model,
        provider=get_provider_name(model),
        error_type=response.get('error_type', 'unknown'),
        message=response.get('error_message', 'Unknown error')
    )
```

#### 6.2 In `council.py` - Stage Events

```python
# At stage completion:
from .error_logger import log_event

# Stage 1 complete
log_event("stage1_complete", {
    "total": len(models),
    "success": len([r for r in results if not r.get('error')]),
    "failed": len([r for r in results if r.get('error')])
})

# Stage 2 complete
log_event("stage2_complete", {
    "rankings_received": len(stage2_results)
})

# Stage 3 complete
log_event("stage3_complete", {
    "chairman_model": chairman_model,
    "success": not result.get('error')
})
```

### 7. File Structure

```
llm-council-plus/
├── backend/
│   ├── error_logger.py       # NEW: Error logging module
│   ├── providers/
│   │   └── custom_openai.py  # MODIFIED: Enhanced error parsing
│   ├── council.py            # MODIFIED: Add logging calls
│   ├── settings.py           # MODIFIED: Add logging settings
│   └── main.py               # MODIFIED: Add log viewer endpoints
├── frontend/src/
│   └── components/
│       ├── Settings.jsx      # MODIFIED: Add logging UI + viewer
│       └── Settings.css      # MODIFIED: Add log viewer styles
├── data/
│   ├── logs/                 # NEW: Log folder (git-ignored)
│   │   ├── council_2026-01-01.log
│   │   └── council_2026-01-02.log
│   ├── settings.json
│   └── conversations/
└── .gitignore                # MODIFIED: Add data/logs/
```

### 8. Log File Format

```
2026-01-01 14:30:45 | ERROR | [NanoGPT] [custom:gpt-4-turbo] RATE_LIMIT: Rate limit exceeded. Please try again in 30 seconds.
2026-01-01 14:30:46 | ERROR | [NanoGPT] [custom:claude-3-opus] MODEL_NOT_FOUND: Model 'claude-3-opus' is not available or has been deprecated.
2026-01-01 14:30:50 | INFO  | [stage1_complete] {"total": 8, "success": 6, "failed": 2}
2026-01-01 14:31:05 | INFO  | [stage2_complete] {"rankings_received": 6}
2026-01-01 14:31:15 | INFO  | [stage3_complete] {"chairman_model": "custom:gpt-4o", "success": true}
```

## Security Considerations

1. **Never log API keys** - All data is sanitized before logging
2. **Log folder in .gitignore** - Add `data/logs/` to `.gitignore`
3. **Path traversal prevention** - Reject paths containing `..`
4. **Limit raw response size** - Truncate to 500-1000 chars

## Testing Plan

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| TC-1 | Model fails with rate limit (429) | Error logged with "RATE_LIMIT" type |
| TC-2 | Model fails with auth error (401) | Error logged with "AUTH_ERROR" type |
| TC-3 | Model not found (404) | Error logged with "MODEL_NOT_FOUND" type |
| TC-4 | Enable logging, send message | Log file created |
| TC-5 | Set "errors_only", success | No INFO entries in log |
| TC-6 | View recent errors in UI | Errors displayed correctly |
| TC-7 | View log file in UI | File contents displayed |

## Implementation Steps

### Progress Tracker

| Status | Description |
|--------|-------------|
| ⬜ | Not started |
| 🟡 | In progress |
| ✅ | Completed |
| ⏭️ | Skipped |

---

### Backend Implementation

#### Step 1: Create Error Logger Module
- **File:** `backend/error_logger.py` (NEW FILE)
- **Time:** 30 min
- **Status:** ⬜ Not started

**Implementation Details:**
- Create new file at `backend/error_logger.py`
- Use relative imports: `from .settings import get_settings`
- Reference: See "2. Error Logger Module" section in Technical Design for full code

**Tasks:**
- [ ] Create new file `backend/error_logger.py`
- [ ] Implement `cleanup_old_logs()` function (FR-7)
- [ ] Implement `get_log_path()` function (calls cleanup)
- [ ] Implement `log_model_error()` function
- [ ] Implement `log_event()` function
- [ ] Implement `get_recent_errors()` function
- [ ] Implement `get_log_files()` function
- [ ] Implement `read_log_file()` function
- [ ] Add `_recent_errors` in-memory buffer (max 100 items)

---

#### Step 2: Enhanced Error Parsing for Custom Endpoint
- **File:** `backend/providers/custom_openai.py` (MODIFY)
- **Time:** 30 min
- **Status:** ⬜ Not started

**Implementation Details:**
- Modify existing `query()` method (around line 20-60)
- Add new `_parse_error_response()` method after `_get_config()` method
- Import json at top: `import json`
- Reference: See "1.1 Update Custom OpenAI Provider" section in Technical Design

**Where to modify:**
- Line 49-53: Replace simple error return with enhanced parsing
- Line 59-60: Update exception handling to use enhanced parsing

**Tasks:**
- [ ] Add `import json` at top of file
- [ ] Add `_parse_error_response()` method (after line 18)
- [ ] Update error handling in `query()` method (line 49-53)
- [ ] Update exception handling (line 59-60)
- [ ] Add import: `from ..error_logger import log_model_error`
- [ ] Call `log_model_error()` when error occurs

---

#### Step 3: Add Logging Settings
- **File:** `backend/settings.py` (MODIFY)
- **Time:** 10 min
- **Status:** ⬜ Not started

**Implementation Details:**
- Add 3 new fields to `Settings` class (around line 122, before end of class)
- No new imports needed

**Where to modify:**
- Line ~122: Add fields before class ends

**Tasks:**
- [ ] Add `logging_enabled: bool = False` to Settings class
- [ ] Add `logging_level: str = "errors_only"` to Settings class
- [ ] Add `logging_folder: str = "data/logs"` to Settings class

---

#### Step 4: Add Log Viewer API Endpoints
- **File:** `backend/main.py` (MODIFY)
- **Time:** 20 min
- **Status:** ⬜ Not started

**Implementation Details:**
- Modify `UpdateSettingsRequest` class (around line 308-355)
- Modify GET `/api/settings` response (around line 364-414)
- Modify PUT `/api/settings` validation (around line 438-613)
- Add 3 new endpoints after line 850

**Where to modify:**
- Line ~355: Add 3 Optional fields to UpdateSettingsRequest
- Line ~414: Add 3 fields to GET response
- Line ~560: Add validation for logging settings
- After line 850: Add 3 new GET endpoints

**Tasks:**
- [ ] Add `logging_enabled: Optional[bool] = None` to UpdateSettingsRequest
- [ ] Add `logging_level: Optional[str] = None` to UpdateSettingsRequest
- [ ] Add `logging_folder: Optional[str] = None` to UpdateSettingsRequest
- [ ] Add logging fields to GET `/api/settings` response dict
- [ ] Add validation logic in PUT `/api/settings` for logging fields
- [ ] Add GET `/api/logs/recent` endpoint
- [ ] Add GET `/api/logs/files` endpoint
- [ ] Add GET `/api/logs/file/{filename}` endpoint

---

#### Step 5: Add Logging Calls to Council
- **File:** `backend/council.py` (MODIFY)
- **Time:** 20 min
- **Status:** ⬜ Not started

**Implementation Details:**
- Add import at top: `from .error_logger import log_model_error, log_event`
- Add logging calls in stage1/2/3 functions
- Helper function needed: `get_provider_name()` to extract provider from model ID

**Where to modify:**
- Line ~12: Add import for error_logger
- Line ~160-167: In stage1_collect_responses, after error result is built
- Line ~289-297: In stage2_collect_rankings, after error result is built
- Line ~408-415: In stage3_synthesize_final, when error occurs

**Tasks:**
- [ ] Add import: `from .error_logger import log_model_error, log_event`
- [ ] Create helper: `def get_provider_name(model_id: str) -> str`
- [ ] Add `log_model_error()` call in `stage1_collect_responses()` for errors
- [ ] Add `log_model_error()` call in `stage2_collect_rankings()` for errors
- [ ] Add `log_model_error()` call in `stage3_synthesize_final()` for errors
- [ ] (Optional) Add `log_event()` calls for stage completion events

---

### Frontend Implementation

#### Step 6: Update Settings Component
- **File:** `frontend/src/components/Settings.jsx` (MODIFY)
- **Time:** 40 min
- **Status:** ⬜ Not started

**Implementation Details:**
- Add new tab "Logs" as 6th section
- Current sections: 'llm_keys', 'council', 'prompts', 'search', 'import_export'
- New section: 'logs'

**Where to modify:**
- Line ~15: Add 'logs' to activeSection comment
- Line ~68: Add logging state variables (after existing state declarations)
- Line ~230: Add logging settings loading in loadSettings()
- **Nav Button**: Add new sidebar nav button for Logs immediately AFTER the 'import_export' button
- **Section Content**: Add new section rendering immediately AFTER the import_export section block closes
- In handleSave(): Add logging settings to save payload

**State variables to add (around line 68):**
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

**Functions to add:**
```javascript
const loadRecentErrors = async () => {
  setIsLoadingLogs(true);
  try {
    const data = await api.getRecentLogs();
    setRecentErrors(data.errors || []);
    const filesData = await api.getLogFiles();
    setLogFiles(filesData.files || []);
  } catch (err) {
    console.error('Failed to load logs:', err);
  } finally {
    setIsLoadingLogs(false);
  }
};
```

**Tasks:**
- [ ] Add logging state variables (6 variables)
- [ ] Add `loadRecentErrors()` function
- [ ] Add `viewLogFile()` function
- [ ] Update `loadSettings()` to load logging settings from API response
- [ ] Update `handleSave()` to include logging settings in payload
- [ ] Add sidebar nav button for "📋 Logs" section
- [ ] Add `{activeSection === 'logs' && (...)}` section with:
  - [ ] Enable Logging toggle
  - [ ] Log Level dropdown (conditional on enabled)
  - [ ] Log Folder input (conditional on enabled)
  - [ ] Recent Errors viewer
  - [ ] Log Files list

---

#### Step 6b: Update API Client
- **File:** `frontend/src/api.js` (MODIFY)
- **Time:** 10 min (included in Step 6 time)
- **Status:** ⬜ Not started

**Implementation Details:**
- Add 3 new API functions following existing patterns
- Add after `getDefaultSettings()` function (around line 253)

**Functions to add:**
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
```

**Tasks:**
- [ ] Add `getRecentLogs()` function to api object
- [ ] Add `getLogFiles()` function to api object
- [ ] Add `readLogFile()` function to api object

---

#### Step 7: Add Log Viewer Styles
- **File:** `frontend/src/components/Settings.css` (MODIFY)
- **Time:** 15 min
- **Status:** ⬜ Not started

**Implementation Details:**
- Add styles at END of file
- Follow existing color scheme:
  - Error color: `#f87171`
  - Info color: `#60a5fa`
  - Background: `rgba(0, 0, 0, 0.2)`
  - Border: `rgba(255, 255, 255, 0.1)`
- Reference: See "5.3 CSS Styles" section in Technical Design for full CSS

**Tasks:**
- [ ] Add `.log-viewer-section` styles
- [ ] Add `.log-viewer-header` styles
- [ ] Add `.log-entries` styles (max-height 300px, overflow-y auto)
- [ ] Add `.log-entry` and `.log-entry.error` styles
- [ ] Add `.log-timestamp`, `.log-model`, `.log-type`, `.log-message` styles
- [ ] Add `.log-empty` styles
- [ ] Add `.log-files-section` and `.log-file-item` styles

---

### Testing & Finalization

#### Step 8: Test with NanoGPT
- **Time:** 15 min
- **Status:** ⬜ Not started

**Test Procedure:**
1. Start backend: `uv run python -m backend.main`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Go to Settings → Logs tab
5. Enable logging
6. Set up NanoGPT as custom endpoint (if not already)
7. Select 8 models including some that might fail
8. Send a test message
9. Check if errors appear in UI and log file

**Tasks:**
- [ ] Verify backend starts without import errors
- [ ] Verify frontend compiles without errors
- [ ] Test: Enable logging toggle works
- [ ] Test: Send message with models that succeed
- [ ] Test: Intentionally trigger rate limit (if possible)
- [ ] Test: Verify errors appear in "Recent Errors" viewer
- [ ] Test: Verify log file created at `data/logs/council_YYYY-MM-DD.log`
- [ ] Test: "Errors Only" level filters out INFO entries
- [ ] Test: "All Events" level includes INFO entries

---

#### Step 9: Update .gitignore
- **File:** `.gitignore` (MODIFY)
- **Time:** 5 min
- **Status:** ⬜ Not started

**Implementation Details:**
- Add `data/logs/` to .gitignore
- This prevents log files from being committed

**Where to modify:**
- Add after existing `data/` entry (if exists) or in data section

**Tasks:**
- [ ] Add `data/logs/` to .gitignore
- [ ] Verify folder is properly ignored: `git status` should not show log files

---

### Summary

| Step | File | Description | Status | Time |
|------|------|-------------|--------|------|
| 1 | `backend/error_logger.py` | Create error logging module (NEW) | ⬜ | 30 min |
| 2 | `backend/providers/custom_openai.py` | Enhanced error parsing | ⬜ | 30 min |
| 3 | `backend/settings.py` | Add 3 logging settings fields | ⬜ | 10 min |
| 4 | `backend/main.py` | Add settings + 3 log endpoints | ⬜ | 20 min |
| 5 | `backend/council.py` | Add logging calls for errors | ⬜ | 20 min |
| 6 | `frontend/src/components/Settings.jsx` | Add Logs tab + UI | ⬜ | 40 min |
| 6b | `frontend/src/api.js` | Add 3 API functions | ⬜ | (incl.) |
| 7 | `frontend/src/components/Settings.css` | Add log viewer styles | ⬜ | 15 min |
| 8 | - | Test with NanoGPT | ⬜ | 15 min |
| 9 | `.gitignore` | Add data/logs/ | ⬜ | 5 min |

**Total Estimated Time:** ~3 hours  
**Completed:** 0/10 steps (0%)

## Success Criteria

1. ✅ When a model fails, the **exact error reason** is visible
2. ✅ User can see **which models failed** and **why** in the UI
3. ✅ Errors are **persisted to file** for later debugging
4. ✅ User can **toggle** logging on/off and choose level
5. ✅ Log viewer shows **recent errors** without opening files

## References

- [NanoGPT API Documentation](https://docs.nano-gpt.com)
- [OpenAI Error Codes](https://platform.openai.com/docs/guides/error-codes)
- [Existing Settings Pattern](../backend/settings.py)
- [Existing Custom Provider](../backend/providers/custom_openai.py)
