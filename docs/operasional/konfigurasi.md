# Konfigurasi

API dikonfigurasi lewat environment variable (dibaca di `ocr_service/config.py`). Di Docker Compose, tambahkan di bagian `environment:` service `api`.

## Environment variable API

| Variable | Default | Keterangan |
|---|---|---|
| `INFERENCE_BACKEND` | `vllm` | `vllm` (production) atau `hf` (tidak didukung image Docker, karena tanpa torch) |
| `HOST` | `0.0.0.0` | Alamat bind API |
| `PORT` | `8070` | Port API |
| `VLLM_URL` | `http://127.0.0.1:8071` | Alamat server vLLM (di compose: `http://vllm:8071`) |
| `VLLM_MODEL` | `qwen-ktp` | Nama model di server vLLM (`--served-model-name`) |
| `VLLM_TIMEOUT` | `120` | Timeout request ke vLLM (detik) |
| `MIN_PIXELS` / `MAX_PIXELS` | `200704` / `1003520` | Batas resolusi gambar KTP/NPWP. Naikkan `MAX_PIXELS` jika teks kecil salah baca |
| `API_KEYS` | kosong | Key yang diterima di header `X-API-Key`, dipisah koma. Kosong = `/extract/*` terbuka tanpa autentikasi (ada warning di log) |

## Variabel Docker Compose

| Variable | Default | Keterangan |
|---|---|---|
| `API_PORT` | `8070` | Port host untuk API |
| `VLLM_GPU_UTIL` | `0.40` | Porsi memori GPU untuk vLLM |
| `VLLM_EAGER` | `enforce-eager` | `no-enforce-eager` untuk mencoba CUDA graphs |

## Batas per dokumen

Batas berikut diatur di kode (`documents.py`), bukan lewat env var:

| Dokumen | `max_pixels` | `max_new_tokens` |
|---|---|---|
| KTP, NPWP | `MAX_PIXELS` (default `1003520`) | `512` |
| KK | `2508800` | `3072` |

## Menyelaraskan API dan vLLM

Beberapa nilai harus konsisten antara API dan server vLLM:

| Di API | Di vLLM (`docker-compose.yml` / `run_vllm.sh`) | Aturan |
|---|---|---|
| `MAX_PIXELS`, `max_pixels` KK | `max_pixels` di `--mm-processor-kwargs` | Nilai vLLM ≥ batas piksel terbesar di API |
| `VLLM_MODEL` | `--served-model-name` | Harus sama |
| Token gambar + `max_new_tokens` KK | `--max-model-len` | Harus muat (saat ini `8192`) |
