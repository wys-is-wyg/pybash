# VPS Deployment Guide

## Post-Deployment Steps

After deploying code to VPS via Git/SCP, you need to download the LLM model separately (it's not in Git due to size).

### Step 1: Download LLM Model on VPS

SSH into your VPS and run:

```bash
cd ~/ai-news-tracker  # or your deployment directory
bash app/scripts/download_model.sh
```

This downloads ~2.3GB model file to `app/models/` directory.

### Step 2: Verify Model Path in .env

Ensure your `.env` file has:

```bash
LLM_MODEL_PATH=/app/app/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf
LLM_N_CTX=2048
LLM_N_THREADS=2
LLM_N_GPU_LAYERS=0
```

### Step 3: Restart Containers

```bash
docker-compose restart python-app
```

### Step 4: Verify Model Loading

Check logs to confirm model loaded:

```bash
docker-compose logs python-app | grep -i "model\|llm"
```

You should see: `"LLM model loaded successfully"`

## Model File Location

- **Local path**: `app/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf`
- **Container path**: `/app/app/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf`
- **Size**: ~2.3GB
- **Git**: Excluded (in `.gitignore`)

## Troubleshooting

### Model not found error
- Check file exists: `ls -lh app/models/`
- Verify path in `.env` matches actual filename
- Ensure Docker volume mounts include `app/models/`

### Out of memory
- Reduce `LLM_N_CTX` to `1024` or `2048`
- Use smaller model (3B instead of 7B)
- Check VPS RAM: `free -h`

### Slow inference
- Normal for CPU-only VPS (2-5 seconds per article)
- Consider upgrading VPS if too slow
- Reduce `LLM_N_CTX` for faster processing

