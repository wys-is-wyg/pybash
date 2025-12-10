#!/bin/bash
# Git pull with automatic permission fix
# Usage: bash git-pull-safe.sh

set -e

echo "=== Pulling latest changes ==="
git pull

echo ""
echo "=== Fixing script permissions ==="
chmod +x app/run.sh app/scripts/*.sh

echo ""
echo "✅ Pull complete and permissions fixed"

