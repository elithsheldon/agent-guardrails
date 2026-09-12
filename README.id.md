# agent-guardrails

[English](README.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · **Bahasa Indonesia** · [Bahasa Melayu](README.ms.md) · [ไทย](README.th.md)

Kumpulan hook pengaman untuk Claude Code. Menghentikan kesalahan berulang **secara
mekanis**, bukan dengan menulis satu catatan lagi yang meminta agen agar berhati-hati.

> Jaminannya lewat mekanisme, bukan lewat perhatian manusia.

## Alasannya

Saya mengukur 30 sesi — 887 pesan pengguna. Pengguna harus mengoreksi saya **44 kali**, dan
koreksi itu mengerucut menjadi 6 pola. Semuanya hanya dijaga oleh **tulisan di berkas
catatan**. Catatannya sudah ada. Kesalahannya tetap terjadi.

| Terukur | Pola | Penjagaan sekarang |
| --- | --- | --- |
| 12 | Kualitas tulisan | dideteksi `reply_check.py` |
| 9 | Terlalu cepat menyatakan selesai | dideteksi `reply_check.py` |
| 9 | Menyerahkan hasil yang tidak diminta | **ditolak** `outward_action_guard.py` |
| 7 | Bilang "tidak bisa" tanpa mencoba | dideteksi `reply_check.py` |
| 4 | Melewatkan instruksi | berkas kriteria (di bawah ambang) |
| 3 | Salah repositori / lingkungan | berkas kriteria (di bawah ambang) |

Aturan adopsi: **≥5 kejadian = berulang = catatan tidak akan menyelesaikannya** — catatan
itu sudah gagal sekali. Di bawah 5 tetap berupa tulisan. Kalau semuanya dijadikan
penghalang, peringatan akan jenuh sampai tidak ada yang membacanya.

## Isinya

### Hook (terdaftar di `~/.claude/settings.json`, aktif di mana saja)

| Berkas | Peristiwa | Fungsinya |
| --- | --- | --- |
| `reply_check.py` | Stop | Menandai blok status yang hilang, klaim selesai tanpa bukti, "tidak bisa" yang belum dicoba, ciri tulisan mesin (kontras `X, not Y`, pembuka berhitung, kalimat belah, basa-basi pembuka), dan celetukan khas chatbot. **Hanya memperingatkan** — memblokir di Stop berisiko membuat loop |
| `outward_action_guard.py` | PreToolUse(Bash) | **Menolak** tindakan keluar yang sulit dibatalkan (PR/push/buat repositori/rilis/gist). Menolak juga `<check> \| tail; echo $?` — itu membaca kode keluar `tail`, bukan kode pemeriksaannya |
| `guard_the_guards.py` | PreToolUse(Edit/Write) | Meminta konfirmasi sebelum menyunting pemeriksa, hook, konfigurasi, atau memori. Mencegah agen menulis ulang si penilai alih-alih memperbaiki produknya |
| `daily-retro-reminder.sh` | PostToolUse | Mengingatkan retrospektif saat laporan harian ditulis |

### Skill

`skills/daily-retro/` — siklus perbaikan yang dipicu oleh penulisan laporan harian.
Mendorong setiap kesalahan **sejauh mungkin ke bawah** tangga ini:

> memori → dokumen → skrip → pemeriksaan awal → pengujian → izin

### Skrip

| Berkas | Kegunaan |
| --- | --- |
| `mistake-frequency.py` | **Menghitung** pola koreksi di seluruh sesi terdahulu, agar "itu sudah saya perbaiki" terukur, bukan sekadar terasa |
| `verify-gates.py` | **Uji mandiri untuk penghalangnya.** Memberi tiap hook masukan yang harus memicunya dan masukan yang tidak boleh |

### Rujukan

`reference/anti-self-deception/` — 24 aturan, 15 skrip, dan 29 pemeriksaan tetap dari sistem
matang tim lain, disertakan dengan izin dan sudah dianonimkan. Lihat `ATTRIBUTION.md`.

## Dua yang paling berpengaruh

**`guard_the_guards.py`.** Semua penjagaan lain mengawasi *produk*. Tidak ada yang mencegah
pihak yang diperiksa menulis ulang si penilai.

**`verify-gates.py`.** Saya menulis pendeteksi keusangan tiga kali, dan ketiganya meloloskan
seluruh 18 memori. Tanpa membaca angkanya, saya akan melaporkan "sehat" tiga kali berturut.
**Pemeriksaan yang belum pernah gagal mungkin tidak menjaga apa pun.**

## Pemasangan

Klon, lalu `bash install.sh`. Menyalin ke `~/.claude/hooks/` dan `~/.claude/skills/`, lalu
mendaftarkan hook di `~/.claude/settings.json` — hanya menambah, pengaturan lama dipertahankan.

Baca `CLAUDE.example.md`, sesuaikan dengan mesin Anda (jalur memori, lokasi laporan harian),
lalu letakkan sebagai `~/.claude/CLAUDE.md`.

Setelah itu selalu jalankan uji mandiri:

    python3 ~/.claude/skills/daily-retro/scripts/verify-gates.py

Teruji 21/21 pada mesin baru dan 26/26 pada mesin yang sudah dikonfigurasi.

## Catatan

- Hook berada di `~/.claude/`, jadi berlaku **di semua direktori**. Memori tidak — ia
  terikat pada direktori tempat Claude dijalankan, sehingga prinsip lintas proyek sebaiknya
  ditaruh di `~/.claude/CLAUDE.md` yang dimuat tiap sesi.
- `outward_action_guard.py` memblokir push. Yang disengaja memakai `CLAUDE_OUTWARD_OK=1`.
  Terlalu berisik? Hapus entri dari `GUARDED`.
- `reply_check.py` berbasis regex dan akan menghasilkan positif palsu. Bila terjadi,
  **persempit polanya — jangan hapus pemeriksaannya.**
- Pesan runtime hook saat ini berbahasa Jepang. Itu dibaca oleh agen sehingga tidak
  memengaruhi perilaku, tetapi terjemahan sangat diterima.

## Penghargaan

Aturan, skrip, dan pemeriksaan tetap di `reference/anti-self-deception/`
adalah karya [@Karas-cnk](https://github.com/Karas-cnk), disertakan atas izinnya. `guard_the_guards.py` dan
aturan pipa/kode keluar berasal dari sana.

## Lisensi

MIT
