# Echo Demo - Decisions

## Architecture Decisions

### Tech Stack Choices
- **Backend**: FastAPI (async, auto docs) + SQLite (simple state) + SQLAlchemy (ORM)
- **Frontend**: Vite + React + TS (fast dev, type-safe)
- **AI**: Native SDKs only (openai, anthropic) - no litellm/langchain
- **Testing**: pytest + pytest-cov + mutmut (mutation testing)

### Provider Strategy
- OpenAI-compatible SDK covers 5 providers (OpenAI/DeepSeek/Qwen/Kimi/GLM)
- Anthropic SDK covers 1 provider
- JSON mode fallback for providers without native support

### Data Storage Split
- Static world data: YAML (version-controlled)
- Runtime player state: SQLite (mutable)

## Module Design Decisions

### Rule Engine
- Pure functions, no AI calls
- Pipeline: physics check → god intervention → state changes
- 100% deterministic required

### AI Service Layer
- Parser: player text → ParsedIntent (JSON mode + fallback)
- Renderer: JudgmentResult → narrative text (prompt engineering)
- Fallback renderer for reliability

### Frontend
- No streaming (simulate typewriter on complete text)
- Context + useReducer for state (no Redux)
- Custom hooks: useTypewriter, useAction, useGameState

