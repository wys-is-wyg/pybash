# LLM Model Setup Guide

This project uses `llama-cpp-python` for local LLM inference (summarization and video idea generation).

**Important**: Model files (~2.3GB) are **NOT** committed to Git (see `.gitignore`). You must download them separately.

## Quick Start (Local Development)

1. **Download a model** (recommended: Llama 3.2 3B Instruct):
   ```bash
   bash app/scripts/download_model.sh
   ```

2. **Update `.env` file** with model path:
   ```bash
   LLM_MODEL_PATH=/app/app/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf
   ```

3. **Rebuild Docker container**:
   ```bash
   docker-compose build --no-cache python-app
   docker-compose up -d python-app
   ```

## VPS Deployment (After Code Deployment)

**The model file is NOT in Git**, so after deploying code to VPS, download the model directly on the VPS:

1. **SSH into your VPS**:
   ```bash
   ssh user@your-vps-ip
   ```

2. **Navigate to project directory**:
   ```bash
   cd ~/ai-news-tracker  # or your deployment directory
   ```

3. **Download the model** (this will take a few minutes, ~2.3GB):
   ```bash
   bash app/scripts/download_model.sh
   ```

4. **Verify model downloaded**:
   ```bash
   ls -lh app/models/
   # Should show: Llama-3.2-3B-Instruct-Q4_K_M.gguf (~2.3GB)
   ```

5. **Ensure `.env` has correct path**:
   ```bash
   grep LLM_MODEL_PATH .env
   # Should show: LLM_MODEL_PATH=/app/app/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf
   ```

6. **Restart Python container** (if already running):
   ```bash
   docker-compose restart python-app
   ```

**Note**: The model download happens **after** code deployment, directly on the VPS. This avoids pushing large files to GitHub.

## Recommended Models

### Llama 3.2 3B Instruct (Recommended)
- **Size**: ~2.3 GB
- **Speed**: Fast inference on CPU
- **Quality**: Good for summarization and idea generation
- **Download**: `bash app/scripts/download_model.sh llama-3.2-3b-instruct`

### Phi-3 Mini
- **Size**: ~2.4 GB
- **Speed**: Very fast
- **Quality**: Good for summarization
- **Download**: `bash app/scripts/download_model.sh phi-3-mini`

### Mistral 7B Instruct
- **Size**: ~4.1 GB
- **Speed**: Slower but higher quality
- **Quality**: Excellent for complex tasks
- **Download**: `bash app/scripts/download_model.sh mistral-7b-instruct`

## Manual Download

If the script doesn't work, download manually:

1. Visit [HuggingFace GGUF Models](https://huggingface.co/bartowski)
2. Download a Q4_K_M quantized model (good balance of quality/speed)
3. Place in `app/models/` directory
4. Update `LLM_MODEL_PATH` in `.env`

## Configuration (CPU-Only VPS)

**Important**: This setup is optimized for CPU-only VPS (no GPU required).

Edit `.env` file:

```bash
# Model path (inside container)
LLM_MODEL_PATH=/app/app/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf

# Performance settings (optimized for CPU-only VPS)
LLM_N_CTX=2048          # Context window (2048 = good balance, 4096 uses more RAM)
LLM_N_THREADS=2         # CPU threads (2-4 typical for VPS, match your CPU cores)
LLM_N_GPU_LAYERS=0      # GPU layers (0 = CPU only - REQUIRED for VPS without GPU)
LLM_TEMPERATURE=0.3     # Lower = more deterministic (0.0-1.0)
LLM_TOP_P=0.9           # Nucleus sampling (0.0-1.0)
LLM_TOP_K=40            # Top-k sampling
```

### VPS CPU Thread Recommendations

- **1-2 CPU cores**: `LLM_N_THREADS=1` or `2`
- **2-4 CPU cores**: `LLM_N_THREADS=2` (default, recommended)
- **4+ CPU cores**: `LLM_N_THREADS=4` (if you have RAM to spare)

## Performance Tips (CPU-Only VPS)

- **CPU-only (default)**: Use Q4_K_M quantization, 2-4 threads
- **Low RAM VPS**: Use `LLM_N_CTX=1024` or `2048` (default)
- **More RAM available**: Can increase to `LLM_N_CTX=4096` for longer context
- **Faster inference**: Use smaller models (3B) with Q4 quantization
- **Better quality**: Use Q5 or Q6 quantization (slower but better quality)
- **GPU available** (rare on VPS): Set `LLM_N_GPU_LAYERS=20` or higher

## Troubleshooting

### Model not found
- Check `LLM_MODEL_PATH` in `.env` matches actual file location
- Ensure model file is in `app/models/` directory
- Verify file permissions

### Out of memory
- Reduce `LLM_N_CTX` (try 2048 or 1024)
- Use smaller model or lower quantization
- Reduce `LLM_N_THREADS`

### Slow inference (CPU-only VPS)
- Use smaller model (3B instead of 7B) - **recommended for VPS**
- Reduce context window (`LLM_N_CTX=1024` or `2048`)
- Use Q4 quantization (faster than Q5/Q6)
- Match `LLM_N_THREADS` to your CPU cores (don't exceed)
- **Note**: CPU inference is slower than GPU, but works fine for batch processing

## Model Storage

Models are stored in `app/models/` directory and mounted as a volume in Docker.
This allows models to persist between container rebuilds.

## First Run

On first run, the model will be loaded into memory (takes ~10-30 seconds).
Subsequent requests will be faster as the model stays in memory.

