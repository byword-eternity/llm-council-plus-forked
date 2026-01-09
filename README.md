# LLM Council Plus

![LLM Council Plus](header.png)

> **Collective AI Intelligence** — Instead of asking one LLM, convene a council of AI models that deliberate, peer-review, and synthesize the best answer.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What is LLM Council Plus?

Instead of asking a single LLM (like ChatGPT or Claude) for an answer, **LLM Council Plus** assembles a council of multiple AI models that:

1. **Independently answer** your question (Stage 1)
2. **Anonymously peer-review** each other's responses (Stage 2)
3. **Synthesize a final answer** through a Chairman model (Stage 3)

The result? More balanced, accurate, and thoroughly vetted responses that leverage the collective intelligence of multiple AI models.

<p align="center">
  <div align="center">
    <a href="https://www.youtube.com/watch?v=HOdyIyccOCE" target="_blank">
      <img src="https://img.youtube.com/vi/HOdyIyccOCE/hqdefault.jpg" alt="LLM Council Plus Long Demo" width="48%">
    </a>
    <a href="https://www.youtube.com/watch?v=NUmQFGAwD3g" target="_blank">
      <img src="https://img.youtube.com/vi/NUmQFGAwD3g/hqdefault.jpg" alt="LLM Council Plus Short Demo" width="48%">
    </a>
  </div>
</p>

---

## About This Fork

