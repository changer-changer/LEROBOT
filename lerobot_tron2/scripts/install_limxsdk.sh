#!/bin/bash
set -e

echo "Installing LimX SDK for Tron2 Robot..."

# Clone the low-level SDK repository
TMP_DIR=$(mktemp -d)
git clone https://github.com/limxdynamics/limxsdk-lowlevel.git $TMP_DIR/limxsdk-lowlevel

# Install for current architecture (assumes amd64, modify if aarch64 is needed)
echo "Installing python3 amd64 wheel..."
pip install $TMP_DIR/limxsdk-lowlevel/python3/amd64/limxsdk-*-py3-none-any.whl

# Cleanup
rm -rf $TMP_DIR

echo "LimX SDK installed successfully."
