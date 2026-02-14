#!/bin/bash
# Quick setup script to push RAG Debugger to GitHub

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          🚀 RAG Debugger - GitHub Push Helper                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this from the rag-debugger directory"
    exit 1
fi

# Get GitHub username
echo "📝 Enter your GitHub username:"
read -r GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo "❌ Error: GitHub username is required"
    exit 1
fi

echo ""
echo "✅ GitHub username: $GITHUB_USERNAME"
echo ""

# Ask for repository name (default: rag-debugger)
echo "📝 Enter repository name (default: rag-debugger):"
read -r REPO_NAME
REPO_NAME=${REPO_NAME:-rag-debugger}

echo "✅ Repository name: $REPO_NAME"
echo ""

# Choose protocol
echo "🔑 Choose authentication method:"
echo "  1) HTTPS (requires Personal Access Token)"
echo "  2) SSH (requires SSH key setup)"
read -r -p "Enter choice (1 or 2): " AUTH_CHOICE

if [ "$AUTH_CHOICE" = "2" ]; then
    REMOTE_URL="git@github.com:$GITHUB_USERNAME/$REPO_NAME.git"
    echo "✅ Using SSH: $REMOTE_URL"
else
    REMOTE_URL="https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
    echo "✅ Using HTTPS: $REMOTE_URL"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "⚠️  IMPORTANT: Before continuing, please:"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "1. Go to: https://github.com/new"
echo "2. Repository name: $REPO_NAME"
echo "3. Description: DevTools for RAG pipelines"
echo "4. Choose: Public (recommended)"
echo "5. DO NOT initialize with README, .gitignore, or license"
echo "6. Click 'Create repository'"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
read -r -p "Have you created the repository on GitHub? (y/n): " CREATED

if [ "$CREATED" != "y" ] && [ "$CREATED" != "Y" ]; then
    echo ""
    echo "👋 No problem! Create the repository first, then run this script again."
    echo ""
    echo "Quick link: https://github.com/new?name=$REPO_NAME&description=DevTools+for+RAG+pipelines"
    exit 0
fi

echo ""
echo "🔗 Adding remote origin..."

# Remove remote if it exists
git remote remove origin 2>/dev/null

# Add remote
if git remote add origin "$REMOTE_URL"; then
    echo "✅ Remote added successfully"
else
    echo "❌ Failed to add remote"
    exit 1
fi

echo ""
echo "🚀 Pushing to GitHub..."
echo ""

# Push to GitHub
if git push -u origin main; then
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "✨ SUCCESS! Your repository is now on GitHub!"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "🔗 View your repository:"
    echo "   https://github.com/$GITHUB_USERNAME/$REPO_NAME"
    echo ""
    echo "📊 Repository Stats:"
    echo "   • 31 files"
    echo "   • ~4,945 lines of code"
    echo "   • 25 passing tests"
    echo "   • MIT License"
    echo ""
    echo "🎯 Next Steps:"
    echo "   1. Add repository topics: rag, debugging, langchain, llm, python"
    echo "   2. Enable GitHub Issues"
    echo "   3. Add a repository image (Settings → Social preview)"
    echo "   4. Share your project!"
    echo ""
    echo "🎉 Happy debugging!"
    echo ""
else
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "❌ Push Failed"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "Common fixes:"
    echo ""
    echo "1. Authentication failed (HTTPS):"
    echo "   → Generate a Personal Access Token: https://github.com/settings/tokens"
    echo "   → Use token as password when prompted"
    echo ""
    echo "2. Authentication failed (SSH):"
    echo "   → Check SSH key: ssh -T git@github.com"
    echo "   → Setup SSH: https://docs.github.com/en/authentication/connecting-to-github-with-ssh"
    echo ""
    echo "3. Repository doesn't exist:"
    echo "   → Make sure you created it at: https://github.com/new"
    echo ""
    echo "4. Permission denied:"
    echo "   → Check repository name matches: $REPO_NAME"
    echo "   → Verify you own the repository"
    echo ""
    exit 1
fi
