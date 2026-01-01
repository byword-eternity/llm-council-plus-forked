# COMPONENTS GUIDE

## OVERVIEW
22+ React components. Flat structure.
**Style**: Glassmorphism (`.glass-panel`), Dark mode only.

## CORE COMPONENTS
| Component | Role | Notes |
|-----------|------|-------|
| `Stage1/2/3.jsx` | Deliberation views | Handle tab switching and streaming updates. |
| `Settings.jsx` | Config UI | Massive file (1500 lines). 5 sub-sections. |
| `CouncilGrid.jsx` | Visualizer | Renders the grid of active models. |
| `ChatInterface.jsx`| Input | Handles user query and mode toggles. |

## CONVENTIONS
- **Imports**: `import './Component.css'` at the top.
- **Props**: Destructure in function signature.
- **Icons**: SVG imports from `../../assets/icons/`.

## GOTCHAS
- **Settings.jsx**: Complex validation logic for API keys.
- **Stage2.jsx**: Parses raw text rankings to display the leaderboard.
