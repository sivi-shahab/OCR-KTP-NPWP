# Struktur kode

```
main.py                 entry point (python main.py / uvicorn main:app)
docker-compose.yml      deployment production: api + vllm
Dockerfile              image API (mode vLLM)
run_vllm.sh             server vLLM (setup screen, alternatif)
requirements.txt        dependency dasar (mode vLLM, dipakai Dockerfile)
requirements-hf.txt     + torch/transformers untuk mode hf
model/                  bobot Qwen2.5-VL-3B (±7.5 GB, tidak di-commit)
docs/                   situs dokumentasi ini (VitePress)
ocr_service/
├── config.py           Settings dari environment variable
├── schemas.py          KTPData, NPWPData, KKData, response models
├── documents.py        registry jenis dokumen (KTP, NPWP, KK): schema + prompt + batas per dokumen
├── prompts.py          prompt khusus per dokumen (layout kartu + aturan per field)
├── extraction.py       parsing output model
├── images.py           decode & resize gambar
├── api.py              route FastAPI (1 endpoint per dokumen) & mapping error HTTP
├── static/swagger-ui/  file Swagger UI untuk /docs (tanpa CDN)
└── backends/
    ├── base.py         interface InferenceBackend
    ├── hf.py           transformers (in-process)
    └── vllm.py         klien ke server vLLM (structured JSON output)
backup/                 versi kode sebelumnya (untuk rollback)
```

## Tanggung jawab tiap modul

| Modul | Tanggung jawab |
|---|---|
| `api.py` | Membuat app FastAPI, mendaftarkan dua route per dokumen dari `DOCUMENTS`, cek API key, validasi upload, mapping exception ke kode HTTP |
| `documents.py` | `DocumentType`: key endpoint, model data, prompt, field log, batas piksel/token. `json_schema` menandai semua field (termasuk nested) sebagai `required` |
| `schemas.py` | Model Pydantic per dokumen. `_constrained(...)` menambahkan enum/pattern ke JSON schema tanpa membuat Pydantic menolak nilai lain |
| `prompts.py` | Teks prompt per dokumen; daftar key JSON di akhir dibuat dari model data |
| `extraction.py` | Mengambil objek JSON dari output model dan memvalidasinya ke model data |
| `images.py` | Decode bytes ke gambar dan memperkecil ke batas piksel |
| `backends/` | Abstraksi inference: `generate(image, prompt, json_schema, max_new_tokens)` dan `is_ready()` |

Menambah dokumen atau field: lihat [Menambah dokumen baru](/tutorial/dokumen-baru).

## Situs dokumentasi

Sumber situs ini ada di `docs/`. Untuk menjalankan secara lokal:

```bash
cd docs
npm install
npm run dev       # http://localhost:5173/OCR-KTP-NPWP/
npm run build     # hasil di docs/.vitepress/dist
```

Push ke `main` yang mengubah `docs/` otomatis men-deploy ke GitHub Pages lewat `.github/workflows/docs.yml`.
