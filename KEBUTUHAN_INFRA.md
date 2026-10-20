# Kebutuhan Infrastruktur — OCR API (KTP & NPWP)

Analisa kebutuhan GPU, VRAM, RAM, CPU, storage, dan software untuk service ini (Qwen2.5-VL-3B-Instruct + vLLM). Angka diambil dari **pengukuran langsung di server produksi** (Oktober 2026: `nvidia-smi`, `ps`, `du`, log startup vLLM). Angka yang merupakan hitungan/perkiraan ditandai *(estimasi)*.

## Ringkasan

| Komponen | Minimum | Rekomendasi | Server saat ini |
|---|---|---|---|
| GPU | NVIDIA, arsitektur Ampere ke atas (dukung bf16), **≥ 12 GB VRAM** | **≥ 16 GB VRAM khusus** (mis. L4 24 GB, A10 24 GB, L40S) | L40S-24Q vGPU 24 GB, **dipakai bersama** |
| VRAM untuk service ini | ±10 GB | 12–16 GB | ±10 GB (`--gpu-memory-utilization 0.40`) |
| RAM sistem | 16 GB | 32 GB | 31 GB |
| CPU | 4 vCPU | 8 vCPU | 8 vCPU |
| Storage (setup screen) | ±20 GB | **50 GB** (SSD) | dipakai ±15 GB |
| Storage (setup Docker) | ±35 GB | **60 GB** | — |
| OS / driver | Linux x86_64, driver NVIDIA ≥ 535 | Driver terbaru yang didukung vLLM | Linux x86_64, driver NVIDIA terbaru |

## 1. GPU & VRAM

### Pemakaian aktual (mode vLLM, produksi)

Dari log startup vLLM dan `nvidia-smi`:

| Komponen | VRAM |
|---|---|
| Bobot model (bf16) | 7.16 GiB |
| Puncak aktivasi (vision encoder + prefill) | 0.44 GiB |
| KV cache (dialokasikan) | 1.65 GiB → 48.016 token |
| CUDA context / non-torch | ±0.25 GiB |
| CUDA graph | 0 (karena `--enforce-eager`) |
| **Total proses `VLLM::EngineCore`** | **±9.8 GiB (10.025 MiB)** |

Catatan vGPU: L40S-24Q menampilkan 24.576 MiB, tetapi yang bisa dipakai hanya 23.76 GiB dan saat startup vLLM hanya tersedia 20.7 GiB (±2.8 GB overhead tersembunyi vGPU + proses lain).

### Kebutuhan KV cache per request

Arsitektur text model: 36 layer, 2 KV head, head dim 128, bf16.

- KV per token = 2 × 36 × 2 × 128 × 2 byte = **36 KiB/token**
- Token per request *(estimasi)*:
  - gambar maks ±1 MP (`max_pixels=1003520`) ÷ (28×28) ≈ **≤ 1.280 token visual**
  - prompt teks ≈ 400–600 token
  - output JSON ≈ 120–200 token
  - total ≈ **±2.000 token ≈ ±72 MB KV per request**
- Dengan `--max-num-seqs 8`: 8 × ±2.000 = ±16.000 token ≈ **±0.6 GB KV cache**.

KV cache 1.65 GiB yang ada sekarang cukup untuk ±24 request bersamaan, jadi **bukan bottleneck**. Bila konkurensi dinaikkan (mis. `--max-num-seqs 16`), VRAM saat ini masih cukup.

### VRAM minimum per skenario *(estimasi)*

| Skenario | VRAM yang dibutuhkan |
|---|---|
| vLLM, 8 request bersamaan (konfigurasi sekarang) | ±9.5–10 GB |
| vLLM, 16 request bersamaan | ±10.5 GB |
| vLLM tanpa `--enforce-eager` (CUDA graph, butuh `nvcc`) | +0.1–0.5 GB |
| Mode HF (transformers, 1 request sekali jalan) | ±9–10 GB (tidak boleh jalan bersamaan dengan vLLM) |
| Upgrade ke Qwen2.5-VL-7B (bf16) | ±17 GB bobot → butuh GPU **≥ 24 GB khusus** |

**Rekomendasi:** GPU dengan **≥ 16 GB VRAM yang tidak dibagi** dengan service lain memberi ruang aman untuk lonjakan konkurensi dan resolusi gambar lebih tinggi. GPU 12 GB masih bisa, tetapi `--gpu-memory-utilization` harus disetel ulang (mis. ±0.85) dan tidak ada ruang untuk service lain.

GPU yang **tidak** disarankan: T4 / V100 (tidak mendukung bf16 secara native → harus `--dtype float16`, lebih lambat), GPU < 12 GB.

### Kecepatan

| Skenario | Waktu (terukur) |
|---|---|
| 1 request KTP | ±7 detik |
| 1 request NPWP | ±4.5–5 detik |
| 4 request bersamaan (2 KTP + 2 NPWP) | ±7.5 detik total |

Throughput generate di log vLLM: ±15–27 token/detik per request. Bottleneck adalah kecepatan decode di vGPU dalam mode eager, bukan VRAM.

Kapasitas *(estimasi)*: dengan 8 request di-batch dan ±8–9 detik per batch, sekitar **±0.9 request/detik ≈ ±3.000 dokumen/jam** pada konfigurasi sekarang. Untuk kapasitas lebih tinggi: pasang CUDA toolkit (`nvcc`) agar bisa memakai CUDA graph, gunakan GPU khusus (bukan vGPU yang dibagi), atau tambah instance vLLM di GPU lain.