This fork builds upon **[llm-council-plus](https://github.com/jacob-bd/llm-council-plus)** (which already had comprehensive multi-provider support, web search integration, and 3-stage deliberation) by focusing on production-hardening and developer experience improvements.

**Production Reliability Enhancements:**
- **Enhanced Logging System**: Comprehensive error tracking with UI, file management, and automatic rotation
- **Improved Error Handling**: Better graceful degradation and provider failure isolation
- **Enhanced Rate Limit Detection**: More accurate warnings and proactive alerts

**Developer Experience Improvements:**
- **Unified Launch Scripts**: `start.sh` and `start.ps1` with automatic network exposure
- **Cross-Platform Support**: Enhanced Windows compatibility with PowerShell scripts
- **AI-Assisted Development**: OpenCode integration for code quality and documentation

The core architecture and major features (multi-provider LLM support, web search, 3-stage deliberation) were already present in the upstream repository. This fork focuses on making the application more production-ready and developer-friendly.

The entire lineage remains inspired by **[Andrej Karpathy's llm-council](https://github.com/karpathy/llm-council)**, from experimental proof-of-concept to production-hardened application.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR QUESTION                             │
│            (+ optional web search for real-time info)            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 1: DELIBERATION                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐             │
│  │ Claude  │  │  GPT-4  │  │ Gemini  │  │  Llama  │  ...        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘             │
│       │            │            │            │                   │
│       ▼            ▼            ▼            ▼                   │
│  Response A   Response B   Response C   Response D               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 2: PEER REVIEW                          │
│  Each model reviews ALL responses (anonymized as A, B, C, D)     │
│  and ranks them by accuracy, insight, and completeness           │
│                                                                   │
│  Rankings are aggregated to identify the best responses          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 3: SYNTHESIS                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    CHAIRMAN MODEL                        │    │
│  │  Reviews all responses + rankings + search context       │    │
│  │  Synthesizes the council's collective wisdom             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│                      FINAL ANSWER                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture & Technical Implementation

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React 19)                       │
│  ┌──────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │ App.jsx      │  │ Settings    │  │ Stage Views     │   │
│  │ (SSE Handler)│  │ Management  │  │ (1/2/3)        │   │
│  └──────┬───────┘  └──────┬──────┘  └────────┬────────┘   │
│         │                  │                   │             │
│         ▼                  ▼                   ▼             │
│         └──────────────────┼───────────────────┘             │
│                            │                               │
└────────────────────────────┼─────────────────────────────────┘
                           │ HTTP/SSE
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                           │
│  ┌──────────┐  ┌─────────────┐  ┌─────────────────┐          │
│  │ Routes    │  │ Council     │  │ Provider Layer  │          │
│  │ + SSE     │  │ Orchestration│  │ (11 Providers)  │          │
│  └─────┬────┘  └──────┬──────┘  └────────┬────────┘          │
│        │             │                  │                     │
│        ▼             ▼                  ▼                     │
│  ┌──────────┐  ┌─────────────┐  ┌─────────────────┐          │
│  │ Storage   │  │ Search      │  │ Error Logger    │          │
│  │ (JSON)    │  │ Integration │  │ + Rotation     │          │
│  └───────────┘  └─────────────┘  └─────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Component Breakdown

**Backend Core (`backend/`)**
- **`main.py`** (950+ lines): FastAPI application with all routes and SSE streaming
- **`council.py`**: 3-stage orchestration logic with parallel async execution
- **`providers/`**: 11 LLM provider implementations with unified abstraction
- **`settings.py`**: Pydantic-based configuration management
- **`search.py`**: Multi-provider web search with YAKE keyword extraction
- **`error_logger.py`**: **NEW** - Comprehensive logging with rotation and sanitization

**Frontend Core (`frontend/src/`)**
- **`App.jsx`**: Main controller with SSE handling and conversation state (25KB)
- **`Settings.jsx`**: Comprehensive configuration UI (65KB, 5 sections)
- **`components/`**: 22+ specialized React components with "Midnight Glass" dark theme

**Key Frontend Components:**

| Component | Purpose | Key Feature |
|-----------|---------|-------------|
| `Stage1.jsx` | Individual model responses | Tabbed view with live streaming |
| `Stage2.jsx` | Peer rankings view | Aggregate scores, de-anonymization |
| `Stage3.jsx` | Chairman synthesis | Final answer with markdown |
| `StageTimer.jsx` | Real-time timing display | Green checkmark when complete |
| `ThinkBlockRenderer.jsx` | Think block rendering | Renders ` ` blocks (Anthropic) |
| `ChatInterface.jsx` | User input & controls | Web search toggle, mode selector |
| `CouncilGrid.jsx` | Visual council display | Provider icons, status indicators |
| `Settings.jsx` | Configuration UI | 5 tabs, 1500+ lines |
| `Sidebar.jsx` | Conversation list | Inline delete, quick switch |
| `SearchableModelSelect.jsx` | Model dropdown | Async loading, search filtering |
| `ExecutionModeToggle.jsx` | Mode switcher | Visual Chat Only/Chat+Ranking/Full |
| `SearchContext.jsx` | Search results | Web search context display |

**Frontend Styling:**
- **Theme**: "Midnight Glass" dark theme with glassmorphic effects
- **Primary Colors**: Blue (#3b82f6) and cyan (#06b6d4) gradients
- **Typography**: Merriweather 15px/1.7 for content, JetBrains Mono for errors

**Data Flow**
1. **Request Processing**: Frontend sends query + configuration
2. **Stage 1**: Parallel async queries to all enabled providers
3. **Stage 2**: Anonymized responses sent back for peer ranking
4. **Stage 3**: Chairman model receives all responses + rankings + search context
5. **Real-time Updates**: Server-Sent Events stream progress to UI

**Key Technical Features**
- **Async Parallel Execution**: All models queried simultaneously with graceful degradation
- **Provider Abstraction**: Base class enables easy addition of new LLM providers
- **SSE Streaming**: Real-time progress tracking with "X/Y completed" indicators
- **Error Isolation**: Single model failures don't block council deliberation
- **Configuration Persistence**: Comprehensive settings management with import/export
- **Enhanced Logging**: **NEW** - Comprehensive error tracking with UI viewer

---

## Features

### Multi-Provider Support

Mix and match models from different sources in your council:

| Provider             | Type  | Description                                                                                         |
| -------------------- | ----- | --------------------------------------------------------------------------------------------------- |
| **OpenRouter**       | Cloud | 100+ models via single API (GPT-4, Claude, Gemini, Mistral, etc.)                                   |
| **Ollama**           | Local | Run open-source models locally (Llama, Mistral, Phi, etc.)                                          |
| **Groq**             | Cloud | Ultra-fast inference for Llama and Mixtral models                                                   |
| **OpenAI Direct**    | Cloud | Direct connection to OpenAI API                                                                     |
| **Anthropic Direct** | Cloud | Direct connection to Anthropic API                                                                  |
| **Google Direct**    | Cloud | Direct connection to Google AI API                                                                  |
| **Mistral Direct**   | Cloud | Direct connection to Mistral API                                                                    |
| **DeepSeek Direct**  | Cloud | Direct connection to DeepSeek API                                                                   |
| **Custom Endpoint**  | Any   | Connect to any OpenAI-compatible API (Together AI, Fireworks, vLLM, LM Studio, GitHub Models, etc.) |

> **Note**: Comprehensive multi-provider support was already present in the upstream repository. This fork maintains the same architecture while adding production-hardening features.

<p align="center">
  <img width="600" alt="LLM API Keys Settings" src="https://github.com/user-attachments/assets/f9a5ec9d-17e8-4e78-ad40-0c21850f2823" />
</p>

### Execution Modes

<p align="center">
  <img width="818" alt="Execution Modes Toggle" src="https://github.com/user-attachments/assets/6f8dcc5b-6dbb-423a-8376-9f6b0ebb58ba" />
</p>

Choose how deeply the council deliberates:

| Mode                  | Stages       | Best For                                 |
| --------------------- | ------------ | ---------------------------------------- |
| **Chat Only**         | Stage 1 only | Quick responses, comparing model outputs |
| **Chat + Ranking**    | Stages 1 & 2 | See how models rank each other           |
| **Full Deliberation** | All 3 stages | Complete council synthesis (default)     |

> **Note**: 3-stage execution modes were already present in upstream repository. This fork maintains the same deliberation philosophy while adding production reliability enhancements.

### Web Search Integration

<p align="center">
  <img width="841" alt="Web Search Settings" src="https://github.com/user-attachments/assets/ae0d8f30-8a0d-4ae2-924b-3de75e9102e1" />
</p>

Ground your council's responses in real-time information:

| Provider         | Type    | Notes                                     |
| ---------------- | ------- | ----------------------------------------- |
| **DuckDuckGo**   | Free    | News search, no API key needed            |
| **Tavily**       | API Key | Purpose-built for LLMs, rich content      |
| **Brave Search** | API Key | Privacy-focused, 2,000 free queries/month |

**Full Article Fetching**: Uses [Jina Reader](https://jina.ai/reader) to extract full article content from top search results (configurable 0-10 results).

> **Note**: Multi-provider web search with Jina Reader integration was already present in upstream repository. This fork maintains the same search capabilities.

### Temperature Controls

<p align="center">
  <img width="586" alt="Temperature Controls" src="https://github.com/user-attachments/assets/3922edf6-99f5-4020-b80f-ba3c43a2ce9a" />
</p>

Fine-tune creativity vs consistency:

- **Council Heat**: Controls Stage 1 response creativity (default: 0.5)
- **Chairman Heat**: Controls final synthesis creativity (default: 0.4)
- **Stage 2 Heat**: Controls peer ranking consistency (default: 0.3)

<p align="center">
  <img width="849" alt="Council Configuration" src="https://github.com/user-attachments/assets/45880bee-1fec-4efc-b1cb-eceaabe071ff" />
</p>

### Additional Features

- **Live Progress Tracking**: See each model respond in real-time
- **Council Sizing**: adjust council size from 2 to 8
- **Abort Anytime**: Cancel in-progress requests
- **Conversation History**: All conversations saved locally
- **Customizable Prompts**: Edit Stage 1, 2, and 3 system prompts
- **Rate Limit Warnings**: Alerts when your config may hit API limits (when >5 council members)
- **"I'm Feeling Lucky"**: Randomize your council composition
- **Import & Export**: backup and share your favorite council configurations, system prompts, and settings

<p align="center">
  <img width="854" alt="Backup and Reset" src="https://github.com/user-attachments/assets/0e618bd4-02c2-47b2-b82b-c4900b7a4fdd" />
</p>

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **[uv](https://docs.astral.sh/uv/)** (Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/byword-eternity/llm-council-plus-forked.git
cd llm-council-plus-forked

# Install backend dependencies
uv sync

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Running the Application

**Option 1: Use the start script (recommended)**

```bash
# Linux/macOS
./start.sh
```

**Windows (PowerShell):**
```powershell
.\start.ps1
```

**PowerShell Script Features (118 lines):**
- ✅ **Auto-detection**: Automatically detects `uv` vs `python` availability
- ✅ **PID tracking**: Displays process IDs for debugging
- ✅ **Process tree cleanup**: Gracefully stops child processes (npm/node) on shutdown
- ✅ **Process monitoring**: Detects unexpected exits with exit code reporting
- ✅ **Error handling**: Comprehensive try-catch with user-friendly error messages
- ✅ **Graceful shutdown**: Ctrl+C handling with proper process termination

The PowerShell script handles both backend and frontend startup automatically with proper cleanup on exit.

**Option 2: Run manually**

Terminal 1 (Backend):

```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):

```bash
cd frontend
npm run dev
```

Then open **http://localhost:5173** in your browser.

### Network Access

The application is configured to be accessible from other devices on your local network.

**Using start.sh (automatic):**
The start script now exposes both frontend and backend on the network automatically. Just run `./start.sh` and access from any device.

**Access URLs:**

- **Local:** `http://localhost:5173`
- **Network:** `http://YOUR_IP:5173` (e.g., `http://192.168.1.100:5173`)

**Find your network IP:**

```bash
# macOS/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Or use hostname
hostname -I
```

**Manual setup (if not using start.sh):**

```bash
# Backend already listens on 0.0.0.0:8001

# Frontend with network access
cd frontend
npm run dev -- --host
```

The frontend automatically detects the hostname and connects to the backend on the same IP. CORS is configured to allow requests from any hostname on ports 5173 and 3000.

---

## Configuration

### First-Time Setup

On first launch, the Settings panel will open automatically. Configure at least one LLM provider:

1. **LLM API Keys** tab: Enter API keys for your chosen providers
2. **Council Config** tab: Select council members and chairman
3. **Save Changes**

### LLM API Keys

| Provider   | Get API Key                                                          |
| ---------- | -------------------------------------------------------------------- |
| OpenRouter | [openrouter.ai/keys](https://openrouter.ai/keys)                     |
| Groq       | [console.groq.com/keys](https://console.groq.com/keys)               |
| OpenAI     | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| Anthropic  | [console.anthropic.com](https://console.anthropic.com/)              |
| Google AI  | [aistudio.google.com/apikey](https://aistudio.google.com/apikey)     |
| Mistral    | [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys/)  |
| DeepSeek   | [platform.deepseek.com](https://platform.deepseek.com/)              |

**API keys are auto-saved** when you click "Test" and the connection succeeds.

### Ollama (Local Models)

1. Install [Ollama](https://ollama.com/)
2. Pull models: `ollama pull llama3.1`
3. Start Ollama: `ollama serve`
4. In Settings, enter your Ollama URL (default: `http://localhost:11434`)
5. Click "Connect" to verify

### Custom OpenAI-Compatible Endpoint

Connect to any OpenAI-compatible API:

1. Go to **LLM API Keys** → **Custom OpenAI-Compatible Endpoint**
2. Enter:
   - **Display Name**: e.g., "Together AI", "My vLLM Server"
   - **Base URL**: e.g., `https://api.together.xyz/v1`
   - **API Key**: (optional for local servers)
3. Click "Connect" to test and save

**Compatible services**: Together AI, Fireworks AI, vLLM, LM Studio, Ollama (if you prefer this method), GitHub Models (`https://models.inference.ai.azure.com/v1`), and more.

### Council Configuration

1. **Enable Model Sources**: Toggle which providers appear in model selection
2. **Select Council Members**: Choose 2-8 models for your council
3. **Select Chairman**: Pick a model to synthesize the final answer
4. **Adjust Temperature**: Use sliders for creativity control

**Tips:**

- Mix different model families for diverse perspectives
- Use faster models (Groq, Ollama) for large councils
- Free OpenRouter models have rate limits (20/min, 50/day)

### Search Providers

| Provider   | Setup                                                                                           |
| ---------- | ----------------------------------------------------------------------------------------------- |
| DuckDuckGo | Works out of the box, no setup needed                                                           |
| Tavily     | Get key at [tavily.com](https://tavily.com), enter in Search Providers tab                      |
| Brave      | Get key at [brave.com/search/api](https://brave.com/search/api/), enter in Search Providers tab |

**Search Query Processing:**

| Mode                      | Description                                          | Best For                                                                                                                                          |
| ------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direct** (default)      | Sends your exact query to the search engine          | Short, focused questions. Works best with semantic search engines like Tavily and Brave.                                                          |
| **Smart Keywords (YAKE)** | Extracts key terms from your prompt before searching | Very long prompts or multi-paragraph context that might confuse the search engine. Uses [YAKE](https://github.com/LIAAD/yake) keyword extraction. |

> **Tip:** Start with **Direct** mode. Only switch to **YAKE** if you notice search results are irrelevant when pasting long documents or complex prompts.

---

## Usage

### Basic Usage

1. Start a new conversation (+ button in sidebar)
2. Type your question
3. (Optional) Enable web search toggle for real-time info
4. Press Enter or click Send

### Understanding the Output

**Stage 1 - Council Deliberation**

- Tab view showing each model's individual response
- Live progress as models respond

**Stage 2 - Peer Rankings**

- Each model's evaluation and ranking of peers
- Aggregate scores showing consensus rankings
- De-anonymization reveals which model gave which response

**Stage 3 - Chairman Synthesis**

- Final, synthesized answer from the Chairman
- Incorporates best insights from all responses and rankings

### Keyboard Shortcuts

| Key           | Action            |
| ------------- | ----------------- |
| `Enter`       | Send message      |
| `Shift+Enter` | New line in input |

### Logging & Debugging

LLM Council Plus includes a comprehensive logging system to help debug model errors, especially when using custom endpoints.

#### Enable Logging

1. Go to **Settings** → **Logs** tab
2. Toggle **Enable Logging** on
3. Choose log level:
   - **Errors Only** - Log only model failures (default)
   - **All Events** - Log errors + stage completions
   - **Debug** - Log everything including raw API responses

#### View Logs

**Recent Errors (UI):**
- Shows last 100 errors from memory
- Color-coded error type badges (ERROR, WARN)
- Filterable by error type

**Log Files (UI + File System):**
- Browse and view logs in `data/logs/`
- Download logs for offline analysis
- Recent files appear in UI automatically

**API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/logs/recent` | GET | Get recent errors (last 100 in memory) |
| `/api/logs/files` | GET | List available log files |
| `/api/logs/file/{filename}` | GET | Read log file content |
| `/api/logs/client` | POST | Submit client-side logs |

#### Log Format

```
2026-01-06 14:30:45 | ERROR | [NanoGPT] [custom:gpt-4-turbo] RATE_LIMIT: Rate limit exceeded.
2026-01-06 14:30:50 | INFO  | [stage1_complete] {"total": 8, "success": 6, "failed": 2}
2026-01-06 14:30:52 | WARN  | [client_disconnect] {"stage": "web_search"}
```

**Format:** `TIMESTAMP | LEVEL | [CONTEXT] MESSAGE`

#### Error Types

| Error Type | HTTP Code | Description | User Action |
|------------|-----------|-------------|-------------|
| `rate_limit` | 429 | Too many requests | Wait and retry, or reduce council size |
| `auth_error` | 401 | Invalid API key | Check API key in settings |
| `forbidden` | 403 | Access denied | Check account permissions/quota |
| `model_not_found` | 404 | Model doesn't exist | Check model name spelling |
| `quota_exceeded` | 402/403 | Insufficient balance | Top up your account |
| `service_unavailable` | 503 | Provider overloaded | Wait and retry |
| `server_error` | 5xx | Provider internal error | Wait and retry |
| `timeout` | - | Request timed out | Check network or increase timeout |
| `context_length` | 400 | Input too long | Reduce input size |
| `validation_error` | 422 | Invalid request format | Check input format |
| `empty_response` | - | Model returned no content | Retry or try different model |
| `ranking_error` | - | Peer ranking failed | Check model availability |
| `synthesis_error` | - | Chairman synthesis failed | Check chairman model |

#### Log Features

- **Automatic rotation**: 10MB max per file, creates `council_YYYY-MM-DD_N.log`
- **7-day retention**: Automatic cleanup runs hourly
- **API key sanitization**: 20+ patterns prevent sensitive data logging
- **UTC timestamps**: Consistent time across all logs
- **Path traversal protection**: Security features prevent file access attacks
- **Fallback logging**: Emergency logging to `fallback.log` if main logging fails

#### Security

All logs automatically sanitize sensitive data using these patterns:
- `api_key`, `apikey`, `secret`, `token`
- `password`, `credential`, `authorization`
- And 15+ more patterns

**API keys are never written to log files.**

See [docs/logging-guide.md](docs/logging-guide.md) for complete logging documentation.

---

## AI-Assisted Development

This fork has been enhanced using **[OpenCode](https://github.com/OpenCode-Team/OpenCode)** with **[Oh-My-OpenCode](https://github.com/code-yeongyu/oh-my-opencode)** plugin harness, leveraging advanced AI agents for:

- **Multi-Agent Development**: Sisyphus orchestrates specialized AI agents (Oracle, Explore, Librarian, Frontend) for coordinated development
- **Intelligent Research**: Automated documentation analysis, GitHub code search, and official API exploration
- **Code Quality Enhancement**: LSP-guided refactoring, AST-aware transformations, and comprehensive testing
- **Documentation Generation**: AI-assisted README improvements, API documentation, and user guides

The **OpenCode ecosystem** enabled rapid enhancement of original codebase while maintaining code quality and architectural consistency. This represents a modern approach to AI-assisted software development where multiple specialized agents collaborate under intelligent coordination.

> **Note**: The `ultrawork` keyword activates the full multi-agent system for comprehensive development tasks.

---

## Tech Stack

### Backend (Python 3.10+)

| Component | Version | Purpose | Documentation |
|-----------|---------|---------|---------------|
| **FastAPI** | ≥0.115.0 | Web framework with automatic OpenAPI docs | [fastapi.tiangolo.com](https://fastapi.tiangolo.com/) |
| **Uvicorn** | ≥0.32.0 | ASGI web server with hot reload | [uvicorn.org](https://www.uvicorn.org/) |
| **Pydantic** | ≥2.9.0 | Data validation and settings management | [docs.pydantic.dev](https://docs.pydantic.dev/) |
| **httpx** | ≥0.27.0 | Async HTTP client with HTTP/2 support | [python-httpx.org](https://www.python-httpx.org/) |
| **ddgs** | ≥8.0.0 | DuckDuckGo search (free, no API key) | [GitHub](https://github.com/deedy5/duckduckgo_search) |
| **YAKE** | ≥0.4.8 | Keyword extraction for search queries | [liaad.github.io/yake](https://liaad.github.io/yake/) |
| **python-dotenv** | ≥1.0.0 | Environment variable management | [pypi.org/project/python-dotenv](https://pypi.org/project/python-dotenv/) |

### Frontend (React 19 + Vite)

| Component | Version | Purpose | Documentation |
|-----------|---------|---------|---------------|
| **React** | 19.2.0 | UI component library with hooks | [react.dev](https://react.dev/) |
| **Vite** | 7.2.4 | Build tool with instant HMR | [vite.dev](https://vite.dev/) |
| **React Markdown** | 10.1.0 | Markdown rendering for responses | [react-markdown.netlify.app](https://react-markdown.netlify.app/) |
| **React Select** | 5.10.2 | Advanced searchable dropdowns | [react-select.com](https://react-select.com/) |
| **ESLint** | 9.39.1 | JavaScript/JSX linting | [eslint.org](https://eslint.org/) |

### Package Managers

- **Python**: [uv](https://docs.astral.sh/uv/) - Ultra-fast Python package manager
- **JavaScript**: npm (Node.js 18+) - Standard Node package manager

### External Services

| Category | Providers | Notes |
|----------|-----------|-------|
| **LLM Providers** | OpenRouter, Ollama, Groq, OpenAI, Anthropic, Google, Mistral, DeepSeek, Custom endpoints | 9+ providers supported |
| **Search Providers** | DuckDuckGo (free), Tavily (API), Brave Search (API) | Configurable in Settings |
| **Content Extraction** | [Jina Reader](https://r.jina.ai/) | Full article content from URLs |

### Styling & Storage

- **Styling**: CSS with "Midnight Glass" dark theme (glassmorphic effects)
- **Storage**: JSON files in `data/` directory (git-ignored)
- **Logs**: Rotating log files in `data/logs/` (7-day retention)

---

## Data Storage

All data is stored locally in the `data/` directory:

```
data/
├── settings.json          # Your configuration (includes API keys)
└── conversations/         # Conversation history
    ├── {uuid}.json
    └── ...
```

**Privacy**: No data is sent to external servers except API calls to your configured LLM providers.

> **⚠️ Security Warning: API Keys Stored in Plain Text**
>
> In this build, **API keys are stored in clear text** in `data/settings.json`. The `data/` folder is included in `.gitignore` by default to prevent accidental exposure.
>
> **Important:**
>
> - **Do NOT remove `data/` from `.gitignore`** — this protects your API keys from being pushed to GitHub
> - If you fork this repo or modify `.gitignore`, ensure `data/` remains ignored
> - Never commit `data/settings.json` to version control
> - If you accidentally expose your keys, rotate them immediately at each provider's dashboard

---

## Troubleshooting

### Common Issues

**"Failed to load conversations"**

- Backend might still be starting up
- App retries automatically (3 attempts with 1s, 2s, 3s delays)

**Models not appearing in dropdown**

- Ensure the provider is enabled in Council Config
- Check that API key is configured and tested successfully
- For Ollama, verify connection is active

**Jina Reader returns 451 errors**

- HTTP 451 = site blocks AI scrapers (common with news sites)
- Try Tavily/Brave instead, or set `full_content_results` to 0

**Rate limit errors (OpenRouter)**

- Free models: 20 requests/min, 50/day
- Consider using Groq (14,400/day) or Ollama (unlimited)
- Reduce council size for free tier usage

**Binary compatibility errors (node_modules)**

- When syncing between Intel/Apple Silicon Macs:
  ```bash
  rm -rf frontend/node_modules && cd frontend && npm install
  ```

### Logs

- **Backend logs**: Terminal running `uv run python -m backend.main`
- **Frontend logs**: Browser DevTools console

---

## Credits & Acknowledgements

This project is a fork and enhancement of the original **[llm-council](https://github.com/karpathy/llm-council)** by **[Andrej Karpathy](https://github.com/karpathy)**, further building upon **[llm-council-plus](https://github.com/jacob-bd/llm-council-plus)** (which already provided comprehensive multi-provider support, web search, and deliberation features).

**This fork adds production-hardening and AI-assisted development capabilities:**

- **Enhanced Logging System**: Comprehensive error tracking with UI, file management, and automatic rotation
- **Production Reliability**: Improved error handling, graceful degradation, and enhanced rate limit detection
- **AI-Assisted Development**: OpenCode integration for code quality and documentation enhancement
- **Developer Experience**: Unified launch scripts and cross-platform compatibility improvements

We gratefully acknowledge Andrej Karpathy for the original concept, jacob-bd for the feature-complete foundation, and the OpenCode community for enabling modern AI-assisted development practices.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Documentation

This project includes comprehensive documentation for users and developers:

### User Documentation

| Document | Description | Lines |
|----------|-------------|-------|
| **[README.md](README.md)** | Main project documentation (this file) | 619 |
| **[QUICKSTART.md](QUICKSTART.md)** | Get running in 5 minutes | 123 |
| **[docs/logging-guide.md](docs/logging-guide.md)** | Logging system guide (166 lines) | 166 |

### Developer Documentation

| Document | Description | Lines |
|----------|-------------|-------|
| **[CLAUDE.md](CLAUDE.md)** | Claude Code AI integration guide (architecture, patterns, gotchas) | 302 |
| **[AGENTS.md](AGENTS.md)** | Project knowledge base for AI agents (136 lines) | 136 |
| **[backend/AGENTS.md](backend/AGENTS.md)** | Backend-specific guidelines (47 lines) | 47 |
| **[frontend/AGENTS.md](frontend/AGENTS.md)** | Frontend-specific guidelines (46 lines) | 46 |
| **[backend/providers/AGENTS.md](backend/providers/AGENTS.md)** | Provider development guide | - |

### Quick Links

- **Quick Start**: See [QUICKSTART.md](QUICKSTART.md) for 5-minute setup guide
- **Logging**: See [docs/logging-guide.md](docs/logging-guide.md) for debug features
- **AI Development**: See [CLAUDE.md](CLAUDE.md) for AI-assisted development workflow
- **Backend Patterns**: See [backend/AGENTS.md](backend/AGENTS.md) for Python backend conventions
- **Frontend Patterns**: See [frontend/AGENTS.md](frontend/AGENTS.md) for React development rules

---

## Contributing

Contributions are welcome! This project embraces the spirit of "vibe coding" - feel free to fork and make it your own.

---

<p align="center">
  <strong>Built with the collective wisdom of AI</strong><br>
  <em>Ask the council. Get better answers.</em>
</p>
