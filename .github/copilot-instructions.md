# RAGTrace — Copilot Project Instructions

> Automatically loaded for every Copilot conversation in this workspace.

## What is this project?

**RAGTrace** (`pip install ragtrace`) is an observability and debugging tool for RAG (Retrieval-Augmented Generation) pipelines. It captures retrieval, prompt, and generation events and exposes them via a REST API, a Web UI, and a CLI.

GitHub: https://github.com/Sabyasachig/ragtrace

---

## Project layout

```
ragtrace/               ← Python package root (work always happens here)
├── api/                ← FastAPI REST API (main.py + routes.py)
├── cli/                ← Click CLI (main.py)
├── core/               ← Business logic: capture.py, storage.py, models.py, cost.py, regression.py
├── langchain/          ← LangChain middleware/callbacks
├── llamaindex/         ← LlamaIndex integration
├── ui/                 ← Vanilla JS web UI (index.html, app.js, styles.css, serve.py)
├── demo/               ← Demo tooling (make_demo_gif.py, record_demo.sh, demo.gif)
├── tests/              ← pytest test suite (146 tests)
├── .github/workflows/  ← CI/CD: publish-testpypi.yml + publish-pypi.yml
├── VERSION             ← Single source of truth for package version
├── pyproject.toml      ← Poetry build config
├── setup.py            ← Reads version from VERSION file
└── push-to-github.sh   ← Daily git workflow: branch → commit → push → PR URL
```

---

## Running locally

```bash
cd ragtrace/

# API server (port 8000)
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# UI server (port 3000)
python3 ui/serve.py

# Generate sample data
python3 ui/generate_test_data_v2.py

# Stop all servers
lsof -ti:8000,3000 | xargs kill -9 2>/dev/null

# Run tests
python3 -m pytest tests/ -v
```

**Python**: Use `python3` (system) — the local venv at `ragtrace/venv/` is broken due to a directory rename. A working venv exists at `/Users/sabyasachighosh/Projects/rag_trace/.venv/` (Python 3.9, has playwright + Pillow).

---

## Git workflow

Always use `push-to-github.sh` for committing/pushing:

```bash
./push-to-github.sh           # interactive: branch → stage → commit → push → PR URL
./push-to-github.sh --setup   # first-time remote setup only
```

Branch naming convention: `feat/`, `fix/`, `chore/`, `docs/`

---

## API structure

- Base URL: `http://localhost:8000/api`
- Key endpoints: `/sessions`, `/sessions/{id}`, `/sessions/{id}/events`, `/sessions/{id}/cost`
- Regression: `/snapshots`, `/snapshots/{id}/compare/{id2}`, `/snapshots/{id}/score/{id2}`
- Prompts: `/prompts`, `/prompts/{name}/versions`, `/prompts/{name}/active`

The `/sessions` endpoint returns a **plain array** (not `{sessions: [...]}`). The `/sessions/{id}` detail endpoint returns `{session: {...}, retrieval: {...}, generation: {...}}` — always unwrap `.session`.

---

## UI notes

- `app.js` cache-buster: currently `v=7` in `index.html` — bump when changing `app.js`
- `type="module"` was intentionally removed from the script tag (breaks inline `onclick` handlers)
- Create Snapshot modal uses a `<select>` dropdown populated from `GET /api/sessions`

---

## CI/CD pipelines

| Workflow | Trigger | Target |
|---|---|---|
| `publish-testpypi.yml` | Push to `main` | TestPyPI (with `--skip-existing`) |
| `publish-pypi.yml` | GitHub Release published | PyPI (with `--skip-existing`) |

**Version flow**: Create GitHub Release with tag `v0.3.0` → CI reads tag, sets version, builds, publishes → CI auto-bumps patch to `0.3.1`, commits back to `main` with `[skip ci]`.

Secrets needed: `PYPI_API_TOKEN`, `TEST_PYPI_API_TOKEN`

---

## Current version & history

- **Current version**: `0.2.2` (in `VERSION` file)
- **v0.1.x**: Core capture, storage, LangChain middleware, CLI, REST API, Web UI
- **v0.2.x**: Regression testing (snapshots + scoring), LlamaIndex integration, prompt versioning, demo tooling, CI/CD

---

## Key technical decisions

- **SQLite** at `~/.ragtrace/ragtrace.db` — no external DB dependency
- **Pydantic v2** models throughout
- **FastAPI** for API, **Click** for CLI, **tiktoken** for token counting
- Demo GIF auto-generated with Playwright headless: `demo/record_demo.sh`
- `demo/_demo_frames/` is gitignored (intermediate PNGs); `demo/demo.gif` is tracked
