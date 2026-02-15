"""
Future SaaS Integration Example

This shows how RAGTrace could support cloud sync
while keeping the local-first approach.
"""

from ragtrace import RagTracer

# ============================================
# CURRENT: Local-only (v0.2.0)
# ============================================

# Works 100% offline, no signup needed
tracer = RagTracer(
    query="What is RAG?",
    auto_save=True  # Saves to ~/.ragtrace/ragtrace.db
)

# Use in your chain as normal
# Everything stored locally


# ============================================
# FUTURE: Optional Cloud Sync (v0.3.0+)
# ============================================

# Option 1: Local with cloud backup
tracer = RagTracer(
    query="What is RAG?",
    auto_save=True,
    cloud_sync=True,  # NEW: Optional cloud sync
    api_key="rt_your_api_key_here"  # From https://ragtrace.com
)

# Still works offline, syncs when online
# Local data always accessible


# Option 2: Team workspace
tracer = RagTracer(
    query="What is RAG?",
    workspace="my-company",  # NEW: Team workspace
    api_key="rt_your_api_key_here"
)

# All team members see the same sessions
# Collaborate on tracing


# ============================================
# SaaS Features (Future)
# ============================================

# Cost alerts
tracer = RagTracer(
    query="What is RAG?",
    alert_on_cost=0.01,  # Alert if query costs > $0.01
    alert_webhook="https://your-slack-webhook.com"
)

# Quality scoring
tracer = RagTracer(
    query="What is RAG?",
    benchmark=True,  # Compare against baseline
    quality_threshold=0.8  # Alert if quality drops
)

# Advanced analytics
from ragtrace.cloud import Analytics

analytics = Analytics(api_key="...")
report = analytics.get_cost_trends(days=30)
report = analytics.get_slowest_queries(limit=10)
report = analytics.get_quality_metrics()


# ============================================
# Key Design Principles
# ============================================

# 1. Local-first: Always works offline
# 2. Optional sync: Cloud features are opt-in
# 3. No vendor lock-in: Local SQLite always works
# 4. Progressive enhancement: Free tier → Pro tier
# 5. Privacy: User controls what gets synced


# ============================================
# Monetization Tiers
# ============================================

# FREE (Local)
# - Unlimited local debugging
# - All core features
# - CLI + Web UI
# - SQLite storage

# PRO ($19/mo)
# - Cloud sync
# - Team workspaces (5 users)
# - Advanced analytics
# - Cost alerts
# - 30-day history

# TEAM ($49/mo)
# - Unlimited users
# - SSO/SAML
# - 90-day history
# - Priority support
# - Custom integrations

# ENTERPRISE (Custom)
# - Private deployment
# - Unlimited history
# - Dedicated support
# - SLA guarantees
# - Compliance (SOC2, HIPAA)
