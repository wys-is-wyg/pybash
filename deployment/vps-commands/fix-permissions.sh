#!/bin/bash
# Fix shell script permissions on VPS
# Run this after git pull to ensure scripts are executable
# Usage: bash fix-permissions.sh

set -e

echo "=== Fixing shell script permissions ==="

# Fix permissions for all shell scripts
chmod +x app/run.sh
chmod +x app/scripts/*.sh

echo "✅ Permissions fixed for:"
echo "  - app/run.sh"
ls -1 app/scripts/*.sh | while read script; do
    echo "  - $script"
done

echo ""
echo "=== Verifying permissions ==="
ls -l app/run.sh app/scripts/*.sh

echo ""
echo "✅ All scripts are now executable"

