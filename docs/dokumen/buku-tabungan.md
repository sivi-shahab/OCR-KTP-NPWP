# Buku Tabungan

Endpoint: `POST /extract/buku-tabungan` (multipart) · `POST /extract/buku-tabungan/base64` (JSON)

Cover atau halaman identitas buku tabungan dari bank mana pun (BCA, BNI, Mandiri, BRI, BTN, Bank Mega, dll). Satu prompt dipakai untuk semua bank; bank dikenali dari logo/nama di gambar.

## Field

| Field | Keterangan | Nilai yang diizinkan (mode vLLM) |
|---|---|---|
| `BANK` | Nama bank sesuai logo/judul | Bebas |
| `NAMA_NASABAH` | Nama pemilik rekening sesuai cetakan | Bebas |
| `NO_REKENING` | Nomor rekening, hanya digit (spasi, titik, strip dihapus) | 8–18 digit |
| `JENIS_TABUNGAN` | Nama produk tabungan, mis. `TAPRES`, `Britama` | Bebas |
| `CABANG` | Nama cabang/KCP/unit jika tercetak | Bebas |
| `KODE_CABANG` | Kode cabang jika tercetak | Bebas |

Field yang tidak terbaca atau tidak tercetak dikembalikan sebagai `""`.

## Contoh

```bash
curl -H "X-API-Key: <key>" -F "file=@buku.jpg;type=image/jpeg" \
  http://localhost:8070/extract/buku-tabungan
```

Respons memakai bentuk yang sama dengan dokumen lain: `success`, `data`, `raw_output`, `fraud_check`.

## Catatan

- **Belum diuji dengan buku tabungan asli.** Prompt dan skema disusun dari pola endpoint lain dan riset; ukur akurasi pada sampel berlabel Anda sebelum produksi.
- Referensi terdekat (API buku bank iApp, Thailand) melaporkan nama bank ±99,5% dan nomor rekening ±96,8% benar, tetapi nama pemilik ±52,6% dan cabang ±63,1%. Perlakukan `NAMA_NASABAH` dan `CABANG` sebagai pendukung dan verifikasi di sisi aplikasi. Angka itu dari vendor, bukan audit, dan untuk bank Thailand.
- Panjang nomor rekening per bank **tidak divalidasi**: klaim panjang digit per bank tidak lolos verifikasi riset. Tambahkan aturan per bank hanya dari sumber resmi.
- `fraud_check` memakai ambang warna `0.05` yang belum dikalibrasi dengan cover asli (desain tiap bank berbeda). Perlakukan sebagai petunjuk review. Lihat [Deteksi fotokopi & layar](/guide/fraud-check).
- Privasi (UU PDP): nomor rekening dan nama adalah data keuangan pribadi. Server tidak menulis nama/nomor ke log, tetapi `raw_output` memuat semuanya; simpan hanya jika ada dasar pemrosesan yang sah, dengan retensi minimal.
