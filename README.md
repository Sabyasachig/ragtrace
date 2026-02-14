# RAG Debugger 🔍

> **DevTools for your RAG pipelines** - Debug, inspect, and optimize Retrieval-Augmented Generation systems with ease.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## ✨ What is RAG Debugger?

RAG Debugger is a lightweight debugging layer for RAG (Retrieval-Augmented Generation) systems that captures and visualizes every step of your pipeline:

- 🔍 **Event Capture** - Automatically intercepts retrieval, prompt, and generation events
- 💰 **Cost Tracking** - Accurate token counting and cost estimation per query
- 📊 **Timeline View** - Visualize the flow from retrieval → prompt → generation
- 🔧 **CLI Tool** - Developer-friendly command-line interface
- 🌐 **REST API** - Query and analyze sessions programmatically
- 🧪 **Regression Testing** - Snapshot and compare RAG outputs

**Think of it as Chrome DevTools, but for your RAG pipelines.**

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/rag-debugger.git
cd rag-debugger

# Install dependencies (using pip)
pip install -e .

# Or using Poetry
poetry install
poetry shell

# Initialize database
ragdebug init
```

### Basic Usage

```python
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain import RagDebuggerCallback

# Your existing RAG setup
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_texts(["Your documents here..."], embeddings)
llm = ChatOpenAI(model="gpt-3.5-turbo")

# Add RAG Debugger - just one line!
debugger = RagDebuggerCallback(auto_save=True)

# Create chain with debugger
chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vectorstore.as_retriever(),
    callbacks=[debugger]  # ← Automatic capture!
)

# Run your query (automatically captured)
result = chain.run("What is RAG?")
```

### View Results

```bash
# View latest session
ragdebug trace last

# List all sessions
ragdebug list

# Export to JSON
ragdebug export <session-id> > session.json

# Start API server
ragdebug run
```

## 📊 Example Output

```
╭─ Session: d4f3a8b2-... ─────────────────────────────────╮
│ Query: What is RAG?                                      │
│ Model: gpt-3.5-turbo                                     │
│ Cost: $0.00360                                           │
│ Duration: 1,850ms                                        │
╰──────────────────────────────────────────────────────────╯

┏━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Event       ┃ Duration   ┃ Cost       ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ Retrieval   │ 150ms      │ $0.00001   │
│ Prompt      │ 0ms        │ $0.00000   │
│ Generation  │ 1,700ms    │ $0.00359   │
└─────────────┴────────────┴────────────┘
```

## 🎯 Features

### ✅ Core Features

- **Automatic Event Capture** - Works with LangChain callbacks
- **Cost Tracking** - Uses tiktoken for accurate token counting
- **Timeline Visualization** - See your RAG pipeline in action
- **Session Management** - Store and retrieve debugging sessions
- **CLI Tool** - Rich formatted terminal output
- **REST API** - FastAPI server with OpenAPI docs
- **JSON Export** - Export sessions for analysis
- **Snapshot Testing** - Save and compare pipeline outputs

### 🎨 CLI Commands

```bash
ragdebug init              # Initialize database
ragdebug list              # List recent sessions
ragdebug trace [id]        # View session details
ragdebug trace last        # View latest session
ragdebug export <id>       # Export to JSON
ragdebug clear             # Clear all data
ragdebug snapshot save     # Save snapshot
ragdebug snapshot list     # List snapshots
ragdebug run               # Start API server
```

### 🌐 API Endpoints

```
POST   /api/sessions                      # Create session
GET    /api/sessions                      # List sessions
GET    /api/sessions/{id}                 # Get session
PATCH  /api/sessions/{id}                 # Update session
DELETE /api/sessions/{id}                 # Delete session
POST   /api/sessions/{id}/events          # Add event
GET    /api/sessions/{id}/costs           # Get costs
POST   /api/snapshots                     # Create snapshot
GET    /api/snapshots                     # List snapshots
GET    /api/snapshots/{id1}/compare/{id2} # Compare snapshots
```

Visit `http://localhost:8000/docs` after running `ragdebug run` for interactive API documentation.

## 🏗️ Architecture

```
rag-debugger/
├── core/              # Core business logic
│   ├── models.py      # Pydantic data models
│   ├── storage.py     # SQLite database layer
│   ├── cost.py        # Token counting & cost calculation
│   └── capture.py     # Event aggregation
├── langchain/         # LangChain integration
│   └── middleware.py  # Callback handler
├── api/               # REST API (FastAPI)
│   ├── main.py        # FastAPI application
│   └── routes.py      # API endpoints
├── cli/               # Command-line interface
│   └── main.py        # Click CLI commands
├── examples/          # Usage examples
│   └── simple_rag.py  # Complete working example
└── tests/             # Test suite
    ├── test_cost.py   # Cost calculation tests
    ├── test_storage.py # Database tests
    └── test_capture.py # Capture logic tests
```

## 📋 Requirements

- **Python**: 3.11+ (3.12 recommended)
- **Dependencies**: FastAPI, LangChain, tiktoken, Rich, Click
- **OpenAI API Key**: Required for examples (not for core functionality)

## 🛠️ Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/rag-debugger.git
cd rag-debugger

# Install with development dependencies
poetry install
poetry shell

# Run tests
pytest

# Run with coverage
pytest --cov=core --cov=langchain --cov=api --cov=cli
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_cost.py -v

# With coverage report
pytest --cov=core tests/
```

### Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type checking
mypy .
```

## 📖 Examples

Check out the `examples/` directory for complete working examples:

- **`simple_rag.py`** - Basic RAG pipeline with debugger
- **`with_sources.py`** - RAG with source tracking (coming soon)

## 🔬 Use Cases

### 1. Debug Failed Queries
```bash
# See exactly why your RAG pipeline failed
ragdebug trace last
```

### 2. Track Costs
```bash
# Monitor spending per query
ragdebug list --sort-by cost
```

### 3. Identify Retrieval Issues
```python
# Check which documents were retrieved
session = debugger.get_latest_session()
print(session.retrieval_event.chunks)
```

### 4. Regression Testing
```bash
# Save baseline
ragdebug snapshot save "v1-baseline"

# Compare after changes
ragdebug snapshot compare <snapshot-id-1> <snapshot-id-2>
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Integrated with [LangChain](https://python.langchain.com/)
- Token counting via [tiktoken](https://github.com/openai/tiktoken)
- Beautiful CLI with [Rich](https://rich.readthedocs.io/)

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/rag-debugger/issues)
- **Documentation**: See [examples/](examples/) directory
- **API Docs**: Run `ragdebug run` and visit `http://localhost:8000/docs`

## 🗺️ Roadmap

### v0.2.0 (Coming Soon)
- [ ] Web UI for timeline visualization
- [ ] Advanced regression testing
- [ ] LlamaIndex integration
- [ ] Prompt versioning

### v0.3.0
- [ ] Agent tracing support
- [ ] Cost optimization suggestions
- [ ] Quality scoring
- [ ] Team collaboration features

### v1.0.0
- [ ] Cloud mode
- [ ] Advanced analytics
- [ ] Alert system
- [ ] Multi-framework support

## ⭐ Star History

If you find RAG Debugger useful, please consider giving it a star! ⭐

---

**Built with ❤️ for RAG developers**
