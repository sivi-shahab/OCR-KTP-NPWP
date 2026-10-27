# Troubleshooting

## Service

| Gejala | Penyebab / solusi |
|---|---|
| `/health` → `degraded` | vLLM mati atau belum siap. Cek `docker compose ps` dan `docker compose logs --tail 100 vllm`, lalu `docker compose up -d vllm` |
| API tidak bisa diakses di port 8070, `docker compose ps` menunjukkan api `unhealthy` dengan kolom PORTS kosong, log API: `vLLM backend at http://vllm:8071 not reachable yet` | Container api kehilangan network compose (tidak punya IP, nama `vllm` tidak bisa di-resolve). Pernah terjadi setelah container lama di-start ulang. Buat ulang: `docker compose up -d --force-recreate --no-deps api` |
| `docker compose up`: `port is already allocated` | Setup screen masih jalan. `screen -S ocr -X quit; screen -S vllm -X quit` |
| `Address already in use` (setup screen) | Port dipakai proses lain, mis. container compose: `docker compose ps`, `ss -ltnp \| grep 807` |

## vLLM

| Gejala | Penyebab / solusi |
|---|---|
| `Free memory on device ... is less than desired` | GPU dipakai proses lain (`nvidia-smi`). Turunkan `VLLM_GPU_UTIL` atau hentikan proses lain |
| `No available memory for the cache blocks` | `VLLM_GPU_UTIL` terlalu kecil untuk bobot model (±7.5 GB) dan context 8192; naikkan sedikit |
| `Could not find nvcc` | Pastikan `--enforce-eager` aktif (default di `docker-compose.yml` dan `run_vllm.sh`) |
| Request KK gagal dengan error panjang context | `--max-model-len` vLLM lebih kecil dari token gambar + `max_new_tokens` KK. Pastikan `8192` di `docker-compose.yml` / `run_vllm.sh` |

## Kualitas hasil

| Gejala | Penyebab / solusi |
|---|---|
| Field salah baca pada foto buram/kecil | Naikkan `MAX_PIXELS` (API) dan `max_pixels` di `--mm-processor-kwargs` vLLM |
| Field KTP bergeser satu baris atau diambil dari tempat yang salah | Perjelas aturan field tersebut di `prompts.py`, lalu `docker compose up -d --build api`. Lihat [Prompt & batasan output](/guide/prompt) |
| Field selalu `""` padahal terbaca jelas | Nilai di kartu tidak cocok dengan enum/pattern di `schemas.py` (mis. format NPWP baru). Longgarkan batasannya, lalu `docker compose up -d --build api` |
| Anggota KK tertukar kolom atau kurang satu | Foto miring/buram atau terpotong. Minta foto seluruh lembar yang tegak dan tajam |
| Perubahan prompt tidak berpengaruh | Kode di-copy ke image; jalankan dengan `--build`: `docker compose up -d --build api` |

## Client

| Gejala | Penyebab / solusi |
|---|---|
| `401` | Header `X-API-Key` tidak dikirim atau key tidak ada di `API_KEYS`. Lihat [Autentikasi](/operasional/autentikasi) |
| `415` | Content-type part multipart bukan `image/jpeg`/`png`/`webp`. Di curl tambahkan `;type=image/jpeg` |
| `422` dengan detail `Field required` | Nama field salah: multipart harus `file`, base64 harus `image` |
| Timeout di client (terutama KK) | Naikkan timeout client ke 120 detik |
| Error CORS di browser | API tidak mengaktifkan CORS. Panggil dari backend. Lihat [Integrasi](/tutorial/integrasi) |
