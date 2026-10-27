# Menambah dokumen baru

Contoh di halaman ini menambahkan **SIM**. Polanya sama untuk dokumen apa pun: model data, prompt, dan satu entri di registry. Endpoint, JSON schema vLLM, dan daftar key di prompt dibuat otomatis.

## 1. Model data (`schemas.py`)

```python
class SIMData(BaseModel):
    NO_SIM: str = _constrained(pattern=r"[0-9]{12,14}")
    NAMA: str = ""
    TTL: str = ""
    JENIS_KELAMIN: str = _constrained(enum=["PRIA", "WANITA"])
    ALAMAT: str = ""
    PEKERJAAN: str = ""
    GOLONGAN: str = _constrained(enum=["A", "B1", "B2", "C", "D"])
    BERLAKU_HINGGA: str = ""


class SIMResponse(BaseModel):
    success: bool
    data: SIMData
    raw_output: str
```

- Pakai `_constrained(enum=...)` atau `_constrained(pattern=...)` untuk field dengan nilai terbatas. String kosong `""` otomatis tetap diizinkan.
- Field bertingkat (seperti `ANGGOTA_KELUARGA` di KK) bisa memakai `list[SubModel] = Field(default_factory=list)`.

## 2. Prompt (`prompts.py`)

Tulis `SIM_PROMPT` yang menjelaskan:

- tata letak kartu: urutan baris dan label tiap field,
- aturan per field: dari baris mana nilainya diambil, format yang diharapkan,
- aturan bersama: baca persis sesuai cetakan, `""` jika tidak terbaca.

Lihat `KTP_PROMPT` sebagai contoh. Daftar key JSON di akhir prompt diisi otomatis dari `SIMData`.

## 3. Daftarkan di registry (`documents.py`)

```python
SIM = DocumentType(
    key="sim",                       # → POST /extract/sim dan /extract/sim/base64
    label="SIM",
    data_model=SIMData,
    response_model=SIMResponse,
    prompt=SIM_PROMPT,
    log_fields=("NO_SIM", "NAMA"),   # field yang dicatat di log setelah sukses
)

DOCUMENTS: tuple[DocumentType, ...] = (KTP, NPWP, KK, SIM)
```

### Dokumen besar

Untuk dokumen dengan teks kecil atau output panjang (seperti KK), isi batas sendiri:

```python
    max_pixels=3200 * 28 * 28,   # piksel gambar maksimum untuk dokumen ini
    max_new_tokens=3072,         # token output maksimum
```

Pastikan nilainya masih di bawah batas server vLLM: `max_pixels` di `--mm-processor-kwargs` dan `--max-model-len` (di `docker-compose.yml` dan `run_vllm.sh`).

## 4. Deploy

```bash
docker compose up -d --build api
```

vLLM tidak perlu di-restart. Endpoint baru langsung muncul di Swagger (`/docs`).

## 5. Uji

```bash
curl -H "X-API-Key: <key>" -F "file=@sim.jpg;type=image/jpeg" \
  http://localhost:8070/extract/sim
```

Uji dengan beberapa foto asli. Jika ada field yang sering salah tempat, perjelas aturannya di prompt (lihat [Prompt & batasan output](/guide/prompt)).

## Menambah field ke dokumen yang sudah ada

Tambahkan field di model data (`KTPData`, `NPWPData`, `KKData`, atau `KKMember`), lalu tambahkan aturan field-nya di `prompts.py`. Daftar key JSON di prompt dan JSON schema vLLM ikut ter-update otomatis. Deploy dengan `docker compose up -d --build api`.
