# Prompt & batasan output

Kualitas hasil ditentukan oleh dua hal: **prompt** yang menjelaskan tata letak dokumen, dan **JSON schema** yang membatasi apa yang boleh dihasilkan model.

## Prompt per dokumen

Setiap dokumen punya prompt sendiri di `ocr_service/prompts.py` (`KTP_PROMPT`, `NPWP_PROMPT`, `KK_PROMPT`). Prompt menjelaskan tata letak kartu dan aturan tiap field, karena salah posisi adalah sumber salah baca yang paling sering.

### KTP

Urutan baris di kartu disebutkan satu per satu. `Gol. Darah` sering kosong; tanpa penjelasan ini model mengisinya dengan nilai baris berikutnya sehingga `ALAMAT`, `RT_RW`, `KEL_DESA`, dst. ikut bergeser satu baris. Prompt juga menegaskan `BERLAKU_HINGGA` diambil dari baris "Berlaku Hingga", bukan dari kota/tanggal terbit di bawah foto.

### NPWP

Menjelaskan format nomor lama dan baru, memisahkan alamat wajib pajak dari nama KPP, dan melarang menyalin nomor NPWP ke `NIK`.

### Kartu Keluarga

Menjelaskan header dan kedua tabel anggota, dan meminta baris N tabel atas digabung dengan baris N tabel bawah menjadi satu anggota, tanpa menggeser nilai ke baris atau kolom tetangga.

### Aturan bersama

- Teks dibaca **persis sesuai cetakan**, tanpa koreksi ejaan.
- Petunjuk angka yang sering tertukar untuk NIK/NPWP/No. KK: `O`→`0`, `I`→`1`, `B`→`8`, `S`→`5`.
- Daftar key JSON di akhir prompt dibuat otomatis dari model data, jadi tidak bisa berbeda dari schema.

## JSON schema (constrained decoding)

JSON schema yang dikirim ke vLLM (`DocumentType.json_schema` di `documents.py`) membatasi output saat decoding:

- **Semua key wajib** (`required`), termasuk di dalam objek anggota KK, sehingga model tidak bisa melewatkan field.
- **Enum/pattern** untuk field dengan nilai terbatas, didefinisikan dengan `_constrained(...)` di `schemas.py`.

Contoh: huruf yang rusak di kartu tidak lagi menghasilkan `PEREMPUA-J`, karena model hanya bisa memilih `LAKI-LAKI`, `PEREMPUAN`, atau `""`.

| Field | Batasan |
|---|---|
| `NIK` (KTP, NPWP, anggota KK), `NO_KK` | Tepat 16 digit |
| `JENIS_KELAMIN` | `LAKI-LAKI`, `PEREMPUAN` |
| `GOL_DARAH` (KTP) | `A`, `B`, `AB`, `O` (boleh dengan `+`/`-`), `-` |
| `RT_RW` | `N/N` s.d. `NNN/NNN` |
| `STATUS_PERKAWINAN` (KTP) | `BELUM KAWIN`, `KAWIN`, `CERAI HIDUP`, `CERAI MATI` |
| `NPWP` | `NN.NNN.NNN.N-NNN.NNN` atau 15–16 digit |
| `KODE_POS` (KK) | Tepat 5 digit |
| `TANGGAL_LAHIR` (anggota KK) | `DD-MM-YYYY` |

String kosong `""` selalu diizinkan, juga untuk field yang dibatasi.

::: warning Hanya di mode vLLM
Batasan ini **hanya berlaku di mode vLLM**. Pydantic tidak memvalidasinya, jadi mode `hf` (tanpa constrained decoding) tetap mengembalikan apa pun yang dibaca model, bukan error.
:::

## Mengubah prompt

1. Edit `ocr_service/prompts.py`.
2. Build ulang dan restart API saja:
   ```bash
   docker compose up -d --build api
   ```
   Kode di-copy ke dalam image, jadi tanpa `--build` perubahan tidak terpakai. vLLM tidak perlu di-restart.
3. Uji dengan beberapa foto asli dan bandingkan hasil sebelum dan sesudah.

::: tip Hati-hati dengan contoh di prompt
Perubahan kecil bisa berdampak besar. Misalnya contoh `JL. MERDEKA` di prompt bisa membuat model ikut "mengoreksi" teks seperti `JL KECAPI V` menjadi `JL. KECAPI V`.
:::
