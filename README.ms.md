# agent-guardrails

[English](README.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · **Bahasa Melayu** · [ไทย](README.th.md)

Kumpulan cangkuk pelindung untuk Claude Code. Menghalang kesilapan berulang **secara
mekanikal**, bukan dengan menulis satu lagi nota yang meminta ejen supaya berhati-hati.

> Jamin dengan mekanisme, bukan dengan perhatian manusia.

## Sebabnya

Saya mengukur 30 sesi — 887 mesej pengguna. Pengguna terpaksa membetulkan saya **44 kali**,
dan pembetulan itu terkumpul kepada 6 corak. Setiap satu hanya dipertahankan oleh **teks di
dalam fail nota**. Notanya sudah pun ditulis. Kesilapannya tetap berlaku.

| Diukur | Corak | Pertahanan kini |
| --- | --- | --- |
| 12 | Mutu penulisan | dikesan `reply_check.py` |
| 9 | Terlalu awal mengaku siap | dikesan `reply_check.py` |
| 9 | Menghantar hasil yang tiada sesiapa minta | **ditolak** `outward_action_guard.py` |
| 7 | Kata "tidak boleh" tanpa mencuba | dikesan `reply_check.py` |
| 4 | Terlepas arahan | fail kriteria (bawah ambang) |
| 3 | Salah repositori / persekitaran | fail kriteria (bawah ambang) |

Peraturan penerimaan: **≥5 kejadian = ia berulang = nota tidak akan membaikinya** — nota itu
sudah pun gagal sekali. Bawah 5 kekal sebagai teks. Jika semuanya dijadikan sekatan, amaran
akan tepu sehingga tiada siapa membacanya.

## Kandungan

### Cangkuk (didaftarkan dalam `~/.claude/settings.json`, aktif di mana-mana)

| Fail | Peristiwa | Tugasnya |
| --- | --- | --- |
| `reply_check.py` | Stop | Menandakan blok status yang tiada, dakwaan siap tanpa bukti, "tidak boleh" yang belum dicuba, ciri tulisan mesin (kontras `X, not Y`, pembuka berbilang, ayat belah, mukadimah berjela), dan ungkapan biasa chatbot. **Amaran sahaja** — menyekat pada Stop berisiko gelung |
| `outward_action_guard.py` | PreToolUse(Bash) | **Menolak** tindakan keluar yang sukar dibatalkan (PR/push/cipta repositori/keluaran/gist). Turut menolak `<check> \| tail; echo $?` — itu membaca kod keluar `tail`, bukan kod pemeriksaan |
| `guard_the_guards.py` | PreToolUse(Edit/Write) | Meminta pengesahan sebelum menyunting pemeriksa, cangkuk, tetapan atau memori. Menghalang ejen daripada menulis semula penilai dan bukannya membaiki produk |
| `daily-retro-reminder.sh` | PostToolUse | Mengingatkan retrospektif apabila laporan harian ditulis |

### Kemahiran

`skills/daily-retro/` — kitaran penambahbaikan yang dicetuskan oleh penulisan laporan
harian. Menolak setiap kesilapan **serendah mungkin** pada tangga ini:

> memori → dokumen → skrip → pemeriksaan awal → ujian → kebenaran

### Skrip

| Fail | Kegunaan |
| --- | --- |
| `mistake-frequency.py` | **Mengira** corak pembetulan merentas semua sesi lalu, supaya "itu sudah saya baiki" adalah ukuran, bukan rasa |
| `verify-gates.py` | **Ujian kendiri untuk sekatan.** Memberi setiap cangkuk input yang mesti mencetuskannya dan input yang tidak boleh |

### Rujukan

`reference/anti-self-deception/` — 24 peraturan, 15 skrip dan 29 pemeriksaan tetap daripada
sistem matang pasukan lain, disertakan dengan kebenaran dan telah dilindungi identiti.
Lihat `ATTRIBUTION.md`.

## Dua yang paling memberi kesan

**`guard_the_guards.py`.** Semua pertahanan lain memerhati *produk*. Tiada apa yang
menghalang pihak yang diaudit daripada menulis semula penilainya.

**`verify-gates.py`.** Saya menulis pengesan keusangan tiga kali, dan ketiga-tiganya
meluluskan kesemua 18 memori. Tanpa membaca angkanya, saya akan melaporkan "sihat" tiga kali
berturut-turut. **Pemeriksaan yang tidak pernah gagal mungkin tidak melindungi apa-apa.**

## Pemasangan

Klon, kemudian `bash install.sh`. Menyalin ke `~/.claude/hooks/` dan `~/.claude/skills/`,
lalu mendaftarkan cangkuk dalam `~/.claude/settings.json` — menambah sahaja, tetapan sedia
ada dikekalkan.

Baca `CLAUDE.example.md`, sesuaikan dengan mesin anda (laluan memori, lokasi laporan
harian), kemudian letakkan sebagai `~/.claude/CLAUDE.md`.

Selepas itu sentiasa jalankan ujian kendiri:

    python3 ~/.claude/skills/daily-retro/scripts/verify-gates.py

Diuji 21/21 pada mesin baharu dan 26/26 pada mesin yang telah dikonfigurasi.

## Nota

- Cangkuk berada dalam `~/.claude/`, jadi ia terpakai **dalam setiap direktori**. Memori
  tidak — ia bergantung pada direktori tempat Claude dimulakan, jadi prinsip merentas
  projek patut diletakkan dalam `~/.claude/CLAUDE.md` yang dimuatkan setiap sesi.
- `outward_action_guard.py` menyekat push. Yang disengajakan menggunakan
  `CLAUDE_OUTWARD_OK=1`. Terlalu bising? Buang entri daripada `GUARDED`.
- `reply_check.py` berasaskan regex dan akan menghasilkan positif palsu. Apabila berlaku,
  **sempitkan coraknya — jangan padam pemeriksaan itu.**
- Mesej masa jalan cangkuk kini dalam bahasa Jepun. Ia dibaca oleh ejen jadi tidak
  menjejaskan tingkah laku, tetapi terjemahan amat dialu-alukan.

## Lesen

MIT
