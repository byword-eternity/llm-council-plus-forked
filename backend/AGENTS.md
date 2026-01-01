# BACKEND GUIDE

## OVERVIEW
FastAPI application serving the deliberation engine.
**Python 3.10+**. Monolithic structure in `main.py` with modular providers.

## STRUCTURE
```
backend/
├── providers/        # Provider implementations
├── council.py        # Stage 1-3 logic & routing
├── main.py           # API Routes + SSE Event Generator
├── prompts.py        # System prompts
├── search.py         # Search tools (DDG + Jina)
└── storage.py        # JSON file persistence
```

## KEY PATTERNS
- **Execution**: `uv run python -m backend.main` (Run from PROJECT ROOT).
- **Imports**: `from .module import X` (Relative only).
- **Async**: Heavy use of `asyncio.gather` for parallel model queries.
- **SSE**: `event_generator` in `main.py` drives the frontend state.

## COMPLEXITY HOTSPOTS
| File | Issue | Advice |
|------|-------|--------|
| `main.py` | ~1000 lines | Contains ALL routes and schemas. Search carefully. |
| `council.py` | Regex parsing | Stage 2 parsing is fragile. Test changes against `parse_ranking_from_text`. |

## CRITICAL IMPLEMENTATION DETAILS
### Python Module Imports
**ALWAYS** use relative imports in backend modules:
```python
from .config import ...
from .council import ...
```
**NEVER** use absolute imports like `from backend.config import ...`.

### Streaming & Abort Logic
- Backend checks `request.is_disconnected()` inside loops.
- **Critical**: Always inject raw `Request` object into streaming endpoints (Pydantic models lack `is_disconnected()`).

## ANTI-PATTERNS
- **NO** `from backend...` imports.
- **NO** synchronous network calls (block the event loop).
- **NO** database schemas (uses flat JSON in `data/`).
