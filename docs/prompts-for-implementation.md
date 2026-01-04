# Implementation Prompts for Spec Documents

This file contains ready-to-use prompts for AI agents to implement features from specification documents.

**Target Spec:** `docs/spec-add-logs-feature.md`

---

## Required Context Files

Before implementing, the AI should read these files:

| File | Purpose |
|------|---------|
| `docs/spec-add-logs-feature.md` | Full implementation spec with code snippets (1832 lines) |
| `CLAUDE.md` | Project architecture, conventions, gotchas |
| `AGENTS.md` | Quick reference for structure and anti-patterns |

**Key conventions from CLAUDE.md:**
- Backend imports: ALWAYS relative (`from .module import ...`), NEVER absolute
- Backend port: 8001 (NOT 8000)
- Run backend: `uv run python -m backend.main` from project root
- React state: Immutable updates via spread operator
- Model ID format: `prefix:model_name` (e.g., `custom:gpt-4`, `ollama:llama3`)

---

## Fresh Start Prompt

Use this when starting implementation from scratch (0% progress).

```
Implement the logging feature based on the spec at docs/spec-add-logs-feature.md

CONTEXT FILES TO READ FIRST:
1. docs/spec-add-logs-feature.md - Full implementation spec with code snippets (1832 lines)
2. CLAUDE.md - Project architecture, conventions, critical implementation details
3. AGENTS.md - Quick reference for structure and anti-patterns

WHAT THIS FEATURE DOES:
- Adds error visibility for LLM Council Plus (especially NanoGPT endpoint users)
- Logs model errors to files and displays them in Settings UI
- Toggle on/off with "errors only", "all events", or "debug" level
- Size-based rotation (10MB max per file) and 7-day retention
- Debug mode includes raw responses for troubleshooting
- Migrates existing print() statements to unified logging
- Comprehensive sanitization prevents logging API keys
- UTC timestamps for consistency
- Async-safe with file locking prevents corruption
- Fallback logging if primary logging fails

INSTRUCTIONS:
1. Read the spec document COMPLETELY (all 1832 lines)
2. Follow the Implementation Steps section (lines 1282-1631)
3. Implement in order: Steps 0→1→2→3→4→5→6→7→8→9→10→11→12
4. Update the Progress Tracker in the spec after each step (change ⬜ to ✅)
5. Test backend compiles after Step 7: `uv run python -m backend.main`
6. Test frontend compiles after Step 11: `cd frontend && npm run dev`

DO:
- Use the exact code snippets from the spec's Technical Design section
- Follow existing patterns in each file
- Create data/logs/ folder if needed
- Implement async operations with proper locking
- Use UTC timezone for all timestamps

DO NOT:
- Skip steps or do them out of order (dependencies exist)
- Use absolute imports in backend (use `from .module import ...`)
- Commit API keys or log files
- Use sync file operations (must be async with locks)
- Log sensitive data (sanitization is critical)
```

---

## Continue Implementation Prompt

Use this when resuming work (some steps already completed).

```
Continue implementing the logging feature from docs/spec-add-logs-feature.md

CONTEXT FILES:
- docs/spec-add-logs-feature.md - Implementation spec (lines 1282-1631 have the steps)
- CLAUDE.md - Project conventions (read "Critical Implementation Details" section)

CURRENT PROGRESS (update before using):
- Step 0 (Pre-audit): [⬜] 
- Step 1 (error_logger.py): [⬜]
- Step 2 (custom_openai.py): [⬜]
- Step 3 (council.py - provider helper): [⬜]
- Step 4 (settings.py): [⬜]
- Step 5 (main.py - migrate prints): [⬜]
- Step 6 (main.py - API endpoints): [⬜]
- Step 7 (council.py - logging calls): [⬜]
- Step 8 (Settings.jsx): [⬜]
- Step 9 (api.js): [⬜]
- Step 10 (Settings.css): [⬜]
- Step 11 (Testing): [⬜]
- Step 12 (Documentation): [⬜]

INSTRUCTIONS:
1. Read the spec document to understand context
2. Check the Progress Tracker section (spec lines 1284-1291) for current status
3. Continue from the next pending step
4. Update Progress Tracker in the spec after completing each step
5. If you encounter errors, fix them before moving on

VERIFICATION CHECKPOINTS:
- After Step 7: Run `uv run python -m backend.main` - should start without import errors
- After Step 11: Run `cd frontend && npm run dev` - should compile without errors
- If either fails, STOP and fix the issue before proceeding

CRITICAL DEPENDENCIES:
- Step 3 (provider helper) MUST be done before Step 7
- Step 1 (error_logger) MUST be done before Steps 2, 5, 6, 7
- Step 9 (api.js) MUST be done before Step 11 testing
```

