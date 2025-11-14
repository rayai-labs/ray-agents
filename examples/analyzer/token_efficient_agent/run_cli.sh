#!/bin/bash
# Run the CLI with proper stdin handling

cd "$(dirname "$0")"

# Get the uv Python environment
UV_PYTHON=$(uv run --no-sync which python)

# Run with that Python directly (not through uv run)
exec "$UV_PYTHON" cli.py "$@"
