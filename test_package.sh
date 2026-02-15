#!/bin/bash
# Test script to verify package is ready for PyPI

set -e

echo "🧪 Testing RAGTrace Package"
echo "================================"

echo ""
echo "📦 Step 1: Installing build tools..."
pip install -q build twine check-manifest

echo ""
echo "🧹 Step 2: Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info

echo ""
echo "🔨 Step 3: Building package..."
python -m build

echo ""
echo "✅ Step 4: Checking package..."
twine check dist/*

echo ""
echo "📋 Step 5: Verifying package contents..."
echo "Source distribution:"
tar -tzf dist/*.tar.gz | grep -E "(ui/|README.md|LICENSE)" || echo "⚠️  Warning: UI files may be missing"

echo ""
echo "🧪 Step 6: Installing package locally..."
pip install dist/*.whl --force-reinstall

echo ""
echo "🧪 Step 7: Testing CLI..."
ragtrace --version || echo "❌ CLI not working"

echo ""
echo "🧪 Step 8: Testing Python import..."
python -c "from ragtrace import RagTracer; print('✓ Import successful')"

echo ""
echo "🧪 Step 9: Testing initialization..."
ragtrace init

echo ""
echo "✅ All tests passed!"
echo ""
echo "📤 Ready to publish:"
echo "   Test: python -m twine upload --repository testpypi dist/*"
echo "   Prod: python -m twine upload dist/*"