---

## Checkpoint Resume Prompt

Use this when you're unsure about current progress (most robust).

```
Resume logging feature implementation from docs/spec-add-logs-feature.md

CONTEXT FILES TO READ:
- docs/spec-add-logs-feature.md - Full spec with code snippets
- CLAUDE.md - Critical implementation details and gotchas

FIRST: Check current state by running these commands:
1. `git status` - see what files were modified
2. Check if backend/error_logger.py exists
3. Check if backend/council.py has get_provider_name() function
4. Check if backend/main.py has @app.get("/api/logs/recent") endpoint
5. Check if frontend/src/components/Settings.jsx has activeSection === 'logs' section
6. Check if frontend/src/api.js has logToServer() function

THEN: Read the spec and identify which steps are done based on:
- Step 0 done if: You've audited print/console statements
- Step 1 done if: backend/error_logger.py exists with async log_model_error() function
- Step 2 done if: backend/providers/custom_openai.py has _parse_error_response() method
- Step 3 done if: backend/council.py has get_provider_name() helper function
- Step 4 done if: backend/settings.py has logging_enabled field
- Step 5 done if: backend/main.py has replaced print() statements with log_event()
- Step 6 done if: backend/main.py has /api/logs/* endpoints
- Step 7 done if: backend/council.py calls log_model_error() in stage functions
- Step 8 done if: frontend/src/components/Settings.jsx has Logs tab UI
- Step 9 done if: frontend/src/api.js has 4 API functions including logToServer()
- Step 10 done if: frontend/src/components/Settings.css has .log-viewer-* styles
- Step 11 done if: Testing completed with verification checklist
- Step 12 done if: Documentation files created

FINALLY:
1. Update the Progress Tracker in the spec to reflect actual state
2. Continue from the first incomplete step
3. Follow the spec's code snippets exactly
4. Verify compilation after backend steps (7) and frontend steps (11)
```

---

## Single Step Prompts

Use these when you want to implement just one step at a time.

### Step 0: Pre-Implementation Audit

