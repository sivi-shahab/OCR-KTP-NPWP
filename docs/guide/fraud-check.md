# Deteksi fotokopi & foto layar

Setiap respons `/extract/ktp`, `/extract/npwp`, dan `/extract/kk` (termasuk varian `/base64`) membawa field `fraud_check`. Field ini menandai gambar yang kemungkinan:

- **fotokopi hitam-putih** dari dokumen berwarna, atau
- **foto dari layar** laptop/HP (dokumen ditampilkan di layar lalu difoto).

::: warning Hanya penanda, bukan penolakan
API **tidak pernah menolak** request karena `fraud_check`. OCR tetap berjalan dan `data` tetap terisi. Aplikasi pemanggil yang memutuskan tindak lanjutnya, misalnya mengarahkan `suspicious: true` ke review manual. Deteksi ini heuristik dan belum dikalibrasi dengan foto asli, jadi bisa salah.
:::

## Format

```json
{
  "success": true,
  "data": { "...": "..." },
  "raw_output": "...",
  "fraud_check": {
    "suspicious": true,
    "is_photocopy": false,
    "is_screen_recapture": true,
    "photocopy_score": 0.0,
    "screen_score": 1.0,
    "signals": ["moire_pattern"]
  }
}
```

| Field | Keterangan |
|---|---|
| `suspicious` | `true` jika salah satu detektor menandai gambar. Arahkan ke review manual |
| `is_photocopy` | Dokumen tampak seperti fotokopi hitam-putih (`photocopy_score >= 0.5`) |
| `is_screen_recapture` | Gambar tampak difoto dari layar (`screen_score >= 0.5`) |
| `photocopy_score` | `0` = warna penuh … `1` = tanpa warna |
| `screen_score` | `0` = tanpa pola periodik … `1` = moiré kuat |
| `signals` | Detektor yang menyala: `low_colour`, `moire_pattern` |

`fraud_check` bernilai `null` jika fitur dimatikan (`FRAUD_CHECK=false`) atau pengecekan gagal karena error. Kegagalan pengecekan tidak menggagalkan OCR.

Skor dikembalikan apa adanya, jadi aplikasi boleh memakai ambang sendiri. Contohnya, tandai hanya `screen_score >= 0.8`.

## Cara kerja

Kedua detektor memakai analisis sinyal klasik (numpy, tanpa model), berjalan di CPU container API **bersamaan** dengan OCR di vLLM. Hasil uji di server: tidak ada tambahan latensi yang terukur (±0,5–1 detik CPU, tertutup waktu OCR). GPU tidak dipakai.

### Fotokopi: `low_colour`

Fotokopi hitam-putih menghilangkan warna kartu. Detektor menghitung porsi piksel yang jelas berwarna (saturasi HSV > 0,15) di 60% area tengah gambar, tanpa menghitung teks hitam dan pantulan cahaya. Porsi itu dibandingkan dengan nilai minimal dokumen asli (`min_colour_fraction` di `documents.py`):

| Dokumen | `min_colour_fraction` | Alasan |
|---|---|---|
| KTP | `0.30` | Latar biru muda menutupi sebagian besar kartu |
| NPWP | `0.05` | Kartu dominan putih; hanya logo dan header yang berwarna |
| KK | `0.02` | Kertas putih. **KK TTE yang dicetak hitam-putih juga akan ditandai** |

Keterbatasan: fotokopi **berwarna** tidak terdeteksi. Begitu juga fotokopi yang difoto di atas latar berwarna yang memenuhi tengah gambar.

### Foto layar: `moire_pattern`

Grid subpiksel RGB layar yang difoto kamera menghasilkan **moiré**: pola periodik yang muncul sebagai puncak tajam di spektrum frekuensi (FFT), terutama di kanal warna (pinggiran pelangi). Kertas cetak dan foto biasa tidak punya puncak seperti itu. Detektor merata-rata spektrum per tile 256×256 pada gambar resolusi penuh (maks. 2048 px), lalu mengukur puncak tertinggi di kanal luminance dan dua kanal warna. Area di dekat sumbu frekuensi diabaikan di kanal luminance karena di situ energi baris teks dan garis tabel (KK) terkumpul.

Keterbatasan:
- Moiré bisa hilang jika penyerang mengatur jarak/zoom kamera, atau pada layar OLED ber-PPI sangat tinggi.
- Gambar yang sudah diperkecil atau dikompres berat oleh aplikasi sebelum dikirim kehilangan pola moiré. **Kirim foto asli dari kamera**, jangan thumbnail.
- Gambar lebih kecil dari ±512 px tidak dinilai (`screen_score: 0`).

## Akurasi

Ambang disetel memakai **serangan simulasi** (gambar sintetis yang dijadikan hitam-putih dan simulasi foto layar), dan pada simulasi itu keduanya terpisah dengan jelas. Belum ada pengukuran dengan foto KTP/NPWP/KK asli.

Sebagai acuan dari literatur (dokumen tiruan, dataset DLC-2021): metode moiré klasik mencapai presisi ±95% / recall ±90% untuk foto layar, dan metode warna ±99% / ±85% untuk fotokopi hitam-putih. Di data nyata dengan perangkat yang beragam, hasilnya biasanya lebih rendah.

## Kalibrasi

Ambang ada di kode, bukan env var:

| Ambang | Lokasi | Efek |
|---|---|---|
| `min_colour_fraction` per dokumen | `documents.py` | Turunkan jika dokumen asli sering ditandai fotokopi; naikkan jika fotokopi lolos |
| `_SATURATION_MIN` (`0.15`) | `fraud.py` | Seberapa berwarna sebuah piksel agar dihitung "berwarna" |
| `_PEAK_RANGE` (`2.0`–`3.0`) | `fraud.py` | Tinggi puncak moiré yang dipetakan ke `screen_score` 0–1. Naikkan jika foto biasa ditandai layar |
| `FLAG_THRESHOLD` (`0.5`) | `fraud.py` | Skor minimal agar `is_photocopy` / `is_screen_recapture` bernilai `true` |

Cara menyetel:

1. Kumpulkan contoh nyata per dokumen, misalnya 20–50 per kelompok: **asli**, **fotokopi**, dan **foto dari layar** (beberapa HP dan laptop, jarak dan sudut berbeda). Simpan di folder terpisah per kelompok.
2. Ukur nilai mentahnya dari root repo:

   ```bash
   python3 - <<'PY'
   import glob
   from PIL import Image
   from ocr_service import fraud
   for path in sorted(glob.glob("sampel/*/*.jpg")):
       img = Image.open(path).convert("RGB")
       print(f"{path:50s} warna={fraud._colour_fraction(img):.3f} puncak={fraud._spectral_peak(img):.2f}")
   PY
   ```

3. Pilih ambang yang memisahkan kelompok asli dari serangan, sesuai toleransi Anda terhadap salah tolak dan salah lolos.
4. Ubah nilainya, lalu deploy dengan `docker compose up -d --build api`.

## Langkah berikutnya

Jika dataset sudah cukup (ratusan contoh per kelompok), tambahkan classifier terlatih, misalnya DINOv2/EfficientNet yang di-fine-tune, sebagai detektor ketiga. Literatur melaporkan error 1–4% pada data yang sejenis dengan data latih. Model vision-language untuk OCR (Qwen-VL) **tidak** cocok sebagai detektor: penelitian menunjukkan error zero-shot 25–35%.

## Mematikan

```bash
# .env
FRAUD_CHECK=false
```

lalu `docker compose up -d api`.
