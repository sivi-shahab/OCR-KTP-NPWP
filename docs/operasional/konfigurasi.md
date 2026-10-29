# Konfigurasi

API dikonfigurasi lewat environment variable (dibaca di `ocr_service/config.py`). Di Docker Compose, variabel yang diteruskan ke API ada di bagian `environment:` service `api`.

## File `.env`

Semua variabel didokumentasikan di `.env.example` (di root repo). Untuk setup baru:

```bash
cp .env.example .env && chmod 600 .env   # lalu isi API_KEYS
```

`.env` dibaca oleh `docker-compose.yml`, `run_vllm.sh`, dan `main.py`; variabel yang sudah diset di shell menang atas `.env`. File ini masuk `.gitignore` dan `.dockerignore`, jadi tidak pernah di-commit atau ikut masuk image.

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
| `VISION_MAX_PIXELS` | `2508800` | Batas atas vision processor (backend `hf`); minimal sebesar batas piksel KK |
| `MAX_NEW_TOKENS` | `512` | Batas token output KTP/NPWP |
| `MAX_UPLOAD_MB` | `10` | Ukuran maksimal gambar yang diupload |
| `MODEL_DIR` | `model/` | Folder bobot model (backend `hf`) |
| `MODEL_ID` | `Qwen/Qwen2.5-VL-3B-Instruct` | Model Hugging Face yang diunduh ke `MODEL_DIR` jika kosong (backend `hf`) |
| `API_KEYS` | kosong | Key yang diterima di header `X-API-Key`, dipisah koma. Kosong = `/extract/*` terbuka tanpa autentikasi (ada warning di log) |

## Variabel Docker Compose

| Variable | Default | Keterangan |
|---|---|---|
| `API_PORT` | `8070` | Port host untuk API |
| `VLLM_GPU_UTIL` | `0.40` | Porsi memori GPU untuk vLLM |
| `VLLM_EAGER` | `enforce-eager` | `no-enforce-eager` untuk mencoba CUDA graphs |
| `VLLM_MODEL` | `qwen-ktp` | Dipakai untuk `--served-model-name` vLLM **dan** API, sehingga selalu sama |
| `VLLM_MAX_MODEL_LEN` | `8192` | `--max-model-len` vLLM |
| `VLLM_MAX_NUM_SEQS` | `8` | Maksimal request diproses bersamaan di vLLM |
| `VLLM_IMAGE` | `vllm/vllm-openai:v0.31.0` | Image Docker vLLM |

## Batas per dokumen

Batas berikut diatur di kode (`documents.py`), bukan lewat env var:

| Dokumen | `max_pixels` | `max_new_tokens` |
|---|---|---|
| KTP, NPWP | `MAX_PIXELS` (default `1003520`) | `MAX_NEW_TOKENS` (default `512`) |
| KK | `2508800` | `3072` |

## Menyelaraskan API dan vLLM

Beberapa nilai harus konsisten antara API dan server vLLM:

| Di API | Di vLLM (`docker-compose.yml` / `run_vllm.sh`) | Aturan |
|---|---|---|
| `MAX_PIXELS`, `max_pixels` KK | `max_pixels` di `--mm-processor-kwargs` | Nilai vLLM ≥ batas piksel terbesar di API |
| `VLLM_MODEL` | `--served-model-name` | Harus sama (di compose dan `run_vllm.sh` otomatis dari `VLLM_MODEL` yang sama) |
| Token gambar + `max_new_tokens` KK | `--max-model-len` (`VLLM_MAX_MODEL_LEN`) | Harus muat (default `8192`) |
