# v0.2.0 Development Roadmap

**Branch**: `feature/v0.2.0-web-ui`  
**Status**: 🚧 In Progress  
**Target**: Week 2 (Days 6-10)

## 🎯 Goals

Transform RAG Debugger from CLI-only to a full-featured debugging platform with:
1. Interactive Web UI for timeline visualization
2. Advanced regression testing capabilities
3. LlamaIndex integration (in addition to LangChain)
4. Prompt versioning system

## 📋 Feature Breakdown

### 1. Web UI for Timeline Visualization ⏰

**Priority**: HIGH  
**Estimated Time**: 2 days  
**Status**: 🚧 Starting

#### Components to Build:

##### A. Backend Enhancements
- [ ] Add WebSocket support for real-time updates
- [ ] Enhance API endpoints for UI data
- [ ] Add session streaming endpoint
- [ ] Implement pagination for large sessions

##### B. Frontend (Vanilla JS)
- [ ] Session list view with filtering/sorting
- [ ] Timeline visualization component
- [ ] Event detail panels
- [ ] Cost breakdown charts
- [ ] Search and filter functionality
- [ ] Real-time updates via WebSocket
- [ ] Dark/light theme toggle
- [ ] Responsive design

##### C. Visualization Features
- [ ] Interactive timeline with zoom/pan
- [ ] Event cards with collapsible details
- [ ] Retrieved chunks viewer
- [ ] Prompt diff viewer
- [ ] Cost breakdown pie chart
- [ ] Duration waterfall chart

#### File Structure:
```
ui/
├── index.html          # Main app shell
├── styles.css          # Global styles
├── app.js              # Main application logic
├── components/
│   ├── timeline.js     # Timeline visualization
│   ├── session-list.js # Session browser
│   ├── event-viewer.js # Event details
│   └── cost-chart.js   # Cost visualization
├── utils/
│   ├── api.js          # API client
│   └── websocket.js    # WebSocket handler
└── assets/
    └── logo.svg        # Brand assets
```

---

### 2. Advanced Regression Testing 🧪

**Priority**: HIGH  
**Estimated Time**: 1.5 days  
**Status**: ⏳ Queued

#### Features:

##### A. Enhanced Snapshot System
- [ ] Automatic snapshot capture on test runs
- [ ] Snapshot metadata (git commit, timestamp, tags)
- [ ] Baseline management (mark snapshot as baseline)
- [ ] Snapshot collections/suites

##### B. Comparison Engine
- [ ] Smart diff algorithm for responses
- [ ] Semantic similarity scoring
- [ ] Cost drift detection
- [ ] Performance regression detection
- [ ] Chunk overlap analysis

##### C. Regression CLI
- [ ] `ragdebug regression run` - Run regression tests
- [ ] `ragdebug regression compare` - Compare two runs
- [ ] `ragdebug regression baseline` - Set baseline
- [ ] `ragdebug regression report` - Generate HTML report

##### D. Test Configuration
```yaml
# .ragdebug.yml
regression:
  baseline: "snapshot-id-123"
  thresholds:
    cost_increase: 10%  # Fail if cost increases > 10%
    similarity: 0.85    # Fail if similarity < 85%
    duration: 2x        # Fail if duration > 2x baseline
  test_queries:
    - "What is RAG?"
    - "How does retrieval work?"
```

---

### 3. LlamaIndex Integration 🦙

**Priority**: MEDIUM  
**Estimated Time**: 1 day  
**Status**: ⏳ Queued

#### Components:

##### A. LlamaIndex Callback Handler
```python
llamaindex/
├── __init__.py
├── callback.py         # LlamaIndexDebuggerCallback
└── instrumentation.py  # Instrumentation integration
```

##### B. Features:
- [ ] Query event capture
- [ ] Retrieval event capture
- [ ] Synthesis event capture
- [ ] Token counting
- [ ] Cost tracking
- [ ] Auto-save to database

##### C. Example Integration:
```python
from llama_index import VectorStoreIndex
from rag_debugger.llamaindex import RagDebuggerCallback

# Add debugger to LlamaIndex
callback = RagDebuggerCallback(auto_save=True)
index = VectorStoreIndex.from_documents(
    documents,
    callback_manager=CallbackManager([callback])
)
```

---

### 4. Prompt Versioning 📝

**Priority**: MEDIUM  
**Estimated Time**: 1 day  
**Status**: ⏳ Queued

#### Features:

