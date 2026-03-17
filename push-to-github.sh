#!/bin/bash
# RAGTrace GitHub helper
# Modes:
#   ./push-to-github.sh            → commit + push current branch + open PR URL
#   ./push-to-github.sh --setup    → first-time remote setup (original flow)

set -euo pipefail

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║            🚀 RAGTrace - GitHub Helper                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Sanity check ─────────────────────────────────────────────
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Run this from the ragtrace/ directory"
    exit 1
fi

# ════════════════════════════════════════════════════════════════
# MODE: first-time setup
# ════════════════════════════════════════════════════════════════
if [ "${1:-}" = "--setup" ]; then
    echo "📝 Enter your GitHub username:"
    read -r GITHUB_USERNAME
    [ -z "$GITHUB_USERNAME" ] && echo "❌ Username required" && exit 1

    echo "📝 Enter repository name (default: ragtrace):"
    read -r REPO_NAME
    REPO_NAME=${REPO_NAME:-ragtrace}

    echo "🔑 Auth method — 1) HTTPS  2) SSH"
    read -r -p "Choice (1/2): " AUTH_CHOICE
    if [ "$AUTH_CHOICE" = "2" ]; then
        REMOTE_URL="git@github.com:$GITHUB_USERNAME/$REPO_NAME.git"
    else
        REMOTE_URL="https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
    fi

    echo ""
    echo "⚠️  Create the repo first at https://github.com/new (no README/gitignore)"
    read -r -p "Done? (y/n): " CREATED
    [ "$CREATED" != "y" ] && [ "$CREATED" != "Y" ] && exit 0

    git remote remove origin 2>/dev/null || true
    git remote add origin "$REMOTE_URL"
    echo "✅ Remote set to $REMOTE_URL"

    git push -u origin main
    echo ""
    echo "✅ Pushed! View at: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
    exit 0
fi

# ════════════════════════════════════════════════════════════════
# MODE: daily workflow — branch → stage → commit → push → PR URL
# ════════════════════════════════════════════════════════════════

# Detect remote org/repo from origin URL
ORIGIN_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -z "$ORIGIN_URL" ]; then
    echo "❌ No git remote 'origin' found. Run: ./push-to-github.sh --setup"
    exit 1
fi
# Extract owner/repo from https or ssh URL
GITHUB_SLUG=$(echo "$ORIGIN_URL" | sed -E 's|.*github\.com[:/](.+)\.git|\1|;s|.*github\.com[:/](.+)|\1|')
GITHUB_USERNAME=$(echo "$GITHUB_SLUG" | cut -d'/' -f1)
REPO_NAME=$(echo "$GITHUB_SLUG" | cut -d'/' -f2)

# ── Branch ───────────────────────────────────────────────────
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"
echo ""
echo "📝 Branch name for this change (Enter to keep '$CURRENT_BRANCH'):"
read -r BRANCH_INPUT
BRANCH=${BRANCH_INPUT:-$CURRENT_BRANCH}

if [ "$BRANCH" != "$CURRENT_BRANCH" ]; then
    if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
        git checkout "$BRANCH"
    else
        git checkout -b "$BRANCH"
        echo "✅ Created and switched to branch: $BRANCH"
    fi
fi

# ── Stage & Commit ───────────────────────────────────────────
echo ""
git status --short
echo ""
echo "📝 Stage all changes? (Y/n):"
read -r STAGE_ALL
if [ "${STAGE_ALL:-y}" != "n" ] && [ "${STAGE_ALL:-y}" != "N" ]; then
    git add -A
    echo "✅ All changes staged"
else
    echo "📝 Enter files to stage (space-separated):"
    read -r FILES
    # shellcheck disable=SC2086
    git add $FILES
fi

# Check if there's anything to commit
if git diff --cached --quiet; then
    echo "ℹ️  Nothing to commit — working tree clean"
else
    echo ""
    echo "📝 Commit message:"
    read -r COMMIT_MSG
    [ -z "$COMMIT_MSG" ] && echo "❌ Commit message required" && exit 1
    git commit -m "$COMMIT_MSG"
    echo "✅ Committed"
fi

# ── Push ─────────────────────────────────────────────────────
echo ""
echo "🚀 Pushing '$BRANCH' to origin…"
git push -u origin "$BRANCH"
echo "✅ Pushed"

# ── PR URL ───────────────────────────────────────────────────
DEFAULT_BRANCH=$(git remote show origin 2>/dev/null | grep "HEAD branch" | awk '{print $NF}' || echo "main")
PR_URL="https://github.com/$GITHUB_USERNAME/$REPO_NAME/compare/$DEFAULT_BRANCH...$BRANCH?expand=1"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✨ Done! Open this URL to create the PR:"
echo ""
echo "   $PR_URL"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Auto-open in browser on macOS
if command -v open &>/dev/null; then
    open "$PR_URL"
fi

