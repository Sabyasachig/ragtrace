# RAGTrace — Copilot Project Instructions

> Auto-loaded for every Copilot conversation. Update this file whenever anything significant changes.

---

## 1. What is this project?

**RAGTrace** is a developer observability tool for RAG (Retrieval-Augmented Generation) pipelines. It captures every step of a RAG execution (retrieval, prompt construction, generation) and exposes them through a REST API, an interactive Web UI, and a CLI.

- **PyPI**: `pip install ragtrace`
- **GitHub**: https://github.com/Sabyasachig/ragtrace
- **Current version**: read from `VERSION` file (currently `0.2.2`)

---

## 2. Project layout

```
ragtrace/                          ← All work happens here
├── VERSION                        ← Single source of truth for version
├── pyproject.toml                 ← Poetry build config (version synced from VERSION by CI)
├── setup.py                       ← Reads version from VERSION file
├── start.sh                       ← Start both servers + open browser (see §4)
├── push-to-github.sh              ← Daily git workflow (see §4)
├── test_package.sh                ← Validate package before PyPI publish (see §4)
│
├── api/                           ← FastAPI REST API
│   ├── main.py                    ← App entry point, mounts router with /api prefix
│   └── routes.py                  ← All endpoints
│
├── cli/                           ← Click CLI
│   └── main.py
│
├── core/                          ← Business logic
│   ├── capture.py                 ← RagTracer context manager
│   ├── storage.py                 ← SQLite storage (db at ~/.ragtrace/ragtrace.db)
│   ├── models.py                  ← Pydantic v2 models (Session, Retrieval, Generation, Snapshot, PromptVersion)
│   ├── cost.py                    ← Token counting + cost for GPT-4o, Claude, Gemini, o1/o3
│   └── regression.py              ← Snapshot comparison + scoring
│
├── langchain/                     ← LangChain callback middleware
├── llamaindex/                    ← LlamaIndex integration
│
├── ui/                            ← Vanilla JS web UI
│   ├── index.html                 ← Single page app (script tag: app.js?v=7, NO type=module)
│   ├── app.js                     ← All UI logic (~1400 lines); bump ?v= on every change
│   ├── styles.css
│   ├── serve.py                   ← Simple HTTP server on port 3000
│   ├── generate_test_data_v2.py   ← Creates 5 sample sessions in the DB
│   └── generate_test_data.py      ← Older generator (use v2)
│
├── demo/                          ← Demo tooling
│   ├── record_demo.sh             ← Re-record demo GIF (see §4)
│   ├── make_demo_gif.py           ← Playwright headless automation script
│   ├── demo.gif                   ← Latest demo (embedded in README)
│   └── _demo_frames/              ← Gitignored intermediate PNGs
│
├── tests/                         ← 146 pytest tests
└── .github/
    ├── copilot-instructions.md    ← This file
    └── workflows/
        ├── publish-testpypi.yml   ← Publishes to TestPyPI on push to main
        └── publish-pypi.yml       ← Publishes to PyPI on GitHub Release; auto-bumps version after
```

---

## 3. Project milestone history

| Day | What was built |
|-----|----------------|
| Day 1 | Project scaffold, FastAPI skeleton, SQLite storage, Pydantic models |
| Day 2 | LangChain callback middleware (`langchain/middleware.py`) |
| Day 3 | Token counting + cost estimation (`core/cost.py`) — GPT-4o, Claude, Gemini, o1/o3 |
| Day 4 | Click CLI (`cli/main.py`) — `sessions`, `inspect`, `export`, `cost` commands |
| Day 5 | Session JSON export, full REST API for sessions/events/cost |
| Day 6 | Vanilla JS Web UI — Sessions list, Timeline, Performance waterfall, Cost doughnut chart |
| Day 7 | UI polish — dark mode, filters, event detail panel, charts |
| Day 8 | Regression testing — `core/regression.py`, snapshot CRUD + compare/score API, CLI `snapshot compare` |
| Day 9 | LlamaIndex integration (`llamaindex/`), prompt versioning (`PromptVersion` model, `prompt_versions` table, 7 prompt API endpoints, CLI `prompt` group) |
| Day 10 | Updated pricing in `cost.py`, wired Regression + Prompts UI tabs, rewrote README, CHANGELOG |
| Post v0.2 | CI/CD pipelines, doc cleanup, demo GIF tooling, `push-to-github.sh` daily workflow, `VERSION` file + auto-bump on release, UI bug fixes |

**Tests**: 146 total (unit + integration across capture, storage, cost, regression, prompts, llamaindex)

---

## 4. Automation scripts

### `./start.sh` — Start the full project
```bash
cd ragtrace/
./start.sh
```
- Creates venv if missing, installs deps
- Generates sample data if DB doesn't exist (`~/.ragtrace/ragtrace.db`)
- Starts API on :8000 and UI on :3000 in background (logs: `/tmp/ragtrace-api.log`, `/tmp/ragtrace-ui.log`)
- Opens http://localhost:3000 in browser
- Press Ctrl+C to stop everything cleanly
- **Note**: `ragtrace/venv/` is broken (directory rename issue). If `start.sh` fails, start servers manually (see §5)

