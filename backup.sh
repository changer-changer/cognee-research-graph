#!/bin/bash
set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/cuizhixing/backups/research_graph_${DATE}"
mkdir -p "$BACKUP_DIR"

echo "=== Backing up project code ==="
# Project source code (git tracked)
cd /home/cuizhixing/research_graph
git archive --format=tar.gz HEAD > "$BACKUP_DIR/research_graph_src.tar.gz"

echo "=== Backing up environment ==="
# Python environment packages list
pip freeze > "$BACKUP_DIR/requirements.txt"

echo "=== Backing up Cognee patches ==="
# Modified Cognee files
cp -r /home/cuizhixing/research_graph/cognee_patches "$BACKUP_DIR/"

echo "=== Backing up test outputs ==="
# Latest test results
cp -r /home/cuizhixing/research_graph/tests/output "$BACKUP_DIR/test_outputs"

echo "=== Backup complete ==="
echo "Location: $BACKUP_DIR"
echo "Size: $(du -sh $BACKUP_DIR | cut -f1)"
