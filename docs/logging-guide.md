# Logging System Guide

**Created:** 2026-01-06  
**Status:** Active Feature

---

## Overview

LLM Council Plus includes a comprehensive logging system to help you debug model errors, especially when using aggregator services like NanoGPT or custom OpenAI-compatible endpoints.

## Enabling Logging

1. Navigate to **Settings** → **Logs** tab
2. Toggle **Enable Logging** to on
3. Select your **Log Level**:
   - **Errors Only** - Log only model errors (default)
   - **All Events** - Log errors + stage completions + client events
   - **Debug** - Log everything including raw API responses

## Log File Location

Logs are stored in the `data/logs/` directory:

```
data/logs/
├── council_2026-01-06.log      # Today's logs
├── council_2026-01-05.log      # Previous day
├── council_2026-01-05_1.log    # Rotated (previous day, file 1)
└── fallback.log                 # Emergency logs if main logging fails
```

## Log File Format

```
2026-01-06 14:30:45 | ERROR | [NanoGPT] [custom:gpt-4-turbo] RATE_LIMIT: Rate limit exceeded.
2026-01-06 14:30:50 | INFO  | [stage1_complete] {"total": 8, "success": 6, "failed": 2}
2026-01-06 14:30:52 | WARN  | [client_disconnect] {"stage": "web_search"}
```

**Format:** `TIMESTAMP | LEVEL | [CONTEXT] MESSAGE`

## Log Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| **ERROR** | Model failures, API errors, exceptions | Debugging failed requests |
| **WARN** | Client disconnects, prompt formatting issues | Monitoring connection issues |
| **INFO** | Stage completions, successful operations | General progress tracking |
| **DEBUG** | Raw API responses, verbose details | Deep troubleshooting |

## Error Types

| Error Type | Description | User Action |
|------------|-------------|-------------|
| `rate_limit` | Too many requests (HTTP 429) | Wait and retry, or reduce council size |
| `auth_error` | Invalid API key (HTTP 401) | Check API key in settings |
| `forbidden` | Access denied (HTTP 403) | Check account permissions/quota |
| `model_not_found` | Model doesn't exist (HTTP 404) | Check model name spelling |
| `quota_exceeded` | Insufficient balance (HTTP 402/403) | Top up your account |
| `service_unavailable` | Provider overloaded (HTTP 503) | Wait and retry |
| `server_error` | Provider internal error (HTTP 5xx) | Wait and retry |
| `timeout` | Request timed out | Check network or increase timeout |
| `context_length` | Input too long (HTTP 400) | Reduce input size |
| `validation_error` | Invalid request format (HTTP 422) | Check input format |
| `empty_response` | Model returned no content | Retry or try different model |
| `ranking_error` | Peer ranking failed | Check model availability |
| `synthesis_error` | Chairman synthesis failed | Check chairman model |

## Log Rotation

- **Size Limit:** 10MB per file
- **Rotation:** When a log file exceeds 10MB, it creates `council_YYYY-MM-DD_N.log`
- **Retention:** Logs are kept for 7 days
- **Cleanup:** Automatic cleanup runs hourly

## Viewing Logs in UI

### Recent Errors Tab

The **Recent Errors** section shows the last 100 errors from memory:
- Timestamp
- Model name
- Provider
- Error type (color-coded badge)
- Error message

### Log Files Tab

Browse and view log files:
- **View** - Click a file to see its contents (last 100 lines)
- **Download** - Click the download button (⬇) to save the file
- **Refresh** - Click refresh to reload the file list

## Security

### API Key Protection

All logs automatically sanitize sensitive data using these patterns:
- `api_key`, `apikey`, `secret`, `token`
- `password`, `credential`, `authorization`
- And 17+ more patterns

API keys are **never** written to log files.

### Path Traversal Protection

The log viewer prevents path traversal attacks by:
- Rejecting filenames containing `..`, `/`, or `\`
- Validating file paths are within the log directory

## Troubleshooting

### "No logs are being created"

1. Check `data/logs/` folder exists
2. Verify **Enable Logging** is toggled on
3. Check `data/logs/fallback.log` for errors

### "Recent errors not showing in UI"

1. Check browser console for errors
2. Verify `/api/logs/recent` endpoint works
3. Check if buffer exceeded 100 entries (oldest are removed)

### "Log files growing too large"

1. Verify size rotation code is active
2. Check for rapid error generation
3. Set log level to **Errors Only**

### "Sensitive data in logs"

1. Immediately rotate your API keys
2. Report the issue
3. Check if your API key format matches sanitization patterns

## Backend Logs

For more detailed debugging, check the backend console output:

```bash
uv run python -m backend.main
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/logs/recent` | GET | Get recent errors from buffer |
| `/api/logs/files` | GET | List available log files |
| `/api/logs/file/{filename}` | GET | Read log file content |
| `/api/logs/client` | POST | Submit client-side logs |

## Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `logging_enabled` | `false` | Enable/disable logging |
| `logging_level` | `errors_only` | Log verbosity: errors_only, all, debug |
| `logging_folder` | `data/logs` | Log file directory |

---

**Note:** Logs are stored in the `data/` folder which is git-ignored to protect your API keys and privacy.
