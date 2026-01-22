#!/bin/bash
set -e

echo "Running pre-commit checks..."

# Run tests
echo "Running pytest..."
python3 -m pytest tests/

echo "Pre-commit checks passed!"
