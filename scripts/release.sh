#!/bin/bash
set -e

# Check if version type is provided
if [ -z "$1" ]; then
    echo "Usage: ./release.sh [major|minor|patch]"
    exit 1
fi

VERSION_TYPE=$1

# Bump version
bump2version $VERSION_TYPE

# Build distribution
python -m build

# Upload to PyPI
twine upload dist/*

echo "Release completed successfully!" 