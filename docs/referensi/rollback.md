# Rollback

Folder `backup/` menyimpan versi kode sebelumnya. Versi lama hanya punya endpoint KTP (tanpa `/extract/npwp` dan `/extract/kk`).

```bash
cp backup/main_single_file_vllm.py main.py   # versi 1 file dengan dukungan vLLM
cp backup/main_original_hf.py main.py        # versi asli (HF saja, matikan vLLM dulu)
```

Lalu:

```bash
docker compose up -d --build api
```

Versi HF tidak bisa jalan di image Docker (tanpa torch); pakai [setup screen](/operasional/screen#mode-hf-tanpa-vllm).

`backup/ktp_ocr_package/` adalah versi package KTP-only sebelum digabung dengan NPWP.

## Rollback lewat git

Cara yang lebih bersih untuk kembali ke versi sebelumnya adalah checkout commit atau tag yang diinginkan, lalu build ulang:

```bash
git log --oneline              # cari commit tujuan
git checkout <commit> -- ocr_service main.py
docker compose up -d --build api
```

Jika versi tujuan memakai flag vLLM berbeda (mis. sebelum KK, `--max-model-len 4096`), samakan juga `docker-compose.yml` lalu `docker compose up -d vllm`.
