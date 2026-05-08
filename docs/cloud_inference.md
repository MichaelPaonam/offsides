# Cloud Inference Runbook

Step-by-step instructions for running Qwen-VL inference on the AMD MI300X GPU droplet.

## Prerequisites

- SSH key: `~/.ssh/id_ed25519_amd`
- Droplet IP: `129.212.183.87` (or check `doctl compute droplet list`)
- Local repo with `scripts/vlm_inference.py` and `data/demo_matches.json`
- Python `openai` package installed locally: `pip install openai`

## 1. SSH Into Droplet

```bash
ssh -i ~/.ssh/id_ed25519_amd root@129.212.183.87
```

## 2. Start vLLM Server

The droplet uses `rocm/vllm:latest` Docker image with GPU passthrough.

### Qwen-VL 7B (fast iteration, ~2s per match)

```bash
docker run -d --name vllm-server \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8000:8000 --shm-size=16g \
  rocm/vllm:latest \
  vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
    --dtype auto --max-model-len 8192 --port 8000 --host 0.0.0.0
```

### Qwen-VL 72B (production quality, ~10-18s per match)

```bash
docker run -d --name vllm-server \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8000:8000 --shm-size=16g \
  rocm/vllm:latest \
  vllm serve Qwen/Qwen2.5-VL-72B-Instruct \
    --dtype auto --max-model-len 8192 --port 8000 --host 0.0.0.0
```

### Wait for Model Loading

72B takes ~3 minutes to load (download weights + compile graphs). Monitor with:

```bash
docker logs -f vllm-server
```

Look for: `Application startup complete.`

### Verify Server Is Ready

```bash
curl -s http://localhost:8000/v1/models | python3 -m json.tool
```

Should return the model ID.

## 3. Set Up SSH Tunnel (from local machine)

```bash
ssh -i ~/.ssh/id_ed25519_amd -f -N -L 8000:localhost:8000 root@129.212.183.87
```

This forwards local port 8000 → droplet port 8000. Verify:

```bash
curl -s http://localhost:8000/v1/models
```

## 4. Run Inference

### All 5 demo matches

```bash
VLM_MODEL="Qwen/Qwen2.5-VL-72B-Instruct" python3 scripts/vlm_inference.py
```

### Single match

```bash
VLM_MODEL="Qwen/Qwen2.5-VL-72B-Instruct" python3 scripts/vlm_inference.py --match "Dortmund_vs_PSG"
```

### Dry run (no API call, just prints prompts)

```bash
python3 scripts/vlm_inference.py --dry-run
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VLM_BASE_URL` | `http://localhost:8000/v1` | vLLM API endpoint |
| `VLM_MODEL` | `Qwen/Qwen2.5-VL-7B-Instruct` | Model to use |
| `VLM_API_KEY` | `EMPTY` | API key (vLLM doesn't require one) |

## 5. Results

Output saved to `data/vlm_results/results.json`. Annotated frames copied to `data/vlm_results/frames/`.

## 6. Troubleshooting

### Container won't start

```bash
# Check if old container exists
docker rm -f vllm-server

# Check GPU is available
rocm-smi --showid
```

### Out of memory

Reduce context length:

```bash
--max-model-len 4096  # instead of 8192
```

### SSH tunnel already bound

```bash
# Kill existing tunnel
lsof -ti:8000 | xargs kill -9
```

### Model download stalls

The first run downloads from HuggingFace. If it stalls, the container has HF cache at `/root/.cache/huggingface/`. You can pre-download:

```bash
docker exec vllm-server huggingface-cli download Qwen/Qwen2.5-VL-72B-Instruct
```

## 7. Switching Models

```bash
# Stop current server
docker stop vllm-server && docker rm vllm-server

# Start with different model (use the 72B or 7B commands above)
docker run -d --name vllm-server ...
```

## 8. Shut Down Droplet

**Important:** The droplet costs $1.99/hr. Shut down when done.

```bash
# From local machine
doctl compute droplet delete <droplet-id> --force

# Or from AMD Developer Cloud web console:
# https://cloud.amd.com → Droplets → Destroy
```

## Quick Reference

```bash
# Full workflow (copy-paste)
ssh -i ~/.ssh/id_ed25519_amd -f -N -L 8000:localhost:8000 root@129.212.183.87
VLM_MODEL="Qwen/Qwen2.5-VL-72B-Instruct" python3 scripts/vlm_inference.py
```

## Cost Estimate

- MI300X: $1.99/hr
- 7B inference (5 matches): ~15s total
- 72B inference (5 matches): ~60s total
- Model loading (72B, first time): ~5 min (includes download)
- Model loading (72B, cached): ~3 min
- Budget: $100 total ≈ 50 hours of GPU time
