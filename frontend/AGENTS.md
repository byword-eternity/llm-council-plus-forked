# FRONTEND GUIDE

## OVERVIEW
React 19 + Vite application. "Midnight Glass" theme.
**State Heavy**: `App.jsx` controls almost all application logic.

## STRUCTURE
```
frontend/
├── src/
│   ├── components/     # Flat list of UI components
│   ├── api.js          # Custom fetch wrapper (SSE handling)
│   └── App.jsx         # Main controller
├── vite.config.js      # Build config
└── eslint.config.js    # Linting rules
```

## KEY PATTERNS
- **SSE Handling**: `api.js` exposes `streamConversation`. `App.jsx` consumes events.
- **Markdown**: Use `<ReactMarkdown>` wrapped in `.markdown-content`.
- **Styling**: Pure CSS files colocated with components (e.g., `Sidebar.jsx` + `Sidebar.css`).

## DEVELOPER RULES
- **StrictMode**: Enabled. Effects run twice in dev. Plan accordingly.
- **Immutable Updates**: `setResponses(prev => [...prev, new])`.
- **No Unused Vars**: Linting is strict (except `_` prefix).

## ANTI-PATTERNS
- **NO** extensive prop drilling (though `App.jsx` does it—refactor carefully).
- **NO** direct DOM manipulation (use Refs).
- **NO** hardcoded API URLs (use relative `/api/...`).