##### A. Prompt Registry
- [ ] Store prompt templates with versions
- [ ] Track prompt changes over time
- [ ] Associate prompts with sessions
- [ ] Prompt performance analytics

##### B. Version Management
```python
# Store prompts
ragdebug.prompts.register(
    name="qa_prompt_v1",
    template="Context: {context}\n\nQuestion: {question}",
    version="1.0.0"
)

# Track usage
ragdebug.prompts.track_usage(
    prompt_name="qa_prompt_v1",
    session_id="...",
    performance_metrics={...}
)
```

##### C. CLI Commands
- [ ] `ragdebug prompts list` - List all prompts
- [ ] `ragdebug prompts show <name>` - Show prompt details
- [ ] `ragdebug prompts compare <v1> <v2>` - Compare versions
- [ ] `ragdebug prompts stats <name>` - Performance stats

##### D. Database Schema
```sql
CREATE TABLE prompts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    template TEXT NOT NULL,
    variables TEXT,  -- JSON array
    created_at DATETIME,
    UNIQUE(name, version)
);

CREATE TABLE prompt_usage (
    id TEXT PRIMARY KEY,
    prompt_id TEXT,
    session_id TEXT,
    cost REAL,
    duration_ms INTEGER,
    success BOOLEAN,
    created_at DATETIME,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

---

## 🗓️ Development Schedule

### Week 2: Day 6-7 (Web UI)
- **Day 6**: Backend enhancements + Basic UI shell
  - [ ] Add WebSocket support
  - [ ] Create HTML/CSS structure
  - [ ] Implement session list API
  - [ ] Build session browser component

- **Day 7**: Timeline visualization
  - [ ] Timeline component with D3.js or vanilla JS
  - [ ] Event cards and detail views
  - [ ] Cost breakdown charts
  - [ ] Real-time updates

### Week 2: Day 8-9 (Regression + Integrations)
- **Day 8**: Advanced regression testing
  - [ ] Enhanced snapshot system
  - [ ] Comparison engine
  - [ ] Regression CLI commands
  - [ ] HTML report generator

- **Day 9**: LlamaIndex + Prompt versioning
  - [ ] LlamaIndex callback handler
  - [ ] Prompt registry system
  - [ ] Version management
  - [ ] CLI commands

### Week 2: Day 10 (Polish + Release)
- **Day 10**: Documentation and release
  - [ ] Update README with new features
  - [ ] Write migration guide
  - [ ] Create demo videos/GIFs
  - [ ] Tag v0.2.0 release

---

## 🎨 Design Principles

### Web UI
- **Keep it simple**: No framework dependencies (vanilla JS)
- **Performance first**: Lazy loading, virtual scrolling for large lists
- **Accessibility**: ARIA labels, keyboard navigation
- **Mobile-friendly**: Responsive design

### Code Quality
- **Test coverage**: Maintain >80% coverage
- **Type safety**: Use Pydantic for all models
- **Documentation**: Inline comments + docstrings
- **Error handling**: Graceful degradation

---

## 📊 Success Metrics

After v0.2.0, users should be able to:
- ✅ Visualize RAG timelines in browser
- ✅ Run automated regression tests
- ✅ Use with both LangChain and LlamaIndex
- ✅ Version and track prompt performance
- ✅ Generate regression reports
- ✅ See real-time updates during debugging

---

## 🚀 Getting Started

### Setup Development Environment
```bash
cd rag-debugger
git checkout feature/v0.2.0-web-ui
poetry install
poetry shell

# Start development server with hot reload
ragdebug run --reload

# Run tests in watch mode
pytest --watch
```

### Development Workflow
1. Pick a feature from the roadmap
2. Create feature branch: `feature/v0.2.0-<feature-name>`
3. Implement with tests
4. Update documentation
5. Create PR to `feature/v0.2.0-web-ui`
6. Merge when approved

---

## 📝 Notes

- **Keep v0.1.0 stable**: All v0.2.0 work on separate branches
- **Backward compatibility**: Don't break existing CLI/API
- **Progressive enhancement**: Web UI is optional, CLI still works
- **Performance**: Test with large sessions (1000+ events)

---

## 🔗 Related Documents

- [BUILD_PLAN.md](../BUILD_PLAN.md) - Original 2-week plan
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
- [TASK_CHECKLIST.md](../TASK_CHECKLIST.md) - Task tracking

---

**Last Updated**: 2026-02-14  
**Current Status**: Starting Day 6 - Web UI Foundation
