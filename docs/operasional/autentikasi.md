# Autentikasi & API key

Semua endpoint `/extract/*` wajib mengirim header `X-API-Key` berisi salah satu key di `API_KEYS`. Tanpa header atau dengan key salah, API membalas `401`:

```json
{ "detail": "Missing or invalid X-API-Key header." }
```

`/health`, `/docs`, dan `/openapi.json` tetap terbuka. Healthcheck Docker memakai `/health`.

## Di mana key disimpan

- Key disimpan di file `.env` di folder project (permission `600`, masuk `.gitignore`, **tidak pernah di-commit**).
- `docker-compose.yml` meneruskan `API_KEYS` ke container `api`.
- Jika `API_KEYS` kosong, autentikasi mati dan API menulis warning di log. Jangan biarkan kosong di production.

```bash
# .env
API_KEYS=key-aplikasi-a,key-aplikasi-b
```

Setelah mengubah `.env`, terapkan dengan:

```bash
docker compose up -d api
```

## Membuat key baru

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Sebaiknya satu key per aplikasi client, supaya satu aplikasi bisa dicabut aksesnya tanpa mengganggu yang lain.

## Rotasi tanpa downtime

1. Tambahkan key baru di belakang: `API_KEYS=lama,baru`
2. `docker compose up -d api`
3. Pindahkan semua client ke key baru.
4. Hapus key lama dari `API_KEYS`, lalu `docker compose up -d api` lagi.

## Di Swagger

Klik **Authorize** di kanan atas `/docs`, isi key, lalu **Try it out** seperti biasa.
