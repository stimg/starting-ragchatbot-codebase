#!/bin/bash

# Type check Python code with mypy
echo "Running type checks with mypy..."
uv run mypy backend/ --ignore-missing-imports

if [ $? -ne 0 ]; then
    echo "✗ Type checking failed. Fix issues and run again."
    exit 1
fi

echo "✓ Type checking passed!"
