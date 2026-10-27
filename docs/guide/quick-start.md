# Quick start (5 menit)

Halaman ini untuk server yang sudah berisi image Docker dan bobot model (`model/`). Untuk instalasi dari nol, lihat [Deployment Docker Compose](/operasional/deployment).

## 1. Nyalakan service

Kedua container memakai restart policy `unless-stopped`, jadi biasanya sudah jalan setelah server reboot. Untuk menyalakan manual:

```bash
cd /data/ocr-qwen
docker compose up -d     # api baru start setelah vllm healthy (±1–5 menit)
docker compose ps        # kedua service harus "healthy"
```

## 2. Cek kesehatan

```bash
curl localhost:8070/health
```

```json
{"status":"ok","backend":"vllm","model_loaded":true}
```

Jika `status` bernilai `degraded`, vLLM belum siap. Tunggu sebentar atau lihat [Troubleshooting](/operasional/troubleshooting).

## 3. Ambil API key

Semua endpoint `/extract/*` butuh header `X-API-Key`. Key ada di variabel `API_KEYS` dalam file `.env` di folder project. Lihat [Autentikasi](/operasional/autentikasi).

## 4. Kirim dokumen

::: code-group

```bash [KTP]
curl -H "X-API-Key: <key>" \
  -F "file=@ktp.jpg;type=image/jpeg" \
  http://localhost:8070/extract/ktp
```

```bash [NPWP]
curl -H "X-API-Key: <key>" \
  -F "file=@npwp.jpg;type=image/jpeg" \
  http://localhost:8070/extract/npwp
```

```bash [Kartu Keluarga]
curl -H "X-API-Key: <key>" \
  -F "file=@kk.jpg;type=image/jpeg" \
  http://localhost:8070/extract/kk
```

:::

Contoh respons KTP:

```json
{
  "success": true,
  "data": {
    "NIK": "3174010000000901",
    "NAMA": "BUDI SANTOSO",
    "TTL": "JAKARTA, 17-08-1990",
    "JENIS_KELAMIN": "LAKI-LAKI",
    "GOL_DARAH": "O",
    "ALAMAT": "JL. MERDEKA NO. 10",
    "RT_RW": "000/007",
    "KEL_DESA": "KEBAYORAN",
    "KECAMATAN": "KEBAYORAN BARU",
    "AGAMA": "ISLAM",
    "STATUS_PERKAWINAN": "KAWIN",
    "PEKERJAAN": "KARYAWAN SWASTA",
    "KEWARGANEGARAAN": "WNI",
    "BERLAKU_HINGGA": "SEUMUR HIDUP"
  },
  "raw_output": "{\"NIK\":\"3174010000000901\", ...}"
}
```

## 5. Coba lewat Swagger

Buka `http://<host>:8070/docs`, klik **Authorize**, isi API key, lalu pilih endpoint dan klik **Try it out**. Endpoint multipart punya tombol **Choose File** untuk upload gambar.

## Selanjutnya

- [Integrasi dari aplikasi](/tutorial/integrasi): contoh Python, JavaScript, dan Java
- [Referensi API](/guide/api): semua endpoint dan kode HTTP
- Field lengkap per dokumen: [KTP](/dokumen/ktp) · [NPWP](/dokumen/npwp) · [KK](/dokumen/kk)
