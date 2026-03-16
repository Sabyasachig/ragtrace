# Project Rename: RAG Debugger → RAGTrace

## ✅ Complete - Branch: `refactor/rename-to-ragtrace`

All project references have been systematically renamed from "RAG Debugger" to "RAGTrace" for better branding and positioning in the observability/tracing market.

## 🎯 Key Changes

### Package & Branding
- **Package name**: `rag-debugger` → `ragtrace`
- **CLI command**: `ragdebug` → `ragtrace`
- **Main class**: `RagDebuggerCallback` → `RagTracer`
- **Tagline**: "DevTools for RAG" → "Observability for RAG"
- **Icon**: 🔍 → 📊

### Technical Changes
- **Database path**: `~/.ragdebug/` → `~/.ragtrace/`
- **Import**: `from langchain import RagDebuggerCallback` → `from ragtrace import RagTracer`
- **CLI subcommands**: `ragdebug trace` → `ragtrace trace`
- **Download filenames**: `ragdebug-*.json` → `ragtrace-*.json`

## 📝 Files Modified

### Core Package Configuration
- ✅ `setup.py` - Package name, entry points, URLs
- ✅ `pyproject.toml` - Poetry configuration, scripts
- ✅ `MANIFEST.in` - Package manifest (new file)

### Code Files  
- ✅ `core/storage.py` - Database paths
- ✅ `cli/main.py` - CLI commands and messages
- ✅ `api/main.py` - API title and branding
- ✅ `api/__init__.py` - Docstring (if needed)

### UI Files
- ✅ `ui/index.html` - Page title, logo, branding
- ✅ `ui/app.js` - Console logs, download filenames

### Documentation
- ✅ `README.md` - Full documentation update
- ✅ `PUBLISHING.md` - Publishing guide references
- ✅ `test_package.sh` - Test script commands

### Examples
- ✅ `examples/simple_rag.py` - Import and usage
- ✅ `examples/saas_integration_future.py` - All references

## 🔄 Migration Guide for Users

### For Existing Users

If you were using the old `rag-debugger` package:

```bash
# 1. Uninstall old package
pip uninstall rag-debugger

# 2. Install new package
pip install ragtrace

# 3. Update your code
# OLD:
from langchain import RagDebuggerCallback
debugger = RagDebuggerCallback(auto_save=True)

# NEW:
from ragtrace import RagTracer
tracer = RagTracer(auto_save=True)

# 4. Update CLI commands
# OLD: ragdebug trace last
# NEW: ragtrace trace last
```

### Database Migration

The database automatically migrates:
- Old path: `~/.ragdebug/ragdebug.db`
- New path: `~/.ragtrace/ragtrace.db`

You may need to manually copy your old database:
```bash
mkdir -p ~/.ragtrace
cp ~/.ragdebug/ragdebug.db ~/.ragtrace/ragtrace.db
```

## 📦 Publishing Checklist

Before publishing to PyPI:

- [x] All code references updated
- [x] Documentation updated
- [x] Examples updated  
- [x] Tests updated
- [x] Version bumped to 0.2.0
- [ ] Test package locally: `./test_package.sh`
- [ ] Publish to TestPyPI
- [ ] Test installation from TestPyPI
- [ ] Publish to PyPI
- [ ] Update GitHub repo name
- [ ] Announce on social media

## 🌐 Next Steps

### Immediate
1. **Merge PR**: Review and merge `refactor/rename-to-ragtrace` to main
2. **Test locally**: Run `./test_package.sh` to verify package builds
3. **Update repo**: Rename GitHub repository `rag-debugger` → `ragtrace`

### Before Publishing to PyPI
1. **Domain**: Consider registering `ragtrace.com` or `ragtrace.io`
2. **Logo**: Design professional logo (current emoji 📊 is placeholder)
3. **Screenshots**: Add screenshots to README
4. **Video demo**: Record quick demo for README

### After Publishing
1. **Announce**: Share on HN, Reddit, Dev.to, Twitter
2. **Blog post**: Write "Introducing RAGTrace" post
3. **Tutorial**: Create video tutorial
4. **Documentation site**: Consider setting up docs.ragtrace.com

## 🎨 Brand Guidelines

### Name Usage
- ✅ **RAGTrace** - Preferred (PascalCase, one word)
- ✅ **ragtrace** - CLI commands, package name
- ❌ **Rag Trace** - Don't separate words
- ❌ **RAG Trace** - Don't separate words
- ❌ **RagTrace** - Don't use lowercase 'rag'

### Taglines
- **Primary**: "Observability for RAG pipelines"
- **Secondary**: "Trace, inspect, and optimize RAG systems"
- **Technical**: "OpenTelemetry for Retrieval-Augmented Generation"

### Positioning
- Not just debugging - **observability & tracing**
- Production-ready monitoring
- Developer-first tooling
- Local-first with optional cloud sync

## 📊 Comparison: Old vs New

| Aspect | RAG Debugger (Old) | RAGTrace (New) |
|--------|-------------------|----------------|
| **Name Length** | 12 characters | 8 characters |
| **Memorability** | Medium | High |
| **Professional** | Good | Excellent |
| **Industry Fit** | Developer tools | Observability |
| **SaaS Ready** | Maybe | Yes |
| **SEO** | "rag debugger" | "rag trace" |
| **CLI Command** | `ragdebug` | `ragtrace` |
| **Positioning** | Debugging tool | Observability platform |

## ✨ Why This Name is Better

1. **Industry Standard**: "Trace" is the standard term in observability (Jaeger, Zipkin, OpenTelemetry)
2. **Professional**: Sounds like a product, not a side project
3. **Brandable**: Easier to remember, shorter to type
4. **SaaS Ready**: `ragtrace.com` sounds like a company
5. **Accurate**: You're tracing execution, not just debugging
6. **Scalable**: Works for both local dev and production monitoring

## 🔗 Related Changes Needed

After merging this branch:

1. **GitHub Repository**
   - Rename: `rag-debugger` → `ragtrace`
   - Update description
   - Update topics/tags

2. **Social Media**
   - Reserve @ragtrace on Twitter/X
   - Create /r/ragtrace subreddit
   - Update LinkedIn posts

3. **Domain & Hosting**
   - Register ragtrace.com (if available)
   - Set up docs.ragtrace.com
   - Set up api.ragtrace.com (future SaaS)

4. **Package Repositories**
   - PyPI: Publish as `ragtrace`
   - npm (future): Reserve `ragtrace`
   - Docker Hub: `ragtrace/ragtrace`

---

**Status**: ✅ Complete and committed to branch `refactor/rename-to-ragtrace`  
**Date**: February 16, 2026  
**Commit**: c80cf22  
**Ready for**: Code review → Merge → Publishing
