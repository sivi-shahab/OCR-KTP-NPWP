# Referensi API

Base URL: `http://<host>:8070`

## Ringkasan endpoint

| Method | Path | Auth | Keterangan |
|---|---|---|---|
| `POST` | `/extract/ktp` | `X-API-Key` | KTP, multipart |
| `POST` | `/extract/ktp/base64` | `X-API-Key` | KTP, JSON base64 |
| `POST` | `/extract/npwp` | `X-API-Key` | NPWP, multipart |
| `POST` | `/extract/npwp/base64` | `X-API-Key` | NPWP, JSON base64 |
| `POST` | `/extract/kk` | `X-API-Key` | Kartu Keluarga, multipart |
| `POST` | `/extract/kk/base64` | `X-API-Key` | Kartu Keluarga, JSON base64 |
| `GET` | `/health` | — | Status API dan koneksi ke vLLM |
| `GET` | `/docs` | — | Swagger UI |
| `GET` | `/openapi.json` | — | Spec OpenAPI (bisa diimpor ke Postman) |

## Autentikasi

Kirim header `X-API-Key: <key>` di setiap request `/extract/*`. Tanpa header atau dengan key salah, API membalas `401`. `/health` dan `/docs` tetap terbuka. Detail pengelolaan key ada di [Autentikasi & API key](/operasional/autentikasi).

## Format request

Setiap dokumen punya dua endpoint dengan respons yang sama. Gambar boleh **JPEG, PNG, atau WebP**, maksimal **10 MB**.

### Multipart: `POST /extract/{dokumen}`

Body `multipart/form-data`, gambar di field `file`. Content-type part harus `image/jpeg`, `image/png`, atau `image/webp`.

```bash
curl -H "X-API-Key: <key>" \
  -F "file=@ktp.jpg;type=image/jpeg" \
  http://localhost:8070/extract/ktp
```

### Base64: `POST /extract/{dokumen}/base64`

Body `application/json` dengan field `image`. Nilainya boleh base64 polos atau data URI (`data:image/jpeg;base64,...`).

```json
{ "image": "/9j/4AAQSkZJRgABAQAAAQABAAD..." }
```

```bash
(printf '{"image": "'; base64 -w0 ktp.jpg; printf '"}') > body.json
curl -H "X-API-Key: <key>" -H "Content-Type: application/json" \
  -d @body.json http://localhost:8070/extract/ktp/base64
```

## Format respons

Semua endpoint ekstraksi membalas dengan bentuk yang sama:

```json
{
  "success": true,
  "data": { "...": "field sesuai dokumen" },
  "raw_output": "teks JSON mentah dari model"
}
```

| Field | Keterangan |
|---|---|
| `success` | `true` jika ekstraksi berhasil |
| `data` | Field hasil ekstraksi. Isinya tergantung dokumen: [KTP](/dokumen/ktp) · [NPWP](/dokumen/npwp) · [KK](/dokumen/kk) |
| `raw_output` | Output mentah model, berguna untuk debugging |

Field yang tidak terbaca dikembalikan sebagai string kosong `""`. Semua key selalu ada di `data`.

## Kode HTTP

| HTTP | Arti |
|---|---|
| `200` | Berhasil |
| `400` | File bukan gambar yang valid, atau field `image` bukan base64 yang valid |
| `401` | Header `X-API-Key` tidak ada atau salah |
| `404` | Jenis dokumen tidak dikenal (mis. `/extract/sim`) |
| `413` | File lebih dari 10 MB |
| `415` | Content-type bukan JPEG/PNG/WebP |
| `422` | Body request tidak lengkap (mis. field `file`/`image` tidak ada), atau output model tidak bisa di-parse sebagai JSON |
| `500` | Error inference (mis. vLLM mati) |

Respons error memakai format FastAPI:

```json
{ "detail": "Missing or invalid X-API-Key header." }
```

## `GET /health`

```json
{ "status": "ok", "backend": "vllm", "model_loaded": true }
```

| `status` | Arti |
|---|---|
| `ok` | Backend siap menerima request |
| `degraded` | vLLM tidak bisa dihubungi atau belum selesai memuat model |

Healthcheck Docker memakai endpoint ini.

## Swagger UI

Dokumentasi interaktif tersedia di `http://<host>:8070/docs`:

1. Klik **Authorize**, isi API key.
2. Pilih endpoint, klik **Try it out**.
3. Untuk endpoint multipart, klik **Choose File** dan pilih gambar, lalu **Execute**.

Swagger UI (swagger-ui-dist 5.17.14) disajikan langsung oleh API dari `ocr_service/static/swagger-ui/`, bukan dari CDN, jadi tetap tampil di jaringan tanpa akses internet. `/redoc` dimatikan karena ReDoc hanya tersedia lewat CDN.
