# Implementation Prompts for Spec Documents

This file contains ready-to-use prompts for AI agents to implement features from specification documents.

**Target Spec:** `docs/spec-add-logs-feature.md`

---

## Required Context Files

Before implementing, the AI should read these files:

| File | Purpose |
|------|---------|
| `docs/spec-add-logs-feature.md` | Full implementation spec with code snippets |
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
1. docs/spec-add-logs-feature.md - Full implementation spec with code snippets
2. CLAUDE.md - Project architecture, conventions, critical implementation details
3. AGENTS.md - Quick reference for structure and anti-patterns

WHAT THIS FEATURE DOES:
- Adds error visibility for LLM Council Plus (especially NanoGPT endpoint users)
- Logs model errors to files and displays them in Settings UI
- Toggle on/off with "errors only" or "all events" level

INSTRUCTIONS:
1. Read the spec document completely first
2. Follow the Implementation Steps section (lines 893-1238)
3. Implement in order: Steps 1→2→3→4→5→6→6b→7
4. Update the Progress Tracker in the spec after each step (change ⬜ to ✅)
5. Test backend compiles after Step 5: `uv run python -m backend.main`
6. Test frontend compiles after Step 7: `cd frontend && npm run dev`

DO:
- Use the exact code snippets from the spec's Technical Design section
- Follow existing patterns in each file
- Create data/logs/ folder if needed

DO NOT:
- Skip steps or do them out of order
- Use absolute imports in backend (use `from .module import ...`)
- Commit API keys or log files
```

---

## Continue Implementation Prompt

Use this when resuming work (some steps already completed).

```
Continue implementing the logging feature from docs/spec-add-logs-feature.md

CONTEXT FILES:
- docs/spec-add-logs-feature.md - Implementation spec
- CLAUDE.md - Project conventions (read "Critical Implementation Details" section)

CURRENT PROGRESS:
- Step 1 (error_logger.py): [✅/⬜]
- Step 2 (custom_openai.py): [✅/⬜]
- Step 3 (settings.py): [✅/⬜]
- Step 4 (main.py): [✅/⬜]
- Step 5 (council.py): [✅/⬜]
- Step 6 (Settings.jsx): [✅/⬜]
- Step 6b (api.js): [✅/⬜]
- Step 7 (Settings.css): [✅/⬜]
- Step 8 (Testing): [✅/⬜]
- Step 9 (.gitignore): [✅/⬜]

INSTRUCTIONS:
1. Read the spec document to understand context
2. Check the Progress Tracker section (lines 893-1238) for current status
3. Continue from the next pending step
4. Update Progress Tracker in the spec after completing each step
5. If you encounter errors, fix them before moving on

VERIFICATION:
- After Step 5: Run `uv run python -m backend.main` - should start without import errors
- After Step 7: Run `cd frontend && npm run dev` - should compile without errors
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
3. Check if Settings.jsx has "logs" section

THEN: Read the spec and identify which steps are done based on:
- Step 1 done if: backend/error_logger.py exists with log_model_error() function
- Step 2 done if: backend/providers/custom_openai.py has _parse_error_response() method
- Step 3 done if: backend/settings.py has logging_enabled field
- Step 4 done if: backend/main.py has /api/logs/recent endpoint
- Step 5 done if: backend/council.py imports from error_logger
- Step 6 done if: frontend/src/components/Settings.jsx has activeSection === 'logs'
- Step 6b done if: frontend/src/api.js has getRecentLogs() function
- Step 7 done if: frontend/src/components/Settings.css has .log-viewer-section class

FINALLY: 
1. Update the Progress Tracker in the spec to reflect actual state
2. Continue from the first incomplete step
3. Follow the spec's code snippets exactly
4. Verify compilation after backend steps (5) and frontend steps (7)
```

---

## Single Step Prompts

Use these when you want to implement just one step at a time.

### Step 1: Create Error Logger Module

```
Implement Step 1 from docs/spec-add-logs-feature.md

STEP 1: Create Error Logger Module
FILE: backend/error_logger.py (NEW FILE)

TASKS (from spec lines 908-927):
1. Create new file backend/error_logger.py
2. Implement cleanup_old_logs() function (FR-7)
3. Implement get_log_path() function (call cleanup inside)
4. Implement log_model_error() function
5. Implement log_event() function
6. Implement get_recent_errors() function
7. Implement get_log_files() function
8. Implement read_log_file() function
9. Add _recent_errors in-memory buffer (max 100 items)

REFERENCE: See spec lines 353-521 for exact code to use (including cleanup logic).

AFTER DONE: Update spec Progress Tracker - change Step 1 status from ⬜ to ✅
```

### Step 2: Enhanced Error Parsing

```
Implement Step 2 from docs/spec-add-logs-feature.md

