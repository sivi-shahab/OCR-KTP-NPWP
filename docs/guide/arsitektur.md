# Arsitektur

## Deployment

Ada dua container dalam satu network compose. API tidak memuat model; semua inference dikirim ke container vLLM, satu-satunya yang memakai GPU.

```mermaid
flowchart LR
    client(["Client / aplikasi lain"])

    subgraph host["Server GPU"]
        subgraph net["compose network: ocr-qwen_default"]
            api["api · ocr-api:latest<br/>main.py · port 8070 (dipublish)<br/>±80 MB RAM, tanpa torch"]
            engine["vllm · vllm/vllm-openai:v0.31.0<br/>vllm:8071 (tidak dipublish)<br/>OpenAI-compatible API"]
        end

        weights[("model/<br/>Qwen2.5-VL-3B<br/>±7.5 GB")]

        subgraph gpu["NVIDIA L40S (24 GB, dipakai bersama)"]
            vram["vLLM ±10 GB"]
            other["Service lain"]
        end
    end

    client -- "POST /extract/ktp · npwp · kk<br/>(multipart / base64)" --> api
    api -- "POST /v1/chat/completions<br/>gambar base64 + prompt + JSON schema" --> engine
    engine -- "mount ./model read-only,<br/>load saat startup" --> weights
    engine --> vram
```

Poin penting:

- **Port vLLM (8071) tidak dipublish.** Hanya bisa diakses dari dalam network compose (`http://vllm:8071`). Hanya API (port 8070) yang terekspos.
- **vLLM mem-batch request bersamaan**, jadi beberapa request sekaligus selesai hampir secepat satu request.
- **Structured output:** vLLM dipaksa menghasilkan JSON sesuai schema dokumen. Lihat [Prompt & batasan output](/guide/prompt).
- Mode alternatif `hf` memuat model langsung di proses API tanpa vLLM. Lihat [Mode HF](/operasional/screen#mode-hf-tanpa-vllm).

## Alur request

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant A as OCR API :8070
    participant V as vLLM :8071
    participant G as GPU

    C->>A: POST /extract/ktp (file gambar + X-API-Key)
    A->>A: Cek API key (401)
    A->>A: Validasi content-type (415) & ukuran ≤ 10 MB (413)
    A->>A: Decode gambar (400 jika rusak)
    A->>A: Resize ke batas piksel dokumen & encode JPEG base64
    A->>V: chat/completions: gambar + prompt KTP + JSON schema KTPData
    V->>G: Vision encoder + generate token (greedy)
    G-->>V: Teks JSON
    V-->>A: {"NIK":"...","NAMA":"...",...}
    A->>A: Parse JSON → KTPData (422 jika gagal)
    A-->>C: 200 {"success":true,"data":{...},"raw_output":"..."}
```

Untuk NPWP dan KK alurnya sama; yang berbeda hanya prompt, schema, dan batasnya:

| Dokumen | Batas piksel gambar | Batas token output |
|---|---|---|
| KTP | `1003520` (±1 MP, `MAX_PIXELS`) | `512` |
| NPWP | `1003520` (±1 MP, `MAX_PIXELS`) | `512` |
| KK | `2508800` (±2.5 MP) | `3072` |

KK berupa lembar A4 dengan teks tabel kecil dan output yang panjang (satu objek per anggota keluarga), sehingga butuh resolusi dan token lebih banyak. Karena itu vLLM dijalankan dengan `--max-model-len 8192`.

## Lapisan kode

```mermaid
flowchart TD
    main["main.py<br/>entry point"] --> api

    subgraph pkg["ocr_service/"]
        api["api.py<br/>route per dokumen, validasi upload, mapping error HTTP"]
        docs["documents.py<br/>registry: KTP, NPWP, KK<br/>(schema + prompt + batas)"]
        prompts["prompts.py<br/>KTP_PROMPT · NPWP_PROMPT · KK_PROMPT"]
        extraction["extraction.py<br/>parse_fields"]
        images["images.py<br/>decode · limit_pixels"]
        schemas["schemas.py<br/>KTPData · NPWPData · KKData"]
        config["config.py<br/>Settings dari env var"]

        subgraph backends["backends/"]
            base["base.py<br/>InferenceBackend (interface)"]
            vllmb["vllm.py<br/>VLLMBackend (HTTP ke vLLM)"]
            hfb["hf.py<br/>HFBackend (transformers, in-process)"]
        end
    end

    api --> docs
    api --> extraction
    api --> images
    api --> config
    api --> base
    docs --> schemas
    docs --> prompts
    prompts --> schemas
    base -.-> vllmb
    base -.-> hfb
```

Backend dipilih sekali saat startup lewat `INFERENCE_BACKEND`. Backend tidak tahu soal KTP/NPWP/KK; ia hanya menerima gambar, prompt, JSON schema, dan batas token. Karena itu menambah jenis dokumen tidak perlu mengubah backend.
