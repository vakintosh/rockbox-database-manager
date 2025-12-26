#!/usr/bin/env bash
# Wrapper script to run rdbm during development
# Usage: ./rdbm.sh [args...]

cd "$(dirname "$0")"
PYTHONPATH=src:$PYTHONPATH exec python3 -m rockbox_db_manager.cli "$@"
