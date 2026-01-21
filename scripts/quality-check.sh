#!/bin/bash

# Comprehensive quality check script
# Runs formatting, linting, type checking, and tests for both frontend and backend

set -e

echo "=========================================="
echo "Running Code Quality Checks"
echo "=========================================="
echo ""

# Backend checks
echo "BACKEND CHECKS:"
echo "----------------------------------------"
echo ""

# Run linting
echo "1. Running backend linter (Ruff)..."
bash scripts/lint.sh
echo ""

# Run type checking
echo "2. Running backend type checker (mypy)..."
bash scripts/typecheck.sh
echo ""

# Run tests
echo "3. Running backend tests..."
uv run pytest backend/tests/ -v

if [ $? -ne 0 ]; then
    echo "✗ Tests failed."
    exit 1
fi

echo ""
echo "FRONTEND CHECKS:"
echo "----------------------------------------"
echo ""

# Frontend linting
echo "4. Running frontend linter (ESLint)..."
bash scripts/frontend-lint.sh
echo ""

echo ""
echo "=========================================="
echo "✓ All quality checks passed!"
echo "=========================================="
