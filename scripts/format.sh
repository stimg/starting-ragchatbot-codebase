#!/bin/bash

# Format Python code with Black
echo "Formatting Python code with Black..."
uv run black backend/ --line-length=100

echo "✓ Code formatting complete!"
