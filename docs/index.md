---
layout: home

hero:
  name: OCR API
  text: KTP, NPWP & Kartu Keluarga jadi JSON
  tagline: Satu service FastAPI dengan model vision-language Qwen2.5-VL-3B di atas vLLM. Kirim foto dokumen, terima data terstruktur yang selalu valid sesuai schema.
  image:
    src: /logo.svg
    alt: OCR API
  actions:
    - theme: brand
      text: Quick start (5 menit)
      link: /guide/quick-start
    - theme: alt
      text: Mengapa OCR API?
      link: /guide/why
    - theme: alt
      text: Referensi API
      link: /guide/api

features:
  - icon: 🪪
    title: KTP
    details: 14 field, dari NIK sampai Berlaku Hingga. Prompt memahami tata letak kartu sehingga Gol. Darah yang kosong tidak menggeser baris lain.
    link: /dokumen/ktp
    linkText: Field KTP
  - icon: 🧾
    title: NPWP
    details: Nomor NPWP format lama (NN.NNN.NNN.N-NNN.NNN) dan baru 15–16 digit, nama, NIK, alamat, KPP, dan tanggal terdaftar.
    link: /dokumen/npwp
    linkText: Field NPWP
  - icon: 👨‍👩‍👧
    title: Kartu Keluarga
    details: Header KK plus daftar anggota keluarga. Baris tabel atas dan bawah dengan nomor yang sama digabung menjadi satu objek per anggota.
    link: /dokumen/kk
    linkText: Field KK
  - icon: 🧱
    title: Output selalu JSON valid
    details: Structured output vLLM memaksa model mengikuti JSON schema. Semua key selalu ada, enum dan pattern (NIK 16 digit, jenis kelamin) dijaga saat decoding.
    link: /guide/prompt
    linkText: Prompt & batasan output
  - icon: ⚡
    title: Batching otomatis
    details: Beberapa request bersamaan di-batch oleh vLLM. Empat request KTP/NPWP sekaligus selesai hampir secepat satu request.
    link: /operasional/performa
    linkText: Angka performa
  - icon: 📤
    title: Multipart atau base64
    details: Upload file lewat multipart/form-data, atau kirim JSON berisi base64 / data URI. JPEG, PNG, WebP sampai 10 MB.
    link: /guide/api
    linkText: Endpoint
  - icon: 🔑
    title: Autentikasi X-API-Key
    details: Endpoint /extract/* dilindungi header X-API-Key. Mendukung beberapa key sekaligus untuk rotasi tanpa downtime.
    link: /operasional/autentikasi
    linkText: Autentikasi
  - icon: 📖
    title: Swagger tanpa internet
    details: Swagger UI disajikan langsung oleh API dari file lokal, jadi /docs tetap bisa dipakai di jaringan internal tanpa akses CDN.
    link: /guide/api#swagger-ui
    linkText: Swagger UI
  - icon: 🐳
    title: Docker Compose
    details: Dua container (api + vllm), restart otomatis setelah reboot, healthcheck, dan port vLLM tidak pernah diekspos.
    link: /operasional/deployment
    linkText: Deployment
  - icon: 🧩
    title: Mudah ditambah
    details: Dokumen baru (mis. SIM) cukup schema + prompt + satu entri registry. Endpoint dan JSON schema vLLM dibuat otomatis.
    link: /tutorial/dokumen-baru
    linkText: Tutorial dokumen baru
---

<div class="vp-doc home-extra">

## Cara kerja

```
                               ┌────────────────────────────┐      ┌─────────────────────────────┐
 client ── /extract/ktp   ──►  │ OCR API :8070              │ ───► │ vLLM (Qwen2.5-VL) :8071     │ ── GPU
 client ── /extract/npwp  ──►  │ validasi · resize · prompt │      │ structured JSON output      │
 client ── /extract/kk    ──►  │ + JSON schema per dokumen  │      │ (port tidak dipublish)      │
                               └────────────────────────────┘      └─────────────────────────────┘
```

1. Client mengirim foto dokumen ke endpoint sesuai jenisnya, dengan header `X-API-Key`.
2. API memvalidasi tipe dan ukuran file, memperkecil gambar, lalu mengirimnya ke vLLM bersama prompt dan JSON schema dokumen itu.
3. vLLM menjalankan Qwen2.5-VL di GPU dan hanya boleh menghasilkan JSON yang cocok dengan schema.
4. API mem-parse hasilnya dan membalas `{"success": true, "data": {...}, "raw_output": "..."}`.

Detail lengkapnya ada di [Arsitektur](/guide/arsitektur).

## Pilih jalur Anda

| Saya ingin… | Mulai dari |
|---|---|
| Mencoba API dalam 5 menit | [Quick start](/guide/quick-start) |
| Memanggil API dari aplikasi (Python, JavaScript, Java) | [Integrasi dari aplikasi](/tutorial/integrasi) |
| Tahu field apa saja yang dikembalikan | [KTP](/dokumen/ktp) · [NPWP](/dokumen/npwp) · [KK](/dokumen/kk) |
| Menjalankan dan memelihara server | [Deployment Docker Compose](/operasional/deployment) |
| Memperbaiki field yang salah baca | [Prompt & batasan output](/guide/prompt) |
| Menambah jenis dokumen baru | [Menambah dokumen baru](/tutorial/dokumen-baru) |
| Mengatasi error | [Troubleshooting](/operasional/troubleshooting) |

</div>

<style>
.home-extra {
  max-width: 1152px;
  margin: 48px auto 0;
  padding: 0 24px;
}
@media (min-width: 640px) {
  .home-extra { padding: 0 48px; }
}
@media (min-width: 960px) {
  .home-extra { padding: 0 64px; }
}
</style>
