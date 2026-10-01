#!/bin/sh
set -e

# Apply pending database migrations on startup if requested
if [ "$MIGRATE_ON_STARTUP" = "true" ] || [ "$MIGRATE_ON_STARTUP" = "1" ]; then
    echo "Applying database migrations..."
    python seed/migrate.py
fi

exec "$@"
