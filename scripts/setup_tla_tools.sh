#!/usr/bin/env bash
# Download TLA+ tools (tla2tools.jar) for model checking.
# Installs to tla/tools/ directory.

set -euo pipefail

TOOLS_DIR="$(cd "$(dirname "$0")/../tla/tools" 2>/dev/null || echo "$(dirname "$0")/../tla/tools"; pwd -P)"
JAR_PATH="$TOOLS_DIR/tla2tools.jar"
TLA2TOOLS_URL="https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar"

if [ -f "$JAR_PATH" ]; then
    echo "tla2tools.jar already exists at $JAR_PATH"
    java -cp "$JAR_PATH" tlc2.TLC -h 2>&1 | head -1 || true
    exit 0
fi

echo "Downloading tla2tools.jar..."
mkdir -p "$TOOLS_DIR"

if command -v curl &>/dev/null; then
    curl -fSL -o "$JAR_PATH" "$TLA2TOOLS_URL"
elif command -v wget &>/dev/null; then
    wget -q -O "$JAR_PATH" "$TLA2TOOLS_URL"
else
    echo "ERROR: Neither curl nor wget found. Install one and retry."
    exit 1
fi

echo "Verifying download..."
if java -cp "$JAR_PATH" tlc2.TLC -h 2>&1 | grep -q "TLC"; then
    echo "TLA+ tools installed successfully at $JAR_PATH"
else
    echo "WARNING: tla2tools.jar downloaded but TLC verification failed."
    echo "Check Java installation: $(java -version 2>&1 | head -1)"
fi
