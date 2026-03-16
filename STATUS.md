# 🎯 Current Status

**Date**: March 17, 2026  
**Branch**: `main`  
**Status**: ✅ v0.2.0 Complete — All 10 planned days shipped

---

## 📊 What's Complete

### ✅ Week 1 (Days 1-5) — MVP Core
- **Backend**: Core infrastructure — models, storage, cost tracking, capture
- **Tests**: 110 passing tests
- **CLI**: `init`, `list`, `show`, `export`, `clear`, `snapshot save/list`, `run`
- **API**: 10 REST endpoints (FastAPI)
- **Integration**: LangChain callback handler
- **Storage**: SQLite with sessions, events, snapshots tables

### ✅ Day 6 — Web UI Foundation
- Sessions dashboard with search, sort, real-time updates
- Timeline view with event inspection
- Waterfall duration chart and cost breakdown doughnut (Chart.js)
- Dark/light theme, responsive layout
- WebSocket live notifications

### ✅ Day 7 — Bug Fixes & Polish
- Fixed timeline rendering bugs
- Port-mismatch fix (API :8000, UI :3000)
- UI sections aligned with backend API field names

### ✅ Day 8 — Regression Testing
- `core/regression.py`: `RegressionAnalyzer` (Jaccard + SequenceMatcher scoring)
- New API endpoints: `compare` and `score` for snapshot pairs
- CLI: `ragtrace snapshot compare <id1> <id2>`
- 28 new regression tests

### ✅ Day 9 — LlamaIndex + Prompt Versioning
- `llamaindex/` package: `RagTracerLlamaIndex`, `SimpleRagTracerLlamaIndex`
- `PromptVersion` / `PromptVersionDiff` models
- `prompt_versions` table + full CRUD
- 7 new prompt API endpoints
- CLI `prompt` group: `save`, `list`, `show`, `diff`
- 38 new tests (20 LlamaIndex + 18 prompt versioning)

### ✅ Day 10 — Polish & Release
- Updated pricing to 2025/2026 (GPT-4o, o1, o3-mini, gpt-4-turbo, gpt-4o-mini)
- Web UI Regression tab: real snapshot list + inline comparison panel
- Web UI Prompts tab: real prompt list + version diff viewer
- README.md fully rewritten with all new features
- CHANGELOG.md written for v0.1.0 and v0.2.0
- `pyproject.toml` fixed (packages, Python version, dependencies)

---

## 📈 Test Coverage

| Test File                      | Tests |
|-------------------------------|-------|
| `test_cost.py`                | 42    |
| `test_storage.py`             | 28    |
| `test_capture.py`             | 40    |
| `test_regression.py`          | 28    |
| `test_llamaindex.py`          | 20    |
| `test_prompt_versioning.py`   | 18    |
| **Total**                     | **176** |

---

## 🚀 Quick Start

```bash
# Install
pip install -e .

# Initialize
ragtrace init

# Terminal 1 — API
uvicorn api.main:app --port 8000 --reload

# Terminal 2 — UI
python ui/serve.py
# → open http://localhost:3000
```

---

## 🗺️ Next: v0.3.0

- Agent tracing (multi-step reasoning chains)
- Cost optimization suggestions
- LLM-as-judge quality scoring
- Team collaboration / shared dashboards

