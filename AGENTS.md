# AGENTS.md

**Generated:** 2026-01-01T21:56:43  
**Commit:** b04b983  
**Branch:** main

## OVERVIEW

3-stage LLM council deliberation system. FastAPI backend (Python 3.10) + React 19 frontend. Models answer → peer-rank → chairman synthesizes.

## USER CONTEXT

**Owner is NOT a programmer.** This is a forked project from GitHub. AI agents should:

| Behavior | Why |
|----------|-----|
| **Be proactive** | Don't wait for detailed instructions - anticipate needs |
| **Provide complete solutions** | No partial code, no "implement X here" placeholders |
| **Explain in simple terms** | Avoid jargon; when technical terms needed, explain briefly |
| **Make technical decisions** | Owner trusts your judgment on implementation details |
| **Test before declaring done** | Verify changes work; don't assume |
| **Handle errors autonomously** | If something breaks, fix it without asking |
| **Document changes** | Brief comments explaining what was changed and why |

**When in doubt**: Do more, not less. Complete the task fully rather than asking for clarification on technical details.

**Language**: ALWAYS use English in all responses and code comments, even if the user writes in Indonesian or other languages.

## STRUCTURE

```
llm-council-plus/
├── backend/              # FastAPI app, SSE streaming
│   ├── providers/        # LLM provider implementations (9 providers)
│   ├── council.py        # Stage orchestration, provider routing
│   ├── main.py           # API endpoints, SSE event generator
│   ├── search.py         # Web search (DDG/Tavily/Brave + Jina)
│   ├── settings.py       # JSON-persisted config
│   └── storage.py        # Conversation persistence
├── frontend/src/
│   ├── components/       # 22 components (flat structure)
│   │   ├── Stage1.jsx    # Individual model responses (tabs)
│   │   ├── Stage2.jsx    # Peer rankings + leaderboard
│   │   ├── Stage3.jsx    # Chairman synthesis
│   │   └── settings/     # Provider/Council/Prompt config
│   ├── App.jsx           # SSE handling, conversation state
│   └── api.js            # Backend client
├── data/                 # Runtime storage (git-ignored)
│   ├── settings.json     # API keys (plaintext!)
│   └── conversations/    # Chat history
├── start.sh              # Launch script (backend + frontend)
└── CLAUDE.md             # Detailed reference (read this)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new LLM provider | `backend/providers/` | Inherit `LLMProvider` from base.py, add to PROVIDERS dict in council.py |
| Modify deliberation flow | `backend/council.py` | Stage 1/2/3 orchestration |
| Change API routes | `backend/main.py` | All routes in single file |
| Edit system prompts | `backend/prompts.py` | Stage 1/2/3 default prompts |
| Add UI component | `frontend/src/components/` | CSS colocated with JSX |
| Handle SSE events | `frontend/src/App.jsx` | Giant switch statement in handleSendMessage |
| Modify model selection | `frontend/src/components/settings/CouncilConfig.jsx` | |

## CONVENTIONS

### Backend (Python)
- **Imports**: Relative ONLY (`from .config import ...`). Never `from backend.`
- **Execution**: `uv run python -m backend.main` from root. Never `cd backend && python main.py`
- **Port**: 8001 (NOT 8000)

### Frontend (React)
- **State**: Immutable updates via spread operator. StrictMode runs effects twice.
- **Markdown**: Wrap in `.markdown-content` div, ensure string type
- **Tab bounds**: Check `activeTab < responses.length` during streaming

### Model ID Format
```
prefix:model_name
  openrouter:anthropic/claude-sonnet-4
  ollama:llama3.1:latest
  groq:llama3-70b-8192
  openai:gpt-4.1
  anthropic:claude-sonnet-4
  custom:my-model
```
Routing: `council.py:get_provider_for_model()` parses prefix → dispatches to provider.

## ANTI-PATTERNS

| NEVER | Why |
|-------|-----|
| Absolute imports in backend | Breaks module resolution |
| `cd backend && python main.py` | Breaks relative imports |
| Mutate React state directly | StrictMode issues, lost updates |
| Use port 8000 | Reserved, causes conflicts |
| Commit `data/` directory | Contains plaintext API keys |
| Type suppress (`as any`, `@ts-ignore`) | Masks real errors |

## COMMANDS

```bash
# Start both (recommended)
./start.sh

# Manual
uv run python -m backend.main        # Backend: localhost:8001
cd frontend && npm run dev           # Frontend: localhost:5173

# Install deps
uv sync                              # Backend
cd frontend && npm install           # Frontend

# Test Ollama
curl http://localhost:11434/api/tags
```

## GOTCHAS

1. **Streaming abort**: Backend checks `request.is_disconnected()` inside loops. Inject raw `Request` object, not Pydantic model.
2. **Stage 2 parsing**: Expects "FINAL RANKING:" header. Fallback regex for "Response X" patterns.
3. **Icon detection order**: Check `custom:` prefix BEFORE name patterns (models may contain "claude", "gpt").
4. **node_modules arch**: Delete and reinstall when switching Intel/Apple Silicon.
5. **Jina 451 errors**: Many news sites block AI scrapers. Use Tavily/Brave or set full_content_results=0.

## COMPLEXITY HOTSPOTS

| File | Lines | Notes |
|------|-------|-------|
| Settings.jsx | 1492 | 5-section settings UI |
| backend/main.py | 951 | SSE event generator, all routes |
| App.jsx | 705 | Central state, SSE handling |
| council.py | 588 | Stage orchestration |
| search.py | 527 | Multi-provider search + Jina |

## SEE ALSO

- **CLAUDE.md**: Detailed architecture, implementation patterns, data flow diagrams
- **README.md**: User-facing docs, feature list, setup guide