STEP 2: Enhanced Error Parsing for Custom Endpoint
FILE: backend/providers/custom_openai.py (MODIFY)

TASKS (from spec lines 930-951):
1. Add `import json` at top of file
2. Add _parse_error_response() method after _get_config() method
3. Update error handling in query() method (around line 49-53)
4. Update exception handling (around line 59-60)
5. Import and call log_model_error() when errors occur

REFERENCE: See spec lines 231-333 for exact code to use.

VERIFY: Run `uv run python -m backend.main` - should start without import errors.
AFTER DONE: Update spec Progress Tracker - change Step 2 status from ⬜ to ✅
```

### Step 3: Add Logging Settings

```
Implement Step 3 from docs/spec-add-logs-feature.md

STEP 3: Add Logging Settings
FILE: backend/settings.py (MODIFY)

TASKS (from spec lines 955-970):
1. Add `logging_enabled: bool = False` to Settings class
2. Add `logging_level: str = "errors_only"` to Settings class
3. Add `logging_folder: str = "data/logs"` to Settings class

WHERE: Add these 3 fields at the end of the Settings class, before the class ends.

REFERENCE: See spec lines 523-537 for exact code pattern.

AFTER DONE: Update spec Progress Tracker - change Step 3 status from ⬜ to ✅
```

### Step 4: Add Log Viewer API Endpoints

```
Implement Step 4 from docs/spec-add-logs-feature.md

STEP 4: Add Log Viewer API Endpoints
FILE: backend/main.py (MODIFY)

TASKS (from spec lines 974-999):
1. Add logging_enabled, logging_level, logging_folder to UpdateSettingsRequest class (around line 355)
2. Add logging fields to GET /api/settings response dict (around line 414)
3. Add validation for logging fields in PUT /api/settings (around line 560)
4. Add GET /api/logs/recent endpoint (after line 850)
5. Add GET /api/logs/files endpoint (after line 850)
6. Add GET /api/logs/file/{filename} endpoint (after line 850)

REFERENCE: See spec lines 539-602 for exact code to use.

VERIFY: Run `uv run python -m backend.main` - should start without errors.
AFTER DONE: Update spec Progress Tracker - change Step 4 status from ⬜ to ✅
```

### Step 5: Add Logging Calls to Council

```
Implement Step 5 from docs/spec-add-logs-feature.md

STEP 5: Add Logging Calls to Council
FILE: backend/council.py (MODIFY)

TASKS (from spec lines 1003-1025):
1. Add import at top: `from .error_logger import log_model_error, log_event`
2. Create helper function: `def get_provider_name(model_id: str) -> str`
3. Add log_model_error() call in stage1_collect_responses() for errors
4. Add log_model_error() call in stage2_collect_rankings() for errors
5. Add log_model_error() call in stage3_synthesize_final() for errors
6. (Optional) Add log_event() calls for stage completion events

REFERENCE: See spec lines 797-838 for exact code patterns.

VERIFY: Run `uv run python -m backend.main` - should start without import errors.
AFTER DONE: Update spec Progress Tracker - change Step 5 status from ⬜ to ✅
```

### Step 6: Update Settings Component

```
Implement Step 6 from docs/spec-add-logs-feature.md

STEP 6: Update Settings Component
FILE: frontend/src/components/Settings.jsx (MODIFY)

TASKS (from spec lines 1031-1091):
1. Add logging state variables (6 variables) around line 68
2. Add loadRecentErrors() function
3. Add viewLogFile() function
4. Update loadSettings() to load logging settings from API response
5. Update handleSave() to include logging settings in payload
6. Add sidebar nav button for "Logs" section (AFTER the 'import_export' button)
7. Add {activeSection === 'logs' && (...)} section (AFTER the import_export section block closes)

UI ELEMENTS TO ADD:
- Enable Logging toggle
- Log Level dropdown (conditional on enabled)
- Log Folder input (conditional on enabled)
- Recent Errors viewer with refresh button
- Log Files list with view buttons

REFERENCE: See spec lines 604-723 for exact JSX code.

AFTER DONE: Update spec Progress Tracker - change Step 6 status from ⬜ to ✅
```

### Step 6b: Update API Client

```
Implement Step 6b from docs/spec-add-logs-feature.md

STEP 6b: Update API Client
FILE: frontend/src/api.js (MODIFY)

TASKS (from spec lines 1095-1145):
1. Add getRecentLogs(limit = 50) function to api object
2. Add getLogFiles() function to api object
3. Add readLogFile(filename, lines = 100) function to api object

WHERE: Add after getDefaultSettings() function (around line 253)

REFERENCE: See spec lines 101-140 for exact code patterns.

