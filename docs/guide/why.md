# Mengapa OCR API?

OCR klasik (Tesseract dan sejenisnya) menghasilkan teks mentah. Untuk dokumen identitas, teks mentah belum cukup: aplikasi butuh tahu mana NIK, mana nama, mana alamat, dan itu berarti menulis regex dan aturan posisi yang rapuh untuk tiap jenis kartu.

OCR API memakai model **vision-language** (Qwen2.5-VL-3B-Instruct) yang membaca gambar dan langsung menjawab dalam bentuk JSON per field. Hasilnya:

- **Tidak ada post-processing per kartu.** Model diberi tahu tata letak kartu lewat prompt dan mengisi field langsung.
- **Output terjamin bentuknya.** vLLM menjalankan *constrained decoding* dengan JSON schema, jadi respons selalu JSON valid, semua key selalu ada, dan field seperti `JENIS_KELAMIN` hanya bisa berisi nilai yang diizinkan.
- **Satu service untuk banyak dokumen.** KTP, NPWP, dan Kartu Keluarga memakai model dan server yang sama, dibedakan per endpoint.
- **Berjalan on-premise.** Model dan data tidak keluar dari server. Tidak ada panggilan ke layanan cloud.

## Kapan cocok dipakai

| Cocok | Kurang cocok |
|---|---|
| Onboarding nasabah / pengisian form otomatis dari foto KTP, NPWP, KK | Verifikasi keaslian dokumen (API tidak mendeteksi pemalsuan) |
| Foto dari kamera ponsel atau hasil scan | Foto sangat buram, terpotong, atau sangat miring |
| Volume sedang dengan beberapa request bersamaan | Throughput sangat tinggi (ratusan request per detik) di satu GPU |

::: warning Tetap butuh verifikasi
Model bisa salah baca, terutama pada foto buram atau huruf yang rusak. Untuk proses yang penting, tampilkan hasilnya ke pengguna untuk dikonfirmasi, atau cocokkan dengan sumber data lain (mis. Dukcapil).
:::

## Komponen utama

| Komponen | Peran |
|---|---|
| **FastAPI** (`ocr_service/`) | Endpoint per dokumen, validasi upload, autentikasi, mapping error HTTP |
| **vLLM** `v0.31.0` | Server inference OpenAI-compatible: batching dan structured output |
| **Qwen2.5-VL-3B-Instruct** | Model vision-language (±7.5 GB) yang membaca gambar |
| **Docker Compose** | Menjalankan kedua service dengan restart otomatis dan healthcheck |

Lanjut ke [Quick start](/guide/quick-start) untuk mencobanya.
