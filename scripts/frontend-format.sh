#!/bin/bash

# Format frontend JavaScript code with Prettier
echo "Formatting frontend JavaScript with Prettier..."
cd frontend/
npm run format

echo "✓ Frontend code formatting complete!"
cd ..
