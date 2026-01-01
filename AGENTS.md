# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-01 22:00:00
**Branch:** main

## OVERVIEW
3-stage LLM council deliberation system. FastAPI backend (Python 3.10+) + React 19 frontend (Vite).
Models answer individually (Stage 1) → peer-rank anonymously (Stage 2) → chairman synthesizes (Stage 3).

## USER CONTEXT

**Owner is NOT a programmer.** This is a forked project. AI agents must follow these **STRICT** rules:

| Rule | Instruction | Why |
|------|-------------|-----|
| **NO PARTIAL CODE** | **NEVER** use `// ...`, `TODO`, or `<!-- rest of code -->`. | You cannot "fill in the blanks". Code must be copy-paste ready. |
| **Fix It Yourself** | If a command fails, analyze the error and try to fix it **immediately**. | Do not stop to ask permission for standard fixes. |
| **Verify & Prove** | After editing, run a quick check (e.g., `grep`, `ls`, or a test script). | Prove to the owner that your change was successful. |
| **Explain "Why"** | Explain the *impact* of changes, not just the technical details. | Example: "I increased the timeout so large models won't fail," not "Set timeout to 60s." |
| **Protect Data** | **NEVER** overwrite `data/` or `.env` files without checking. | Preserves the owner's API keys and settings. |

**Golden Rule**: Treat this as a "Black Box" for the user. They care about the **result**, not the implementation.

**Language**: ALWAYS use English.

## STRUCTURE
```
llm-council-plus/
├── backend/              # FastAPI app (Port 8001), SSE streaming
│   ├── providers/        # LLM implementations (OpenRouter, Ollama, etc.)
│   ├── main.py           # Monolithic entry point (Routes + SSE)
│   └── council.py        # Core deliberation logic
├── frontend/             # React 19 + Vite
│   └── src/
│       ├── components/   # Flat UI components (22+ files)
│       └── App.jsx       # "God Mode" state + SSE handler
├── data/                 # Runtime storage (git-ignored)
└── start.sh              # Unified launch script
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add LLM Provider** | `backend/providers/` | Inherit `LLMProvider`, add to `council.py` |
| **Modify Logic** | `backend/council.py` | Stage 1/2/3 orchestration flow |
| **Change API** | `backend/main.py` | All routes + SSE generator in one file |
| **Edit UI** | `frontend/src/components/` | Styles colocated with JSX |
| **Handle SSE** | `frontend/src/App.jsx` | Main event switch statement |
| **Config/Keys** | `data/settings.json` | Plaintext storage (NEVER commit) |

## CONVENTIONS
### Backend (Python)
- **Execution**: `uv run python -m backend.main` (from root).
- **Imports**: RELATIVE ONLY (`from .config import ...`).
- **Port**: **8001** (8000 is reserved/conflict-prone).
- **Search**: `yake` used for keyword extraction before querying.

### Frontend (React)
- **State**: Immutable updates (`[...prev, new]`). StrictMode = double effects.
- **Markdown**: Wrap in `<div className="markdown-content">`.
- **Stream Safety**: Check `activeTab < responses.length`.

### Model IDs
Format: `prefix:model_name`
- `openrouter:anthropic/claude-3`
- `ollama:llama3`
- `custom:my-model`
- `groq:mixtral-8x7b`

## ANTI-PATTERNS (DO NOT DO)
1.  **Absolute Imports**: `from backend.x` breaks the module loading.
2.  **Port 8000**: Will conflict. Use 8001.
3.  **Partial Code**: Never leave `// ... implement here`. Write full solutions.
4.  **Type Suppression**: No `as any` or `@ts-ignore`.
5.  **Commit Data**: `data/` must remain git-ignored.

## COMMANDS
```bash
# Start All
./start.sh

# Backend Only (Manual)
uv run python -m backend.main

# Frontend Only (Manual)
cd frontend && npm run dev
```

## DATA FLOW
```
User Query (+ optional web search)
    ↓
[Web Search: DuckDuckGo/Tavily/Brave + Jina Reader]
    ↓
Stage 1: Parallel queries → Stream individual responses
    ↓
Stage 2: Anonymize → Parallel peer rankings → Parse rankings
    ↓
Calculate aggregate rankings
    ↓
Stage 3: Chairman synthesis → Stream final answer
    ↓
Save conversation (stage1, stage2, stage3 only)
```

## EXECUTION MODES
- **Chat Only**: Stage 1 only (quick responses)
- **Chat + Ranking**: Stages 1 & 2 (peer review without synthesis)
- **Full Deliberation**: All 3 stages (default)

## WEB SEARCH
- **Providers**: DuckDuckGo (free), Tavily (API), Brave (API)
- **Full Content**: Jina Reader (`https://r.jina.ai/{url}`) fetches article text.
- **Budget**: 25s timeout per article, 60s total. Falls back to summary if failed.
- **Query Processing**: Uses `YAKE` to extract keywords from long prompts.

## TESTING & DEBUGGING
```bash
# Check Ollama models
curl http://localhost:11434/api/tags

# Test custom endpoint
curl https://your-endpoint.com/v1/models -H "Authorization: Bearer $API_KEY"
```

## DESIGN PRINCIPLES
- **Graceful Degradation**: Single model failure doesn't block the council.
- **Transparency**: All raw outputs are inspectable.
- **De-anonymization**: Models see "Response A", users see real names.
- **Progress**: "X/Y completed" indicators during streaming.

## NOTES
- **Icons**: `custom:` prefix checked BEFORE name matching (avoids wrong logos).
- **Jina Reader**: Used for full-text search. May 451 on news sites.
- **Complexity**: `backend/main.py` (950+ lines) and `Settings.jsx` (1500+ lines) are huge.