```
Implement Step 0 from docs/spec-add-logs-feature.md

STEP 0: Pre-Implementation Audit (20 min)
FILE: Multiple files (audit only)

TASKS (from spec lines 1295-1300):
1. Search all files for `print(` statements in backend
2. Search all files for `console.log/error/` in frontend
3. Document all existing logging patterns
4. Create migration plan for existing logs
5. Verify .gitignore covers data/logs

PURPOSE: Understand existing logging before adding new system

AFTER DONE: Update spec Progress Tracker - change Step 0 status from ⬜ to ✅
```

### Step 1: Create Error Logger Module

```
Implement Step 1 from docs/spec-add-logs-feature.md

STEP 1: Create Error Logger Module
FILE: backend/error_logger.py (NEW FILE)
TIME: 40 min

TASKS (from spec lines 1314-1327):
1. Create new file backend/error_logger.py
2. Add comprehensive sanitization constants (SANITIZE_KEYS with 17 patterns)
3. Implement cleanup_old_logs() function (FR-7) - runs hourly
4. Implement get_log_path() function with size rotation (FR-6) - 10MB max
5. Implement async log_model_error() function with file locking
6. Implement async log_event() function with sanitization
7. Implement get_recent_errors() function
8. Implement get_log_files() function
9. Implement read_log_file() function with security checks
10. Add _sanitize_dict() helper function
11. Add _log_to_fallback() emergency logging
12. Add async locks (_file_lock, _buffer_lock) for thread safety
13. Use UTC timezone for all timestamps (NFR-4)

KEY FEATURES TO INCLUDE:
- Async file operations with asyncio.Lock()
- Size-based rotation (10MB → creates council_YYYY-MM-DD_N.log)
- UTC timestamps (datetime.now(timezone.utc))
- Comprehensive sanitization (17 key patterns)
- Fallback logging to data/logs/fallback.log
- In-memory buffer for recent errors (max 100)

REFERENCE: See spec lines 378-657 for exact code to use.

VERIFICATION: File should be creatable without syntax errors.
AFTER DONE: Update spec Progress Tracker - change Step 1 status from ⬜ to ✅
```

### Step 2: Enhanced Error Parsing for Custom Endpoint

```
Implement Step 2 from docs/spec-add-logs-feature.md

STEP 2: Enhanced Error Parsing for Custom Endpoint
FILE: backend/providers/custom_openai.py (MODIFY)
TIME: 35 min

TASKS (from spec lines 1342-1348):
1. Add `import json` at top of file
2. Add _parse_error_response() method (after line 18)
3. Update error handling in query() method (line 49-53)
4. Update exception handling (line 59-60)
5. Add lazy import: `from ..error_logger import log_model_error`
6. Call log_model_error() when error occurs
7. Test error parsing with sample responses

KEY CHANGES:
- Parse JSON error responses from OpenAI-compatible endpoints
- Categorize errors by type (rate_limit, auth_error, model_not_found, etc.)
- Get provider name from settings for custom endpoints
- Return structured error dict with error_type, error_code, error_message
- Log errors with detailed context for debugging

REFERENCE: See spec lines 259-361 for exact code to use.

VERIFICATION: Run `uv run python -m backend.main` - should start without import errors.
AFTER DONE: Update spec Progress Tracker - change Step 2 status from ⬜ to ✅
```

### Step 3: Create Provider Name Helper

```
Implement Step 3 from docs/spec-add-logs-feature.md

STEP 3: Create Provider Name Helper
FILE: backend/council.py (MODIFY)
TIME: 10 min
BLOCKS: Step 7

TASKS (from spec lines 1384-1387):
1. Add get_provider_name() function (lines ~48-68, before provider initialization)
2. Import get_settings at top (if not already imported)
3. Test function with various model IDs

FUNCTION REQUIREMENTS:
- Extract provider name from model ID (e.g., "ollama:llama3" → "Ollama")
- Handle custom providers (get name from settings.custom_endpoint_name)
- Return "Unknown" for unrecognized formats
- Use provider mapping for known prefixes

REFERENCE: See spec lines 196-215 for exact code.

VERIFICATION: Function should handle: ollama:*, openrouter:*, groq:*, openai:*, anthropic:*, google:*, mistral:*, deepseek:*, custom:*
AFTER DONE: Update spec Progress Tracker - change Step 3 status from ⬜ to ✅
```

### Step 4: Add Logging Settings

```
Implement Step 4 from docs/spec-add-logs-feature.md

STEP 4: Add Logging Settings
FILE: backend/settings.py (MODIFY)
TIME: 10 min

TASKS (from spec lines 1400-1403):
1. Add `logging_enabled: bool = False` to Settings class
2. Add `logging_level: str = "errors_only"` to Settings class
3. Add `logging_folder: str = "data/logs"` to Settings class

WHERE: Add these 3 fields at the end of the Settings class, before the class ends (around line 122)

VALIDATION RULES:
- logging_level must be one of: "all", "errors_only", "debug"
- logging_folder must not contain ".." (path traversal prevention)

REFERENCE: See spec lines 660-672 for exact code pattern.

VERIFICATION: Settings should load with defaults if not present in existing settings.json
AFTER DONE: Update spec Progress Tracker - change Step 4 status from ⬜ to ✅
```

### Step 5: Migrate Existing Debug Statements

```
Implement Step 5 from docs/spec-add-logs-feature.md

STEP 5: Migrate Existing Debug Statements
FILE: backend/main.py (MODIFY)
TIME: 25 min
PURPOSE: Remove duplicate logging systems

TASKS (from spec lines 1425-1429):
1. Add lazy import: `from .error_logger import log_event` (import inside functions if needed)
2. Replace all 12 print() statements with appropriate log_event() calls
3. Remove or redirect existing logging imports
4. Maintain same information level but structured format

PRINT STATEMENTS TO REPLACE (find at these lines):
- Line 138: "Client disconnected before web search" → log_event("client_disconnect", {"stage": "web_search"}, level="WARN")
- Line 154: "Client disconnected during search setup" → log_event(WARN)
- Line 162: "Client disconnected before search execution" → log_event(WARN)
- Line 187: DEBUG statement → log_event(DEBUG) if logging_level == "debug"
- Line 223: "Stage 2 Progress" → log_event(INFO)
- Line 238: "Client disconnected before Stage 3" → log_event(WARN)
- Line 251: "Error waiting for title task" → log_event(ERROR)
- Line 280, 287, 289: Stream cancel messages → log_event(INFO/WARN)
- Line 292: "Stream error" → log_event(ERROR)
- Line 646: "Error fetching models" → log_event(ERROR)

REFERENCE: Use spec lines 1154-1167 for migration patterns.

VERIFICATION: Run `uv run python -m backend.main` - should start with no errors and no print statements.
AFTER DONE: Update spec Progress Tracker - change Step 5 status from ⬜ to ✅
```

### Step 6: Add Log Viewer API Endpoints

```
Implement Step 6 from docs/spec-add-logs-feature.md

STEP 6: Add Log Viewer API Endpoints
FILE: backend/main.py (MODIFY)
TIME: 25 min

TASKS (from spec lines 1444-1452):
1. Add 3 logging fields to UpdateSettingsRequest class (around line 308-355)
2. Add 3 logging fields to GET `/api/settings` response dict (around line 364-414)
3. Add validation for logging fields in PUT `/api/settings` (around line 560-613)
4. Add GET `/api/logs/recent` endpoint (after line 850)
5. Add GET `/api/logs/files` endpoint (after line 850)
6. Add GET `/api/logs/file/{filename}` endpoint (after line 850)
7. Add POST `/api/logs/client` endpoint (optional, after line 850)
8. Test all endpoints with curl/httpie

ENDPOINTS TO ADD:
- GET /api/logs/recent?limit=50 - returns recent errors from buffer
- GET /api/logs/files - returns list of log files with metadata
- GET /api/logs/file/{filename}?lines=100 - returns content of log file
- POST /api/logs/client - accepts frontend log messages

SECURITY:
- Validate filename parameter to prevent path traversal (reject .., /, \)
- Use lazy imports to avoid circular dependencies

REFERENCE: See spec lines 676-753 for exact code.

VERIFICATION: Run `uv run python -m backend.main` - should start with all new endpoints.
Test: curl http://localhost:8001/api/logs/recent (should return {"errors": []})
AFTER DONE: Update spec Progress Tracker - change Step 6 status from ⬜ to ✅
```

### Step 7: Add Logging Calls to Council

```
Implement Step 7 from docs/spec-add-logs-feature.md

STEP 7: Add Logging Calls to Council
FILE: backend/council.py (MODIFY)
TIME: 25 min

TASKS (from spec lines 1473-1479):
1. Add lazy import: `from .error_logger import log_model_error, log_event`
2. Add logging calls in stage1_collect_responses() for errors
3. Add logging calls in stage2_collect_rankings() for errors
4. Add logging calls in stage3_synthesize_final() for errors
5. Add stage completion events for all 3 stages
6. Verify async/await context in each location

INTEGRATION POINTS:
- Stage 1: After error result is built (around line 160-167)
- Stage 2: After error result is built (around line 289-297)
- Stage 3: When error occurs (around line 408-415)
- Use asyncio.create_task() to log asynchronously if in async context

REFERENCE: See spec lines 1100-1152 for exact integration code.

VERIFICATION: Run `uv run python -m backend.main` - should start with no errors.
AFTER DONE: Update spec Progress Tracker - change Step 7 status from ⬜ to ✅
```

### Step 8: Update Settings Component

```
Implement Step 8 from docs/spec-add-logs-feature.md

STEP 8: Update Settings Component
FILE: frontend/src/components/Settings.jsx (MODIFY)
TIME: 45 min

TASKS (from spec lines 1533-1541):
1. Add 6 logging state variables (around line 68)
2. Add loadRecentErrors() function
3. Add viewLogFile() function
4. Add downloadLogFile() function
5. Update loadSettings() to load logging settings from API response
6. Update handleSave() to include logging settings in payload
7. Add sidebar nav button for "📋 Logs" section
8. Add {activeSection === 'logs' && (...)} section with all controls

STATE VARIABLES TO ADD:
- loggingEnabled, loggingLevel, loggingFolder
- recentErrors, logFiles, isLoadingLogs

FUNCTIONS TO ADD:
- loadRecentErrors(): loads errors and files from API
- viewLogFile(filename): opens log file content
- downloadLogFile(filename): triggers download

UI ELEMENTS:
- Enable Logging toggle
- Log Level dropdown (3 options: errors_only, all, debug)
- Log Folder input
- Recent Errors viewer with refresh button
- Log Files list with view/download buttons

REFERENCE: See spec lines 777-880 for exact JSX code.

VERIFICATION: After done, frontend should compile without errors.
AFTER DONE: Update spec Progress Tracker - change Step 8 status from ⬜ to ✅
```

### Step 9: Update API Client

```
Implement Step 9 from docs/spec-add-logs-feature.md

STEP 9: Update API Client
FILE: frontend/src/api.js (MODIFY)
TIME: 15 min

TASKS (from spec lines 1554-1558):
1. Add getRecentLogs(limit = 50) function to api object
2. Add getLogFiles() function to api object
3. Add readLogFile(filename, lines = 100) function to api object
4. Add logToServer(level, message, data = {}) function to api object

WHERE: Add after getDefaultSettings() function (around line 253)

API FUNCTIONS:
- getRecentLogs: GET /api/logs/recent?limit={limit}
- getLogFiles: GET /api/logs/files
- readLogFile: GET /api/logs/file/{filename}?lines={lines}
- logToServer: POST /api/logs/client with {level, message, data}

REFERENCE: See spec lines 883-935 for exact code.

VERIFICATION: Functions should be callable from Settings.jsx component.
AFTER DONE: Update spec Progress Tracker - change Step 9 status from ⬜ to ✅
```

### Step 10: Add Log Viewer Styles

```
Implement Step 10 from docs/spec-add-logs-feature.md

STEP 10: Add Log Viewer Styles
FILE: frontend/src/components/Settings.css (MODIFY)
TIME: 20 min

TASKS (from spec lines 1572-1580):
1. Add .log-viewer-section styles
2. Add .log-viewer-header styles
3. Add .log-entries styles (max-height 300px, overflow-y auto, monospace)
4. Add .log-entry and variants (.error, .warn, .info)
5. Add .log-timestamp, .log-model, .log-type, .log-message styles
6. Add .log-empty styles
7. Add .log-files-section styles
8. Add .log-file-item and children styles

WHERE: Add at END of file

COLOR SCHEME:
- Error color: #f87171
- Warn color: #fbbf24
- Info color: #60a5fa
- Background: rgba(0, 0, 0, 0.2)
- Border: rgba(255, 255, 255, 0.1)
- Font: Monaco, Menlo, Courier New, monospace for logs
- Font size: 12px for log entries

REFERENCE: See spec lines 938-1098 for exact CSS code.

VERIFY: Run `cd frontend && npm run dev` - should compile without errors.
AFTER DONE: Update spec Progress Tracker - change Step 10 status from ⬜ to ✅
```

### Step 11: Test with NanoGPT

```
Execute Step 11 from docs/spec-add-logs-feature.md

STEP 11: Test with NanoGPT
TIME: 30 min (comprehensive testing)

TEST PROCEDURE (from spec lines 1588-1600):
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

VERIFICATION CHECKLIST (all must pass):
- [ ] Backend starts without import errors
- [ ] Frontend compiles without errors
- [ ] Enable logging toggle works
- [ ] Changing log level updates correctly
- [ ] Send message with models that succeed (logs with INFO in debug mode)
- [ ] Intentionally trigger errors (bad API key, invalid model) - logs appear
- [ ] Errors appear in "Recent Errors" viewer
- [ ] Log file created at data/logs/council_YYYY-MM-DD.log
- [ ] "Errors Only" level filters out INFO entries
- [ ] "All Events" level includes INFO entries
- [ ] "Debug" level includes raw responses
- [ ] Log file > 10MB creates rotated file (council_YYYY-MM-DD_1.log)
- [ ] Click refresh button reloads errors without page reload
- [ ] View log file opens content
- [ ] Download log file works correctly
- [ ] Logs survive application restart (persisted to file)
- [ ] Old logs cleaned up after retention period (7 days)

REFERENCE: See spec lines 1238-1278 for testing plan details.

AFTER DONE: Update spec Progress Tracker - change Step 11 status from ⬜ to ✅
```

### Step 12: Documentation

```
Execute Step 12 from docs/spec-add-logs-feature.md

STEP 12: Documentation
TIME: 20 min

TASKS (from spec lines 1625-1630):
1. Create docs/logging-guide.md with user documentation
2. Add logging section to main README.md
3. Document log file location and format
4. Document error types and meanings
5. Add troubleshooting section for common errors

DOCUMENTATION SHOULD INCLUDE:
- How to enable/disable logging
- Log levels explained (errors_only, all, debug)
- Where to find log files (data/logs/council_YYYY-MM-DD.log)
- Log file format and how to read it
- Error types and what they mean (rate_limit, auth_error, etc.)
- How to view logs in UI (Settings → Logs tab)
- Troubleshooting common issues
- Security: log files contain no API keys (sanitized)
- Retention policy (7 days automatic cleanup)

REFERENCE: See spec sections: Security (lines 1213-1223), Troubleshooting (lines 1754-1789), Alternative Approaches (lines 1675-1711)

AFTER DONE: Update spec Progress Tracker - change Step 12 status from ⬜ to ✅
```

---

## Quick Reference

| Step | File | What to Add | Time |
|------|------|-------------|------|
| 0 | Multiple | Audit existing logs | 20 min |
| 1 | `backend/error_logger.py` | NEW FILE - logging module + async locks | 40 min |
| 2 | `backend/providers/custom_openai.py` | `_parse_error_response()` method + name support | 35 min |
| 3 | `backend/council.py` | `get_provider_name()` helper | 10 min |
| 4 | `backend/settings.py` | 3 logging settings fields | 10 min |
| 5 | `backend/main.py` | Replace 12 print() statements | 25 min |
| 6 | `backend/main.py` | Settings + 4 API endpoints | 25 min |
| 7 | `backend/council.py` | Import + logging calls in stages | 25 min |
| 8 | `frontend/src/components/Settings.jsx` | Logs tab + UI + functions | 45 min |
| 9 | `frontend/src/api.js` | 4 API functions (including logToServer) | 15 min |
| 10 | `frontend/src/components/Settings.css` | Log viewer styles (monospace, colors) | 20 min |
| 11 | - | Comprehensive testing (17 checks) | 30 min |
| 12 | docs/ | User documentation + troubleshooting | 20 min |

**Total:** 4.7 hours | **Critical Path:** 1→2→3→7→8→11

---

## Usage Tips

1. **Copy the entire prompt** including the code blocks
2. **Update progress markers** [✅/⬜] before using Continue/Resume prompts
3. **Always verify compilation** after backend (Step 7) and frontend (Step 11)
4. **Check the spec file** if you need more details - it has full code snippets
5. **Update the spec's Progress Tracker** after each step for future reference
6. **Never skip pre-audit** (Step 0) when starting fresh

---

## Key Gotchas (from CLAUDE.md + new logging feature)

| Issue | Solution | Applies To |
|-------|----------|------------|
| Import errors in backend | Use relative imports: `from .settings import ...` | All backend steps |
| Backend won't start | Run from project root: `uv run python -m backend.main` | All backend verification |
| Port 8000 conflict | Backend uses port **8001**, not 8000 | Backend testing |
| React state bugs | Use spread operator for immutable updates | Step 8 |
| CORS errors | Frontend must be on localhost:5173 or :3000 | Step 11 |
| Code deleted by edit | Never use `// ...` placeholders - always full content | All file edits |
| **NEVER log API keys** | Sanitization happens automatically via _sanitize_dict() | All logging |
| Circular imports | Use lazy imports inside functions for error_logger | Steps 2, 5, 6, 7 |
| Async file corruption | Always use async with _file_lock before file writes | Step 1 |
| Wrong timezone | Always use datetime.now(timezone.utc), not naive datetime | Step 1 |
| Debug logs missing | Set logging_level to "debug" (not just "all") | Testing |
| Path traversal attack | Reject paths with .., /, or \\ in filename parameter | Step 6 |
| Log file size blow-up | Size rotation code in get_log_path() enforces 10MB max | Step 1 |
| Frontend console clutter | Use logToServer() to send errors to backend logs | Step 9 |

**Critical for this feature:**
- **ASYNC EVERYWHERE**: File operations must use async with locks (see Step 1)
- **SANITIZATION**: 17 patterns automatically checked - never bypass
- **UTC TIMESTAMPS**: All logs must use timezone.utc for consistency
- **FALLBACK LOGGING**: If main logging fails, check data/logs/fallback.log
- **SIZE ROTATION**: Check log file size before write, rotate if > 10MB
- **CUSTOM ENDPOINT NAMES**: Use get_provider_name() to get correct name (Step 3)
- **DEBUG MODE**: Raw responses only logged when logging_level == "debug"
- **STAGE EVENTS**: Log stage completions with structured data for analytics

---

**Last Updated:** 2026-01-04 (matches spec revision)
