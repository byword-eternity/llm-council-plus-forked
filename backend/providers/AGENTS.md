# PROVIDERS GUIDE

## OVERVIEW
LLM Provider implementations. Inherits from `LLMProvider`.

## IMPLEMENTATION CHECKLIST
To add a new provider:
1.  Create `backend/providers/{name}.py`.
2.  Inherit `class {Name}Provider(LLMProvider)`.
3.  Implement `async def chat(...)`.
4.  Add to `PROVIDERS` dict in `backend/council.py`.
5.  Add icon in `frontend/src/assets/icons/`.

## BASE CLASS
`backend/providers/base.py`:
- `stream_chat`: Generator for token streaming.
- `chat`: Non-streaming response.

## PROVIDER DETAILS
- **OpenRouter**: `openrouter.py` - Primary cloud gateway.
- **Ollama**: `ollama.py` - Local models.
- **Groq**: `groq.py` - High-speed inference.
- **Custom**: `custom_openai.py` - Generic OpenAI-compatible endpoint.
- **Direct**: `openai.py`, `anthropic.py`, `google.py`, `mistral.py`, `deepseek.py`.

## GOTCHAS
- **Prefixes**: Routing depends on `model_id` prefix (e.g., `ollama:`).
- **Streaming**: Must yield chunks compatible with SSE format.
- **Custom**: `custom_openai.py` handles generic OpenAI-compatible endpoints.
