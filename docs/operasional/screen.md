# Alternatif: setup screen (tanpa Docker)

Setup production sebelum Docker Compose: dua proses di GNU screen, masing-masing dengan venv sendiri. Matikan compose dulu (`docker compose down`) sebelum memakai cara ini.

## Prasyarat

- Python 3.10, GPU NVIDIA (24 GB, bisa dipakai bersama service lain)
- Bobot model di `model/` (±7.5 GB). Jika folder kosong, mode `hf` akan mengunduh `Qwen/Qwen2.5-VL-3B-Instruct` dari HuggingFace dan menyimpannya di sini.
- [`uv`](https://github.com/astral-sh/uv)

## Instalasi

Hanya perlu sekali. Ada **dua venv terpisah** supaya versi torch milik vLLM tidak bentrok dengan API:

```bash
cd /data/ocr-qwen

# 1. API (venv/). requirements-hf.txt = dependency dasar + torch/transformers untuk mode hf
uv venv venv --python 3.10
VIRTUAL_ENV=venv uv pip install -r requirements-hf.txt

# 2. Server vLLM (venv-vllm/, ±8 GB)
uv venv venv-vllm --python 3.10
VIRTUAL_ENV=venv-vllm uv pip install vllm
```

## Menjalankan

Urutan: **vLLM dulu, baru API.**

```bash
# 1. Server vLLM di screen "vllm" (log juga ditulis ke vllm.log)
screen -dmS vllm bash -c 'cd /data/ocr-qwen && ./run_vllm.sh 2>&1 | tee -a vllm.log'

# 2. Tunggu siap (±1 menit)
until curl -sf localhost:8071/health; do sleep 3; done; echo vLLM ready

# 3. API di screen "ocr" (interaktif)
screen -S ocr
cd /data/ocr-qwen && source venv/bin/activate
INFERENCE_BACKEND=vllm python main.py
# lepas dari screen: Ctrl-A lalu D

# 4. Cek
curl localhost:8070/health
```

Di setup ini vLLM hanya listen di `127.0.0.1`, jadi tidak terekspos ke jaringan.

## Melihat status & log

```bash
screen -ls                         # harus ada: vllm, ocr
screen -r ocr                      # log API (lepas: Ctrl-A lalu D)
screen -r vllm                     # log vLLM, atau: tail -f vllm.log
curl localhost:8070/health         # status API + koneksi ke vLLM
nvidia-smi                         # pemakaian GPU (vLLM ±10 GB)
```

## Restart

| Yang di-restart | Cara | Dampak |
|---|---|---|
| API saja (mis. setelah ubah kode) | `screen -r ocr` → Ctrl-C → `INFERENCE_BACKEND=vllm python main.py` | Downtime beberapa detik |
| vLLM | `screen -S vllm -X quit`, lalu langkah 1–2 di atas | Semua endpoint tidak bisa inference ±1 menit |
| Semua (mis. setelah reboot) | Langkah 1–4 di atas | — |

Opsi `run_vllm.sh`: `VLLM_GPU_UTIL=0.35 ./run_vllm.sh` untuk mengubah porsi GPU, `VLLM_EXTRA_ARGS="" ./run_vllm.sh` untuk mencoba tanpa `--enforce-eager`.

## Mode HF (tanpa vLLM)

Model dimuat langsung di proses API. Lebih sederhana, tapi request diproses satu per satu dan **tidak ada structured output** (lihat [Prompt & batasan output](/guide/prompt)).

```bash
screen -S vllm -X quit               # matikan vLLM dulu, GPU tidak cukup untuk keduanya
pip install -r requirements-hf.txt   # sekali saja jika torch/transformers belum terpasang
INFERENCE_BACKEND=hf python main.py
```

Mode HF tidak didukung image Docker, karena image API dibangun tanpa torch.