### `./push-to-github.sh` — Daily git workflow
```bash
./push-to-github.sh              # branch → stage → commit → push → prints PR URL
./push-to-github.sh --setup      # first-time remote setup only
```
- Prompts for: branch name (Enter = keep current), staging choice (y = all), commit message
- Pushes and auto-opens the GitHub PR URL in browser
- Branch naming convention: `feat/`, `fix/`, `chore/`, `docs/`
- Always use this instead of raw `git push`

### `./test_package.sh` — Validate before publishing
```bash
./test_package.sh
```
- Installs build tools → cleans `dist/` → builds wheel + sdist → `twine check`
- Verifies UI files are included in tarball → installs `.whl` locally
- Tests CLI: `ragtrace --version` → tests Python import → tests `ragtrace init`
- Run this before creating a GitHub Release

### `./demo/record_demo.sh` — Re-record the demo GIF
```bash
./demo/record_demo.sh                # servers must be running on :8000 and :3000
./demo/record_demo.sh --regen-data   # also regenerate sample sessions first
```
- Checks/starts API and UI servers if not already running
- Installs playwright + Pillow into `.venv` if missing
- Runs `demo/make_demo_gif.py` (Playwright headless Chromium)
  - Walks through all 4 UI tabs: Sessions → Timeline → Regression → Prompts
  - Creates 2 snapshots, inspects cost breakdown, browses prompt versions
- Saves `demo/demo.gif` (~575KB, ~191 frames, 10fps)
- `demo/_demo_frames/` (intermediate PNGs) is gitignored
- Requires: `/Users/sabyasachighosh/Projects/rag_trace/.venv/bin/python`

---

## 5. Running locally (manual)

```bash
cd ragtrace/

# API server (port 8000) — use system python3, not ragtrace/venv/
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# UI server (port 3000)
python3 ui/serve.py

# Generate 5 sample sessions
python3 ui/generate_test_data_v2.py

# Stop all servers
lsof -ti:8000,3000 | xargs kill -9 2>/dev/null

# Run tests
python3 -m pytest tests/ -v
```

**Python env notes**:
- Use `python3` (system, points to `/usr/local/anaconda3/bin/python3`)
- `ragtrace/venv/` is broken — do NOT use it
- `/Users/sabyasachighosh/Projects/rag_trace/.venv/` works (Python 3.9, has playwright + Pillow)

---

## 6. API reference (critical gotchas)

Base URL: `http://localhost:8000/api`

| Endpoint | Returns | Gotcha |
|---|---|---|
| `GET /sessions` | Plain array `[{id, query, ...}]` | NOT `{sessions: [...]}` — handle both shapes in UI |
| `GET /sessions/{id}` | `{session:{...}, retrieval:{...}, generation:{...}}` | Always unwrap `.session` before rendering |
| `GET /sessions/{id}/events` | Array of events | — |
| `GET /sessions/{id}/cost` | `{total_cost, input_tokens, output_tokens, ...}` | — |
| `POST /snapshots` | Created snapshot | Body: `{session_id, tags}` — NOT `{name, description}` |
| `GET /snapshots` | Array of snapshots | — |
| `GET /snapshots/{id}/compare/{id2}` | Diff object | — |
| `GET /snapshots/{id}/score/{id2}` | Score 0–1 | — |
| `GET /prompts` | Array of prompt names | — |
| `GET /prompts/{name}/versions` | Array of `PromptVersion` | — |
| `GET /prompts/{name}/active` | Active `PromptVersion` | — |

---

## 7. Web UI notes

- Cache-buster in `index.html`: currently `app.js?v=7` — **increment on every `app.js` change**
- `type="module"` was intentionally removed from the script tag — it scopes functions and breaks `onclick` handlers
- Create Snapshot modal: `<select>` dropdown populated from `GET /api/sessions` (replaced old freetext input)
- Dark mode toggle: moon icon in nav bar
- The UI has 4 tabs: Sessions, Timeline, Regression, Prompts

---

## 8. CI/CD & versioning

| Workflow | Trigger | Behaviour |
|---|---|---|
| `publish-testpypi.yml` | Push to `main` | Builds + uploads to TestPyPI (`--skip-existing`) |
| `publish-pypi.yml` | GitHub Release published | Reads version from release tag (e.g. `v0.3.0`), syncs `VERSION`/`pyproject.toml`/`setup.py`, publishes to PyPI, then auto-bumps patch and commits back to `main` with `[skip ci]` |

**To release a new version:**
1. Run `./test_package.sh` to validate locally
2. Create a GitHub Release with tag `v0.X.Y`
3. CI handles everything else (publish + version bump)

Required secrets: `PYPI_API_TOKEN`, `TEST_PYPI_API_TOKEN`

---

## 9. Key technical decisions

- **SQLite** at `~/.ragtrace/ragtrace.db` — no external DB dependency for simple install/use
- **Pydantic v2** models throughout (not v1 — use `model_validate`, not `parse_obj`)
- **FastAPI** for API, **Click** for CLI, **tiktoken** for token counting
- **No bundler** — vanilla JS, single `app.js`, no node_modules, no build step
- `demo/_demo_frames/` is gitignored; `demo/demo.gif` is tracked in git
