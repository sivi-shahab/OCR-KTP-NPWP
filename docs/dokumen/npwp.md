# NPWP

Endpoint: `POST /extract/npwp` (multipart) · `POST /extract/npwp/base64` (JSON)

## Field

| Field | Keterangan | Nilai yang diizinkan (mode vLLM) |
|---|---|---|
| `NPWP` | Nomor NPWP sesuai cetakan | `NN.NNN.NNN.N-NNN.NNN` (kartu lama) atau 15–16 digit tanpa pemisah |
| `NAMA` | Nama wajib pajak (orang atau badan) | Bebas |
| `NIK` | NIK jika tercetak di kartu, selain itu `""` | Tepat 16 digit |
| `ALAMAT` | Alamat wajib pajak, semua baris digabung dengan spasi (tanpa nama KPP) | Bebas |
| `KPP` | Kantor Pelayanan Pajak penerbit, mis. `KPP PRATAMA JAKARTA SETIABUDI SATU` | Bebas |
| `TANGGAL_TERDAFTAR` | Tanggal terdaftar sesuai cetakan | Bebas |

Field yang tidak terbaca dikembalikan sebagai `""`.

## Contoh

```bash
curl -H "X-API-Key: <key>" -F "file=@npwp.jpg;type=image/jpeg" \
  http://localhost:8070/extract/npwp
```

```json
{
  "success": true,
  "data": {
    "NPWP": "01.234.567.8-901.000",
    "NIK": "",
    "NAMA": "BUDI SANTOSO",
    "ALAMAT": "JL. MERDEKA NO. 10 RT 001 RW 002 KEBAYORAN BARU JAKARTA SELATAN",
    "KPP": "KPP PRATAMA JAKARTA KEBAYORAN BARU SATU",
    "TANGGAL_TERDAFTAR": "12/03/2015"
  },
  "raw_output": "{\"NPWP\":\"01.234.567.8-901.000\", ...}"
}
```

## Catatan

- Nomor NPWP dikembalikan **sesuai format di kartu**. Kartu lama memakai titik dan strip; untuk menormalkan, hapus semua karakter non-digit di sisi aplikasi.
- `NIK` hanya terisi jika memang tercetak di kartu. Prompt melarang model menyalin nomor NPWP ke `NIK`.
- Jika `NPWP` selalu `""` padahal terbaca jelas, kemungkinan formatnya tidak cocok dengan pattern di `schemas.py`. Lihat [Troubleshooting](/operasional/troubleshooting).
- Waktu proses: ±4.5–5 detik per request (field lebih sedikit dari KTP).