AFTER DONE: Update spec Progress Tracker - change Step 6b status from ⬜ to ✅
```

### Step 7: Add Log Viewer Styles

```
Implement Step 7 from docs/spec-add-logs-feature.md

STEP 7: Add Log Viewer Styles
FILE: frontend/src/components/Settings.css (MODIFY)

TASKS (from spec lines 1149-1170):
1. Add .log-viewer-section styles
2. Add .log-viewer-header styles
3. Add .log-entries styles (max-height 300px, overflow-y auto)
4. Add .log-entry and .log-entry.error styles
5. Add .log-timestamp, .log-model, .log-type, .log-message styles
6. Add .log-empty styles
7. Add .log-files-section and .log-file-item styles

WHERE: Add at END of file

COLOR SCHEME:
- Error color: #f87171
- Info color: #60a5fa
- Background: rgba(0, 0, 0, 0.2)
- Border: rgba(255, 255, 255, 0.1)

REFERENCE: See spec lines 725-795 for exact CSS code.

VERIFY: Run `cd frontend && npm run dev` - should compile without errors.
AFTER DONE: Update spec Progress Tracker - change Step 7 status from ⬜ to ✅
```

### Step 8: Testing

```
Execute Step 8 from docs/spec-add-logs-feature.md

STEP 8: Test with NanoGPT

TEST PROCEDURE (from spec lines 1176-1200):
1. Start backend: `uv run python -m backend.main`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Go to Settings → Logs tab
5. Enable logging toggle
6. Set up NanoGPT as custom endpoint (if not already configured)
7. Select 8 models including some that might fail
8. Send a test message
9. Check if errors appear in UI and log file

VERIFICATION CHECKLIST:
- [ ] Backend starts without import errors
- [ ] Frontend compiles without errors
- [ ] Enable logging toggle works
- [ ] Log Level dropdown appears when enabled
- [ ] Send message - models respond
- [ ] Errors appear in "Recent Errors" viewer (if any models fail)
- [ ] Log file created at data/logs/council_YYYY-MM-DD.log
- [ ] "Errors Only" level filters out INFO entries
- [ ] "All Events" level includes INFO entries

AFTER DONE: Update spec Progress Tracker - change Step 8 status from ⬜ to ✅
```

### Step 9: Update .gitignore

```
Implement Step 9 from docs/spec-add-logs-feature.md

STEP 9: Update .gitignore
FILE: .gitignore (MODIFY)

NOTE: The .gitignore likely already has `data/` which covers `data/logs/`.

TASKS:
1. Check if .gitignore already has `data/` entry
2. If yes, Step 9 is already covered - mark as ⏭️ Skipped
3. If no, add `data/logs/` to .gitignore

VERIFY: Run `git status` - log files in data/logs/ should NOT appear.

AFTER DONE: Update spec Progress Tracker - change Step 9 status from ✅ or ⏭️
```

---

## Quick Reference

| Step | File | What to Add |
|------|------|-------------|
| 1 | `backend/error_logger.py` | NEW FILE - logging module |
| 2 | `backend/providers/custom_openai.py` | `_parse_error_response()` method |
| 3 | `backend/settings.py` | 3 logging fields |
| 4 | `backend/main.py` | Settings fields + 3 endpoints |
| 5 | `backend/council.py` | Import + logging calls |
| 6 | `frontend/src/components/Settings.jsx` | Logs tab + UI |
| 6b | `frontend/src/api.js` | 3 API functions |
| 7 | `frontend/src/components/Settings.css` | Log viewer styles |
| 8 | - | Testing |
| 9 | `.gitignore` | (likely already covered) |

---

## Usage Tips

1. **Copy the entire prompt** including the code blocks
2. **Update progress markers** [✅/⬜] before using Continue prompt
3. **Always verify compilation** after backend (Step 5) and frontend (Step 7)
4. **Check the spec file** if you need more details - it has full code snippets
5. **Update the spec's Progress Tracker** after each step for future reference

---

## Key Gotchas (from CLAUDE.md)

These are common mistakes to avoid during implementation:

| Issue | Solution |
|-------|----------|
| Import errors in backend | Use relative imports: `from .settings import ...` |
| Backend won't start | Run from project root: `uv run python -m backend.main` |
| Port 8000 conflict | Backend uses port **8001**, not 8000 |
| React state bugs | Use spread operator for immutable updates |
| CORS errors | Frontend must be on localhost:5173 or :3000 |
| Code deleted by edit | Never use `// ...` placeholders - always full content |

**Critical for this feature:**
- **NEVER log API keys** - sanitize all data before logging
- Provider error parsing must handle various JSON formats (OpenAI, NanoGPT, etc.)
- Use `from ..error_logger import ...` in providers folder (double dot for parent)
- Settings.jsx is 1492 lines - be careful with line numbers
