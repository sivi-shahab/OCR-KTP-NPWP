# Performa

Angka referensi, diukur dengan gambar sintetis di GPU NVIDIA L40S (vGPU 24 GB, dipakai bersama), vLLM mode `--enforce-eager`.

| Skenario | Waktu |
|---|---|
| 1 request KTP, mode vLLM | ±7 detik |
| 1 request NPWP, mode vLLM | ±4.5–5 detik (field lebih sedikit) |
| 1 request KK (3 anggota), mode vLLM | ±30 detik, bertambah per anggota |
| 4 request bersamaan (2 KTP + 2 NPWP), mode vLLM | ±7.5 detik total (di-batch) |
| 1 request, mode HF | ±6.6–6.9 detik |
| 4 request bersamaan, mode HF | ±26 detik (antre) |

## Apa yang memengaruhi kecepatan

- **Jumlah token output adalah bottleneck utama**, bukan ukuran gambar. Karena itu NPWP lebih cepat dari KTP, dan KK jauh lebih lambat (satu objek JSON per anggota).
- **Batching:** vLLM memproses sampai 8 request sekaligus (`--max-num-seqs 8`). Throughput naik hampir linear sampai batas itu; request ke-9 dan seterusnya antre.
- **Resolusi gambar:** API memperkecil gambar sebelum dikirim (±1 MP untuk kartu, ±2.5 MP untuk KK). Menaikkan `MAX_PIXELS` membantu akurasi teks kecil tapi menambah waktu proses.
- **CUDA graphs:** server berjalan dengan `--enforce-eager` karena tidak ada `nvcc`. Di server yang punya CUDA toolkit, `VLLM_EAGER=no-enforce-eager` bisa mempercepat generate token.

## Kapasitas kasar

Dengan ±7 detik per batch dan 8 request per batch, satu GPU melayani kira-kira **60 KTP per menit** saat beban penuh. Untuk KK, hitung ±30 detik atau lebih per batch.
