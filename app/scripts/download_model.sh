#!/bin/bash

##############################################################################
# Download LLM Model for llama-cpp-python
#
# Downloads a recommended GGUF model for summarization and video idea generation.
# Recommended: Llama 3.2 3B Instruct (Q4_K_M quantization) - ~2.3GB
#
# Usage:
#   bash download_model.sh [model_name]
#
# Model options:
#   - llama-3.2-3b-instruct (default, recommended)
#   - phi-3-mini
#   - mistral-7b-instruct
##############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
MODELS_DIR="$PROJECT_ROOT/app/models"
MODEL_NAME="${1:-llama-3.2-3b-instruct}"

# Model URLs (using HuggingFace CDN)
declare -A MODEL_URLS=(
    ["llama-3.2-3b-instruct"]="https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    ["phi-3-mini"]="https://huggingface.co/bartowski/Phi-3-mini-4k-instruct-GGUF/resolve/main/Phi-3-mini-4k-instruct-Q4_K_M.gguf"
    ["mistral-7b-instruct"]="https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/Mistral-7B-Instruct-v0.2-Q4_K_M.gguf"
)

declare -A MODEL_FILES=(
    ["llama-3.2-3b-instruct"]="Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    ["phi-3-mini"]="Phi-3-mini-4k-instruct-Q4_K_M.gguf"
    ["mistral-7b-instruct"]="Mistral-7B-Instruct-v0.2-Q4_K_M.gguf"
)

# Create models directory
mkdir -p "$MODELS_DIR"

# Check if model URL exists
if [[ ! -v MODEL_URLS[$MODEL_NAME] ]]; then
    echo "Error: Unknown model name: $MODEL_NAME"
    echo "Available models: ${!MODEL_URLS[@]}"
    exit 1
fi

MODEL_URL="${MODEL_URLS[$MODEL_NAME]}"
MODEL_FILE="${MODEL_FILES[$MODEL_NAME]}"
MODEL_PATH="$MODELS_DIR/$MODEL_FILE"

# Check if model already exists
if [ -f "$MODEL_PATH" ]; then
    echo "Model already exists: $MODEL_PATH"
    echo "File size: $(du -h "$MODEL_PATH" | cut -f1)"
    read -p "Do you want to re-download? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping download."
        exit 0
    fi
    rm -f "$MODEL_PATH"
fi

echo "=========================================="
echo "Downloading LLM Model"
echo "=========================================="
echo "Model: $MODEL_NAME"
echo "URL: $MODEL_URL"
echo "Destination: $MODEL_PATH"
echo ""

# Download model using curl or wget
if command -v curl &> /dev/null; then
    echo "Using curl to download..."
    curl -L -o "$MODEL_PATH" "$MODEL_URL" --progress-bar
elif command -v wget &> /dev/null; then
    echo "Using wget to download..."
    wget -O "$MODEL_PATH" "$MODEL_URL" --progress=bar
else
    echo "Error: Neither curl nor wget found. Please install one."
    exit 1
fi

if [ -f "$MODEL_PATH" ]; then
    echo ""
    echo "=========================================="
    echo "Download complete!"
    echo "=========================================="
    echo "Model saved to: $MODEL_PATH"
    echo "File size: $(du -h "$MODEL_PATH" | cut -f1)"
    echo ""
    echo "Update .env file with:"
    echo "LLM_MODEL_PATH=$MODEL_PATH"
    echo ""
else
    echo "Error: Download failed"
    exit 1
fi

