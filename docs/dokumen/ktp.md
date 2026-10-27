# KTP

Endpoint: `POST /extract/ktp` (multipart) · `POST /extract/ktp/base64` (JSON)

## Field

| Field | Keterangan | Nilai yang diizinkan (mode vLLM) |
|---|---|---|
| `NIK` | NIK di bawah header | Tepat 16 digit |
| `NAMA` | Nama lengkap sesuai cetakan | Bebas |
| `TTL` | Tempat/Tgl Lahir, mis. `JAKARTA, 17-08-1990` | Bebas |
| `JENIS_KELAMIN` | Jenis kelamin | `LAKI-LAKI`, `PEREMPUAN` |
| `GOL_DARAH` | Nilai setelah "Gol. Darah" di baris Jenis Kelamin | `A`, `B`, `AB`, `O` (boleh dengan `+`/`-`), `-` |
| `ALAMAT` | Baris "Alamat" saja, tanpa RT/RW, kelurahan, kecamatan | Bebas |
| `RT_RW` | Mis. `006/005` (tanpa spasi) | `N/N` s.d. `NNN/NNN` |
| `KEL_DESA` | Baris "Kel/Desa" | Bebas |
| `KECAMATAN` | Baris "Kecamatan" (bukan kabupaten/kota di header) | Bebas |
| `AGAMA` | Baris "Agama" | Bebas |
| `STATUS_PERKAWINAN` | Status perkawinan | `BELUM KAWIN`, `KAWIN`, `CERAI HIDUP`, `CERAI MATI` |
| `PEKERJAAN` | Pekerjaan sesuai cetakan | Bebas |
| `KEWARGANEGARAAN` | Biasanya `WNI` | Bebas |
| `BERLAKU_HINGGA` | Baris "Berlaku Hingga" (bukan tanggal terbit di bawah foto) | Bebas |

Field yang tidak terbaca dikembalikan sebagai `""`.

## Contoh

```bash
curl -H "X-API-Key: <key>" -F "file=@ktp.jpg;type=image/jpeg" \
  http://localhost:8070/extract/ktp
```

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

## Catatan

- `TTL` dikembalikan apa adanya (tempat dan tanggal dalam satu string). Pisahkan di sisi aplikasi jika perlu.
- `GOL_DARAH` sering kosong (`-`) di kartu. Prompt menjelaskan posisinya supaya baris lain tidak bergeser.
- Waktu proses: ±7 detik per request. Lihat [Performa](/operasional/performa).
- Field bergeser atau salah tempat? Lihat [Prompt & batasan output](/guide/prompt).
