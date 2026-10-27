import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

export default withMermaid(
  defineConfig({
    lang: 'id-ID',
    title: 'OCR API',
    description: 'Ekstraksi data terstruktur dari KTP, NPWP, dan Kartu Keluarga dengan Qwen2.5-VL',
    base: '/OCR-KTP-NPWP/',
    cleanUrls: true,
    lastUpdated: true,
    head: [['link', { rel: 'icon', type: 'image/svg+xml', href: '/OCR-KTP-NPWP/logo.svg' }]],

    themeConfig: {
      logo: '/logo.svg',
      nav: [
        { text: 'Panduan', link: '/guide/quick-start' },
        { text: 'Dokumen', link: '/dokumen/ktp' },
        { text: 'Tutorial', link: '/tutorial/integrasi' },
        { text: 'Operasional', link: '/operasional/deployment' },
      ],

      sidebar: [
        {
          text: 'Panduan',
          items: [
            { text: 'Mengapa OCR API?', link: '/guide/why' },
            { text: 'Quick start (5 menit)', link: '/guide/quick-start' },
            { text: 'Arsitektur', link: '/guide/arsitektur' },
            { text: 'Referensi API', link: '/guide/api' },
            { text: 'Prompt & batasan output', link: '/guide/prompt' },
          ],
        },
        {
          text: 'Dokumen',
          items: [
            { text: 'KTP', link: '/dokumen/ktp' },
            { text: 'NPWP', link: '/dokumen/npwp' },
            { text: 'Kartu Keluarga (KK)', link: '/dokumen/kk' },
          ],
        },
        {
          text: 'Tutorial',
          items: [
            { text: 'Integrasi dari aplikasi', link: '/tutorial/integrasi' },
            { text: 'Menambah dokumen baru', link: '/tutorial/dokumen-baru' },
          ],
        },
        {
          text: 'Operasional',
          items: [
            { text: 'Deployment Docker Compose', link: '/operasional/deployment' },
            { text: 'Alternatif: setup screen', link: '/operasional/screen' },
            { text: 'Konfigurasi', link: '/operasional/konfigurasi' },
            { text: 'Autentikasi & API key', link: '/operasional/autentikasi' },
            { text: 'Performa', link: '/operasional/performa' },
            { text: 'Troubleshooting', link: '/operasional/troubleshooting' },
          ],
        },
        {
          text: 'Referensi',
          items: [
            { text: 'Struktur kode', link: '/referensi/struktur-kode' },
            { text: 'Rollback', link: '/referensi/rollback' },
          ],
        },
      ],

      socialLinks: [{ icon: 'github', link: 'https://github.com/sivi-shahab/OCR-KTP-NPWP' }],
      search: { provider: 'local' },
      outline: { level: [2, 3], label: 'Di halaman ini' },
      docFooter: { prev: 'Sebelumnya', next: 'Berikutnya' },
      lastUpdated: { text: 'Terakhir diperbarui' },
      darkModeSwitchLabel: 'Tampilan',
      returnToTopLabel: 'Kembali ke atas',
      sidebarMenuLabel: 'Menu',
      footer: { message: 'OCR API · Qwen2.5-VL-3B-Instruct + vLLM' },
    },
  }),
)
