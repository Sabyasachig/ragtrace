# Changelog

All notable changes to RAGTrace are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.2.0] - 2026-03-17

### Added

#### Regression Testing (`core/regression.py`)
- `RegressionAnalyzer` class with full snapshot diff engine
  - `diff_retrieval()` — Jaccard set similarity over retrieved chunk texts
  - `diff_answers()` — `difflib` unified diff + SequenceMatcher ratio
  - `diff_costs()` — absolute and percent cost delta
  - `compare()` — full `ComparisonResult` (retrieval + answer + cost)
  - `regression_score()` — composite score (0.4 × retrieval + 0.6 × answer) with PASS/WARN/FAIL verdict
  - `batch_compare()` — baseline vs. multiple candidates
- Top-level helpers `compare_snapshots()` and `score_regression()`

#### Snapshot API endpoints (`api/routes.py`)
- `GET /api/snapshots/{id1}/compare/{id2}` — full `ComparisonResult` JSON
- `GET /api/snapshots/{id1}/score/{id2}` — regression score summary (verdict + numeric score)

#### Snapshot CLI command (`cli/main.py`)
- `ragtrace snapshot compare <id1> <id2>` — rich terminal regression report
- `ragtrace snapshot compare <id1> <id2> --json` — machine-readable output

#### LlamaIndex integration (`llamaindex/`)
- New package `ragtrace.llamaindex`
- `RagTracerLlamaIndex(BaseCallbackHandler)` — captures QUERY, RETRIEVE, and LLM events
- `SimpleRagTracerLlamaIndex` — context-manager wrapper for easy drop-in use
- Graceful stub fallback: works even when `llama-index` is not installed

#### Prompt Versioning (`core/models.py`, `core/storage.py`, `api/routes.py`, `cli/main.py`)
- New Pydantic models: `PromptVersion`, `PromptVersionDiff`
- New SQLite table: `prompt_versions` (auto-increments integer version per name)
- Storage methods: `save_prompt_version`, `get_prompt_version`, `list_prompt_versions`, `list_prompt_names`, `delete_prompt_version`
- New API endpoints:
  - `GET  /api/prompts` — list all prompt names
  - `POST /api/prompts` — save new prompt version (auto-increments integer version)
  - `GET  /api/prompts/{name}` — list all versions
  - `GET  /api/prompts/{name}/active` — get current active version
  - `GET  /api/prompts/{name}/versions/{v}` — get specific version
  - `GET  /api/prompts/{name}/diff/{va}/{vb}` — unified diff with similarity score
  - `DELETE /api/prompts/{name}/versions/{v}` — delete a version
- New CLI `prompt` group:
  - `ragtrace prompt save <name> <template.txt> [-d description] [-t tag]`
  - `ragtrace prompt list [name]`
  - `ragtrace prompt show <name> [-v version]`
  - `ragtrace prompt diff <name> <va> <vb>`

#### Web UI (`ui/app.js`)
- **Regression tab**: real snapshot list, inline regression comparison panel, PASS/WARN/FAIL badge, answer diff viewer
- **Prompts tab**: real prompt list with active template preview, version diff viewer, "+ New Version" modal, "+New Prompt" modal
- New `APIClient` methods: `getSnapshots`, `getSnapshot`, `createSnapshot`, `deleteSnapshot`, `compareSnapshots`, `scoreSnapshots`, `getPromptNames`, `getPromptVersions`, `getActivePrompt`, `savePromptVersion`, `diffPrompts`, `deletePromptVersion`

#### Cost Pricing (`core/cost.py`)
- Updated PRICING table to 2025/2026 rates
- Added: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `o1`, `o1-mini`, `o3-mini`
- Updated `gpt-3.5-turbo` to current pricing ($0.50 / $1.50 per 1M tokens)
- Default fallback model changed to `gpt-4o-mini` pricing

### Fixed
- `tests/test_storage.py` — rewritten with correct Pydantic v2 field names
- `tests/test_capture.py` — fixed import `detect_unused_chunks → find_unused_chunks`
- `cli/main.py` — fixed indentation bug in `list` command's `console.print` call
- `pyproject.toml` — removed unused `sqlalchemy`, added `llamaindex` package, fixed Python requirement to `^3.11`, added `httpx` as dev dependency

### Tests
- Added `tests/test_regression.py` (28 tests)
- Added `tests/test_prompt_versioning.py` (18 tests)
- Added `tests/test_llamaindex.py` (20 tests)
- Total: **146 passing tests**

---

## [0.1.0] - 2026-03-10

### Added

#### Core Infrastructure
- `core/models.py` — Pydantic v2 models: `RagSession`, `StoredEvent`, `RetrievedChunk`, `PromptData`, `GenerationData`, `SessionDetail`, `CostBreakdown`, `Snapshot`
- `core/storage.py` — SQLite database layer with singleton `Database` class
  - Tables: `sessions`, `events`, `snapshots`
  - CRUD for sessions, events (with JSON serialization), snapshots, cost breakdown
- `core/capture.py` — Event aggregation: `RagCapture` class, `find_unused_chunks()`, `calculate_retrieval_stats()`
- `core/cost.py` — Token counting (tiktoken) and cost estimation; initial GPT-3.5/GPT-4 pricing

#### LangChain Integration (`langchain/`)
- `RagTracer(BaseCallbackHandler)` — captures retrieval, prompt, and LLM events from LangChain chains
- `SimpleRagTracer` — context-manager wrapper for non-LangChain usage
- `capture_retrieval()`, `capture_prompt()`, `capture_generation()` helpers

#### REST API (`api/`)
- FastAPI application (`api/main.py`) with CORS, WebSocket support, and lifespan management
- Endpoints (`api/routes.py`):
  - Sessions: CRUD, event listing, cost breakdown
  - Events: filtered listing
  - Snapshots: create / list / get / delete
  - Stats: aggregate dashboard stats
  - Cost breakdown: per-session or global
  - WebSocket: `/ws` for live session notifications

#### CLI (`cli/main.py`)
- `ragtrace init` — database initialization
- `ragtrace list` — paginated session list with rich table
- `ragtrace show [id]` — detailed session view with event table
- `ragtrace export <id>` — JSON export
- `ragtrace clear` — wipe all data
- `ragtrace snapshot save <name>` — save named snapshot
- `ragtrace snapshot list` — list snapshots
- `ragtrace run` — start API server via uvicorn

#### Web UI (`ui/`)
- Vanilla JS single-page app with sessions / timeline / regression / prompts tabs
- Sessions dashboard with search, sort, and session cards
- Timeline view with waterfall chart (Chart.js) and event inspector
- Cost breakdown doughnut chart
- Export to JSON and CSV
- WebSocket live updates
- Dark / light theme toggle
- Development server (`ui/serve.py`)

#### Tests
- `tests/test_cost.py` — 42 tests for cost calculation and token counting
- `tests/test_storage.py` — 28 tests for database CRUD
- `tests/test_capture.py` — 40 tests for event capture and aggregation
- Total: **110 passing tests**

#### Documentation & Packaging
- `README.md`, `CONTRIBUTING.md`, `ROADMAP_v0.2.0.md`
- `pyproject.toml`, `setup.py`, `MANIFEST.in` for PyPI publishing
- `examples/simple_rag.py` — end-to-end LangChain RAG example

---

[0.2.0]: https://github.com/yourusername/ragtrace/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yourusername/ragtrace/releases/tag/v0.1.0
