#!/bin/bash

# Lint Python code with Ruff
echo "Linting Python code with Ruff..."
uv run ruff check backend/

if [ $? -ne 0 ]; then
    echo "✗ Linting failed. Fix issues and run again."
    exit 1
fi

echo "✓ Linting passed!"
