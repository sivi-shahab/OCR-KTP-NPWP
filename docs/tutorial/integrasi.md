# Integrasi dari aplikasi

Tutorial ini menunjukkan cara memanggil OCR API dari aplikasi lain. Semua contoh memakai endpoint KTP; untuk dokumen lain cukup ganti `ktp` dengan `npwp` atau `kk`.

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

## Tips

- **Timeout:** KTP/NPWP ±5–7 detik, KK ±30 detik atau lebih. Set timeout client minimal 120 detik supaya request yang antre tidak putus.
- **Request paralel itu aman.** vLLM mem-batch request bersamaan, sampai 8 sekaligus; sisanya antre.
- **Kecilkan gambar di client** jika bandwidth terbatas. API toh memperkecil KTP/NPWP ke ±1 MP; mengirim foto 12 MP hanya membuang waktu upload.
- **Validasi tetap di aplikasi.** Field kosong (`""`) berarti tidak terbaca. Untuk data penting, tampilkan hasil ke pengguna untuk dikonfirmasi.
