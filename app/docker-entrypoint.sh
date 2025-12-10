#!/bin/bash
# Docker entrypoint script that fixes permissions on startup
# This ensures scripts are executable even if host filesystem permissions are wrong
# Works for both volume-mounted files (host filesystem) and image files

set -e

# Fix permissions for all shell scripts
# This works on volume mounts because Docker containers typically run as root
# If permissions can't be changed, we continue anyway (scripts might already be executable)
echo "Setting execute permissions for shell scripts..."
chmod +x /app/app/run.sh 2>/dev/null || echo "Warning: Could not set permissions for run.sh"
chmod +x /app/app/scripts/*.sh 2>/dev/null || echo "Warning: Could not set permissions for scripts"

# Execute the main command
exec "$@"

