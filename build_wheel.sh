#!/bin/bash
set -e

# Get the directory of the script
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

# Clean up previous build artifacts
echo "Cleaning up previous builds..."
rm -rf dist/
rm -rf build/
rm -rf *.egg-info

# Build the package using uv
if command -v uv &> /dev/null; then
    echo "Building with uv..."
    uv build
else
    echo "uv not found, falling back to python build module..."
    # Ensure build module is installed
    python3 -m pip install --upgrade build
    python3 -m build
fi

echo "------------------------------------------------"
echo "Build complete! Wheel file can be found in dist/"
ls -lh dist/*.whl
