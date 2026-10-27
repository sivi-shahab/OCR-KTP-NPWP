# Deployment Docker Compose

Setup production. Dua container didefinisikan di `docker-compose.yml`:

| Service | Container | Image | Port | Keterangan |
|---|---|---|---|---|
| `api` | `ocr-qwen-api-1` | `ocr-api:latest`, dibangun dari `Dockerfile` (±260 MB) | `8070` (dipublish) | Mode vLLM, tanpa torch, user non-root, ada healthcheck |
| `vllm` | `ocr-qwen-vllm-1` | `vllm/vllm-openai:v0.31.0` | `8071` (hanya di network compose) | Flag sama dengan `run_vllm.sh`; `model/` di-mount read-only |

Keduanya memakai `restart: unless-stopped`, jadi ikut naik lagi setelah reboot server atau crash. `api` baru start setelah healthcheck `vllm` lolos (`depends_on: condition: service_healthy`).

## Prasyarat

- GPU NVIDIA dengan sisa memori ±10 GB, dan [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
- Image `vllm/vllm-openai:v0.31.0` sudah di-pull. Image ini besar; pantau ruang disk Docker sebelum pull versi lain.
- Bobot model Qwen2.5-VL-3B-Instruct di `model/` (±7.5 GB).
- Setup screen **tidak boleh jalan bersamaan**. Port 8070 bentrok, dan GPU tidak cukup untuk dua vLLM:
  ```bash
  screen -S ocr -X quit; screen -S vllm -X quit
  ```

## Menjalankan & menghentikan

```bash
cd /data/ocr-qwen
docker compose up -d --build        # build image api (jika berubah) lalu start semua
docker compose ps                   # kedua service harus "healthy"
curl localhost:8070/health
docker compose down                 # stop & hapus kedua container (image dan model tetap ada)
```

## Melihat status & log

```bash
docker compose ps                   # status + health; api harus punya PORTS 0.0.0.0:8070->8070
docker compose logs -f api          # log API
docker compose logs -f vllm         # log vLLM
docker compose logs --tail 100 vllm # 100 baris terakhir
curl localhost:8070/health          # status API + koneksi ke vLLM
nvidia-smi                          # pemakaian GPU (vLLM ±10 GB)
```

## Restart & update

| Yang di-restart | Cara | Dampak |
|---|---|---|
| API setelah ubah kode/prompt | `docker compose up -d --build api` | Downtime beberapa detik |
| API saja, tanpa perubahan kode | `docker compose restart api` | Downtime beberapa detik |
| API dibuat ulang (mis. container kehilangan network) | `docker compose up -d --force-recreate --no-deps api` | Downtime beberapa detik |
| vLLM (mis. ubah flag di `docker-compose.yml`) | `docker compose up -d vllm` | Inference tidak tersedia ±1–5 menit |
| Semua | `docker compose down && docker compose up -d` | Inference tidak tersedia ±1–5 menit |

`--no-deps` membuat container vLLM tidak ikut di-restart, sehingga model tidak perlu dimuat ulang.

## Variabel opsional

Diset di shell atau file `.env` di folder project:

| Variable | Default | Keterangan |
|---|---|---|
| `API_KEYS` | kosong | Key untuk header `X-API-Key`, dipisah koma. Kosong = autentikasi mati |
| `API_PORT` | `8070` | Port host untuk API |
| `VLLM_GPU_UTIL` | `0.40` | Porsi memori GPU untuk vLLM |
| `VLLM_EAGER` | `enforce-eager` | `no-enforce-eager` untuk mencoba CUDA graphs (lebih cepat, butuh memori lebih dan `nvcc`) |

Variabel API lain (lihat [Konfigurasi](/operasional/konfigurasi)) ditambahkan di bagian `environment:` service `api`.

## Catatan server vLLM

Flag vLLM di `docker-compose.yml` (service `vllm`) sama dengan di `run_vllm.sh`. Jika mengubah salah satunya, samakan yang lain.

- Memakai ±10 GB GPU (`--gpu-memory-utilization 0.40`). Ubah dengan `VLLM_GPU_UTIL=0.35` di `.env`, lalu `docker compose up -d vllm`.
- Berjalan dengan `--enforce-eager` karena server tidak punya `nvcc` (CUDA toolkit). Tanpa flag itu vLLM crash saat startup dengan `Could not find nvcc`.
- `--max-model-len 8192` dan `max_pixels` `2508800` di `--mm-processor-kwargs`, cukup untuk [Kartu Keluarga](/dokumen/kk).
- Maksimal 8 request diproses bersamaan (`--max-num-seqs 8`); sisanya antre di vLLM.
- Port 8071 tidak dipublish ke host.

## Hanya image API

Image API bisa dipakai sendiri dengan vLLM yang jalan di host ([setup screen](/operasional/screen)):

```bash
docker build -t ocr-api:latest .
docker run -d --name ocr-api --network host \
  -e VLLM_URL=http://127.0.0.1:8071 -e PORT=8070 ocr-api:latest
```
