#!/usr/bin/env bash
# vLLM server for the KTP OCR API. Start this first, then run main.py with:
#   INFERENCE_BACKEND=vllm python main.py
# GPU is shared with other services: --gpu-memory-utilization 0.40 ≈ 9.5 GB of 24 GB.
# --enforce-eager is the default because this server has no CUDA toolkit (nvcc),
# which torch.compile / CUDA-graph mode needs. Once nvcc is installed you can try:
#   VLLM_EXTRA_ARGS="" ./run_vllm.sh
cd "$(dirname "$0")"
# Load .env (see .env.example) without overriding variables already set in the shell.
if [ -f .env ]; then
  while IFS='=' read -r key value; do
    case "$key" in ''|\#*) continue ;; esac
    [ -z "${!key+x}" ] && export "$key=$value"
  done < .env
fi
exec venv-vllm/bin/vllm serve model/ \
  --served-model-name "${VLLM_MODEL:-qwen-ktp}" \
  --host 127.0.0.1 --port 8071 \
  --dtype bfloat16 \
  --gpu-memory-utilization "${VLLM_GPU_UTIL:-0.40}" \
  --max-model-len "${VLLM_MAX_MODEL_LEN:-8192}" \
  --max-num-seqs "${VLLM_MAX_NUM_SEQS:-8}" \
  --limit-mm-per-prompt '{"image":1}' \
  --mm-processor-kwargs '{"min_pixels":200704,"max_pixels":2508800}' \
  ${VLLM_EXTRA_ARGS---enforce-eager}
