# Integrasi dari aplikasi

Tutorial ini menunjukkan cara memanggil OCR API dari aplikasi lain. Semua contoh memakai endpoint KTP; untuk dokumen lain cukup ganti `ktp` dengan `npwp`, `kk`, atau `buku-tabungan`.

## Yang dibutuhkan

- Base URL API, mis. `http://<host>:8070`
- API key (header `X-API-Key`)
- Foto dokumen JPEG, PNG, atau WebP, maksimal 10 MB

## Multipart atau base64?

| Pakai | Jika |
|---|---|
| Multipart `/extract/{dokumen}` | Gambar ada sebagai file (upload dari form, file di disk). Lebih hemat ukuran request |
| Base64 `/extract/{dokumen}/base64` | Gambar sudah berupa string base64, mis. dari kamera di aplikasi web/mobile atau dari sistem lain yang hanya bisa kirim JSON |

## Python

::: code-group

```python [multipart]
import requests

API_URL = "http://<host>:8070"
API_KEY = "<key>"

with open("ktp.jpg", "rb") as f:
    resp = requests.post(
        f"{API_URL}/extract/ktp",
        headers={"X-API-Key": API_KEY},
        files={"file": ("ktp.jpg", f, "image/jpeg")},
        timeout=120,
    )

resp.raise_for_status()
data = resp.json()["data"]
print(data["NIK"], data["NAMA"])
```

```python [base64]
import base64
import requests

API_URL = "http://<host>:8070"
API_KEY = "<key>"

with open("ktp.jpg", "rb") as f:
    encoded = base64.b64encode(f.read()).decode()

resp = requests.post(
    f"{API_URL}/extract/ktp/base64",
    headers={"X-API-Key": API_KEY},
    json={"image": encoded},
    timeout=120,
)

resp.raise_for_status()
print(resp.json()["data"])
```

:::

## JavaScript / TypeScript (Node.js 18+)

```js
import { readFile } from 'node:fs/promises'

const image = await readFile('ktp.jpg')
const form = new FormData()
form.append('file', new Blob([image], { type: 'image/jpeg' }), 'ktp.jpg')

const resp = await fetch('http://<host>:8070/extract/ktp', {
  method: 'POST',
  headers: { 'X-API-Key': process.env.OCR_API_KEY },
  body: form,
  signal: AbortSignal.timeout(120_000),
})
const { data } = await resp.json()
console.log(data.NIK, data.NAMA)
```

::: warning Panggil dari backend, bukan browser
API tidak mengaktifkan CORS, jadi `fetch` langsung dari halaman web di domain lain akan diblok browser. Selain itu API key akan terlihat oleh pengguna. Teruskan upload dari frontend ke backend Anda, lalu backend yang memanggil OCR API.
:::

## Java (11+)

```java
import java.net.URI;
import java.net.http.*;
import java.nio.file.*;
import java.time.Duration;
import java.util.Base64;

var image = Base64.getEncoder().encodeToString(Files.readAllBytes(Path.of("ktp.jpg")));
var body = "{\"image\":\"" + image + "\"}";

var request = HttpRequest.newBuilder(URI.create("http://<host>:8070/extract/ktp/base64"))
    .header("X-API-Key", "<key>")
    .header("Content-Type", "application/json")
    .timeout(Duration.ofSeconds(120))
    .POST(HttpRequest.BodyPublishers.ofString(body))
    .build();

var response = HttpClient.newHttpClient().send(request, HttpResponse.BodyHandlers.ofString());
System.out.println(response.statusCode() + " " + response.body());
```

## Menangani error

```python
resp = requests.post(...)

if resp.status_code == 200:
    data = resp.json()["data"]
elif resp.status_code in (400, 413, 415):
    # Masalah di gambar: minta pengguna upload ulang
    print("Gambar tidak valid:", resp.json()["detail"])
elif resp.status_code == 401:
    # API key salah: masalah konfigurasi, jangan di-retry
    raise RuntimeError("API key ditolak")
elif resp.status_code == 422:
    # Output model tidak bisa di-parse: retry sekali, atau minta foto yang lebih jelas
    ...
else:
    # 500: vLLM bermasalah, retry dengan backoff
    ...
```

Daftar lengkap kode ada di [Referensi API](/guide/api#kode-http).

## Menangani `fraud_check`

API **tidak menolak** dokumen yang dicurigai; keputusan ada di aplikasi Anda. Pola yang disarankan: data tetap dipakai, tetapi pengajuan diarahkan ke review manual.

```python
body = resp.json()
data = body["data"]
fraud = body.get("fraud_check")  # None jika FRAUD_CHECK=false atau pengecekan gagal

if fraud is None:
    status = "perlu_review"            # tidak ada penilaian: jangan anggap aman
elif fraud["suspicious"]:
    status = "perlu_review"
    alasan = fraud["signals"]          # mis. ["moire_pattern"] atau ["low_colour"]
else:
    status = "lolos_otomatis"
```

Skor (`photocopy_score`, `screen_score`, 0–1) dikembalikan apa adanya, jadi Anda boleh memakai ambang sendiri, misalnya:

```python
# Hanya foto layar yang sangat jelas yang ditolak; sisanya review manual
if fraud and fraud["screen_score"] >= 0.9:
    minta_foto_ulang("Foto dokumen fisik secara langsung, bukan dari layar.")
```

::: tip Pesan ke pengguna
Jika `is_screen_recapture: true`, minta pengguna **memotret kartu fisik secara langsung**. Jika `is_photocopy: true` (KTP/NPWP), minta foto **kartu asli**, bukan fotokopi. Untuk KK, cetakan hitam-putih KK TTE bisa sah. Lihat [catatan KK](/dokumen/kk#catatan).
:::

Simpan `fraud_check` bersama data pengajuan supaya ambangnya bisa dievaluasi dan disetel ulang nanti.

## Tips

- **Timeout:** KTP/NPWP/Buku Tabungan ±5–7 detik, KK ±30 detik atau lebih. Set timeout client minimal 120 detik supaya request yang antre tidak putus.
- **Request paralel itu aman.** vLLM mem-batch request bersamaan, sampai 8 sekaligus; sisanya antre.
- **Kirim foto asli dari kamera, jangan diperkecil atau dikompres ulang.** API memang memperkecil gambar untuk OCR, tetapi [fraud check](/guide/fraud-check) memakai resolusi penuh: pola moiré foto layar hilang jika gambar di-resize di client. Batas upload tetap 10 MB; jika harus mengecilkan, sisakan sisi panjang minimal ±2000 px dan kualitas JPEG ≥ 90.
- **Validasi tetap di aplikasi.** Field kosong (`""`) berarti tidak terbaca. Untuk data penting, tampilkan hasil ke pengguna untuk dikonfirmasi.
