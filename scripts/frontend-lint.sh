#!/bin/bash

# Lint frontend JavaScript code with ESLint
echo "Linting frontend JavaScript with ESLint..."
cd frontend/
npm run lint

if [ $? -ne 0 ]; then
    echo "✗ Frontend linting failed. Fix issues and run again."
    exit 1
fi

echo "✓ Frontend linting passed!"
cd ..