## 2. RAM sistem

| Proses | RSS (terukur) |
|---|---|
| vLLM API server (`vllm serve`) | ±2.0 GB |
| vLLM `EngineCore` | ±2.3 GB |
| OCR API (`main.py`, FastAPI tanpa torch) | ±57 MB |
| **Total service** | **±4.4 GB** |

Saat startup, file bobot (6.99 GiB) dibaca lewat page cache, jadi butuh ±7 GB RAM bebas sementara. Mode HF memakai RAM lebih besar (torch + transformers di proses API, ±3–4 GB *(estimasi)*).

- **Minimum:** 16 GB
- **Rekomendasi:** 32 GB (terutama jika server dipakai bersama service lain)
- Swap: server saat ini tanpa swap; tidak wajib.

## 3. CPU

Pekerjaan CPU ringan: decode/resize gambar (Pillow), encode base64, tokenisasi, dan scheduler vLLM.

- **Minimum:** 4 vCPU
- **Rekomendasi:** 8 vCPU (sama dengan server sekarang), x86_64 dengan AVX2.

## 4. Storage

### Rincian pemakaian (terukur)

| Item | Ukuran | Lokasi |
|---|---|---|
| Bobot model `model/` (`model.safetensors` + tokenizer) | 7.1 GB | `model/` |
| venv vLLM (`venv-vllm/`, termasuk torch + CUDA libs) | 7.9 GB | `venv-vllm/` |
| venv API (`venv/`, tanpa torch) | 75 MB | `venv/` |
| Cache vLLM | 27 MB | cache user (`.cache/vllm`) |
| Log vLLM | 73 KB (bertambah terus) | `vllm.log` |
| **Total setup screen** | **±15 GB** | |

### Tambahan sesuai mode

| Item | Ukuran *(estimasi)* |
|---|---|
| Mode HF: torch + transformers di `venv/` (`requirements-hf.txt`) | +5–7 GB |
| Docker: image `vllm/vllm-openai:v0.31.0` | ±9 GB terkompresi, ±20–25 GB setelah diekstrak |
| Docker: image `ocr-api:latest` | ±260 MB |
| Cache unduhan sementara saat instalasi (uv/pip) | ±5–10 GB (bisa dihapus setelahnya) |
| Model lebih besar (Qwen2.5-VL-7B) | +16 GB |

### Rekomendasi

- **50 GB** khusus untuk service (setup screen), **60 GB** jika memakai Docker. Sisakan ruang untuk log, cache build, dan model versi berikutnya.
- SSD/NVMe disarankan: loading bobot 7 GB butuh ±4.6 detik di disk XFS sekarang; total cold start vLLM ±1 menit.
- Service tidak menyimpan gambar upload ke disk (diproses di memori), jadi storage **tidak bertambah** seiring jumlah request — kecuali log.

### Catatan disk

- Image vLLM Docker butuh ±25 GB di volume Docker `data-root`. Pastikan volume tersebut punya ruang cukup sebelum memakai `docker compose`; jika tidak, pindahkan `data-root` ke volume yang lebih besar.
- Cek sisa ruang di volume service sebelum menambah model atau venv baru.
- `vllm.log` ditulis dengan `tee -a` tanpa rotasi; pasang `logrotate` untuk jangka panjang.

## 5. Software

| Komponen | Versi saat ini | Catatan |
|---|---|---|
| OS | Linux x86_64 | |
| Driver NVIDIA | versi yang mendukung CUDA 12.x/13.x | vLLM 0.31 membundel CUDA runtime sendiri di wheel torch |
| CUDA toolkit (`nvcc`) | **tidak terpasang** | Karena itu vLLM wajib `--enforce-eager`. Memasang toolkit membuka opsi CUDA graph / `torch.compile` (lebih cepat) |
| Python | 3.10 | dua venv terpisah (`venv/`, `venv-vllm/`) |
| vLLM | 0.31.0 | |
| `uv` | terpasang | untuk instalasi venv |
| Docker + NVIDIA Container Toolkit | terpasang | hanya untuk setup Docker |

## 6. Jaringan & port

| Port | Bind | Keterangan |
|---|---|---|
| 8000 | `0.0.0.0` | OCR API — satu-satunya yang perlu dibuka ke client |
| 8071 | `127.0.0.1` | vLLM — internal saja |

Bandwidth: upload maks 10 MB per request; gambar yang dikirim ke vLLM sudah di-resize ke ±1 MP (biasanya < 500 KB base64) lewat loopback. Akses internet hanya diperlukan saat instalasi (pip/uv, image Docker, unduh model dari HuggingFace).

## 7. Rekomendasi spesifikasi server baru (dedicated)

Jika service ini dipindah ke server/VM khusus:

| Komponen | Spesifikasi |
|---|---|
| GPU | 1× NVIDIA L4 24 GB / A10 24 GB / L40S (atau vGPU profil ≥ 16 GB, tidak dibagi) |
| CPU | 8 vCPU |
| RAM | 32 GB |
| Disk | 100 GB SSD (OS ±30 GB + service 50–60 GB + cadangan) |
| OS | Ubuntu 22.04/24.04 LTS, driver NVIDIA terbaru, CUDA toolkit terpasang |
| Jaringan | Port 8000 terbuka untuk client internal |

Dengan GPU khusus, `--gpu-memory-utilization` bisa dinaikkan (mis. 0.85) dan `--max-num-seqs` diperbesar untuk throughput lebih tinggi.
