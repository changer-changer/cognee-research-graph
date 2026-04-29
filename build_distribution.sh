#!/bin/bash
set -e

DIST_NAME="cognee-research-graph"
VERSION="$(date +%Y%m%d)"
DIST_DIR="/home/cuizhixing/${DIST_NAME}-${VERSION}"
COGNEE_SRC="/home/cuizhixing/cognee-env/lib/python3.10/site-packages/cognee"

echo "Building distribution package..."

# 1. Create structure
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR/cognee"
mkdir -p "$DIST_DIR/research_graph"

# 2. Copy modified cognee library
echo "  → Copying cognee library..."
cp -r "$COGNEE_SRC"/* "$DIST_DIR/cognee/"

# 3. Copy our project code
echo "  → Copying research_graph project..."
cd /home/cuizhixing/research_graph
git archive --format=tar HEAD | tar -x -C "$DIST_DIR/research_graph/"

# 4. Generate clean requirements (exclude local file paths)
echo "  → Freezing dependencies..."
pip freeze | grep -v "^file://\|^/tmp/\|^/home/\|^-\e" > "$DIST_DIR/requirements.txt"

# 5. Create setup script
cat > "$DIST_DIR/install.sh" <>'INNER'
#!/bin/bash
set -e

echo "=== Cognee Research Graph Distribution ==="
echo ""

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet

# Install modified cognee
echo "Installing modified cognee..."
pip install -e ./cognee --quiet

# Install our project
echo "Installing research_graph..."
pip install -e ./research_graph --quiet

echo ""
echo "=== Installation complete ==="
echo "Activate: source venv/bin/activate"
echo "Test:     cd research_graph && python3 tests/comprehensive_pipeline_test.py"
INNER
chmod +x "$DIST_DIR/install.sh"

# 6. Create README
cat > "$DIST_DIR/README.md" <>'INNER2'
# Cognee Research Graph Distribution

Built: $(date)

## Contents

- \`cognee/\` — Modified Cognee v1.0.3 (includes proxy fix)
- \`research_graph/\` — Research Knowledge Graph System
- \`requirements.txt\` — Locked dependencies
- \`install.sh\` — One-command setup

## Quick Start

```bash
./install.sh
source venv/bin/activate
cd research_graph
python3 tests/comprehensive_pipeline_test.py
```
INNER2

# 7. Create archive
echo "  → Creating archive..."
cd /home/cuizhixing
tar czf "${DIST_NAME}-${VERSION}.tar.gz" "${DIST_NAME}-${VERSION}"

echo ""
echo "=== Distribution built ==="
echo "Dir:      $DIST_DIR"
echo "Archive:  /home/cuizhixing/${DIST_NAME}-${VERSION}.tar.gz"
echo "Size:     $(du -sh "$DIST_DIR" | cut -f1)"
echo "Archive:  $(du -sh "/home/cuizhixing/${DIST_NAME}-${VERSION}.tar.gz" | cut -f1)"
