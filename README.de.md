# agent-guardrails

[English](README.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Español](README.es.md) · **Deutsch** · [Bahasa Indonesia](README.id.md) · [Bahasa Melayu](README.ms.md) · [ไทย](README.th.md)

Schutzmechanismen für Claude Code. Stoppt wiederkehrende Fehler **mechanisch**, statt noch
eine Notiz zu schreiben, die zur Vorsicht mahnt.

> Durch Mechanik absichern, nicht durch menschliche Aufmerksamkeit.

## Warum

Ich habe 30 Sitzungen vermessen — 887 Nutzernachrichten. Der Nutzer musste mich **44 Mal**
korrigieren, und die Korrekturen fallen in 6 Muster. Jedes einzelne war nur durch **Text in
einer Notizdatei** abgesichert. Die Notiz war bereits geschrieben. Der Fehler passierte
trotzdem.

| Gemessen | Muster | Aktuelle Absicherung |
| --- | --- | --- |
| 12 | Qualität der Formulierung | `reply_check.py` erkennt es |
| 9 | Zu früh „fertig" melden | `reply_check.py` erkennt es |
| 9 | Liefern, was niemand verlangt hat | `outward_action_guard.py` **verweigert** |
| 7 | „Geht nicht" sagen, ohne es zu versuchen | `reply_check.py` erkennt es |
| 4 | Anweisung überlesen | Kriteriendatei (unter der Schwelle) |
| 3 | Falsches Repository / falsche Umgebung | Kriteriendatei (unter der Schwelle) |

Aufnahmeregel: **≥5 Vorkommen = es wiederholt sich = eine Notiz behebt es nicht** — diese
Notiz ist bereits einmal gescheitert. Unter 5 bleibt es Text. Alles zu blockieren sättigt
die Warnungen, bis sie niemand mehr liest.

## Inhalt

### Hooks (in `~/.claude/settings.json` registriert, überall aktiv)

| Datei | Ereignis | Funktion |
| --- | --- | --- |
| `reply_check.py` | Stop | Meldet fehlenden Statusblock, unbelegte Fertigmeldungen, ungeprüftes „geht nicht", maschinelle Schreibmuster (`X, not Y`-Kontrast, aufzählende Einleitungen, Spaltsätze, Räuspern) und Chatbot-Floskeln. **Nur Warnung** — Blockieren im Stop-Hook birgt Schleifengefahr |
| `outward_action_guard.py` | PreToolUse(Bash) | **Verweigert** schwer rückgängig zu machende Aktionen nach außen (PR/Push/Repository/Release/Gist). Verweigert außerdem `<check> \| tail; echo $?` — das liest den Exit-Code von `tail`, nicht den der Prüfung |
| `guard_the_guards.py` | PreToolUse(Edit/Write) | Fragt nach, bevor ein Prüfer, ein Hook, die Konfiguration oder der Speicher bearbeitet wird. Verhindert, dass der Geprüfte den Prüfer umschreibt, statt das Produkt zu korrigieren |
| `daily-retro-reminder.sh` | PostToolUse | Erinnert an die Retrospektive, sobald ein Tagesbericht geschrieben wird |

### Skill

`skills/daily-retro/` — ein Verbesserungszyklus, ausgelöst durch das Schreiben des
Tagesberichts. Schiebt jeden Fehler so weit **nach unten** wie möglich:

> Speicher → Dokument → Skript → Vorabprüfung → Test → Berechtigung

### Skripte

| Datei | Zweck |
| --- | --- |
| `mistake-frequency.py` | **Zählt** Korrekturmuster über alle bisherigen Sitzungen, damit „das habe ich schon behoben" gemessen und nicht gefühlt wird |
| `verify-gates.py` | **Selbsttest der Schutzmechanismen.** Gibt jedem eine Eingabe, die auslösen muss, und eine, die nicht auslösen darf |

### Referenz

`reference/anti-self-deception/` — 24 Regeln, 15 Skripte und 29 Dauerprüfungen aus dem
ausgereiften System eines anderen Teams, mit Erlaubnis aufgenommen und anonymisiert.
Siehe `ATTRIBUTION.md`.

## Die zwei wichtigsten

**`guard_the_guards.py`.** Alle anderen Absicherungen beobachteten *Produkte*. Nichts hielt
die geprüfte Seite davon ab, den Prüfer umzuschreiben.

**`verify-gates.py`.** Ich habe dreimal einen Veralterungsdetektor geschrieben, und dreimal
hat er alle 18 Speichereinträge durchgewinkt. Ohne die Zahlen zu lesen, hätte ich dreimal
„alles gesund" gemeldet. **Eine Prüfung, die nie fehlgeschlagen ist, schützt möglicherweise
nichts.**

## Installation

Klonen, dann `bash install.sh`. Kopiert nach `~/.claude/hooks/` und `~/.claude/skills/` und
registriert die Hooks in `~/.claude/settings.json` — nur ergänzend, Bestehendes bleibt.

`CLAUDE.example.md` lesen, an die eigene Maschine anpassen (Speicherpfad, Ablage des
Tagesberichts) und als `~/.claude/CLAUDE.md` ablegen.

Danach immer den Selbsttest laufen lassen:

    python3 ~/.claude/skills/daily-retro/scripts/verify-gates.py

Getestet mit 21/21 auf einer frischen und 26/26 auf einer eingerichteten Maschine.

## Hinweise

- Hooks liegen in `~/.claude/` und gelten daher **in jedem Verzeichnis**. Der Speicher nicht
  — er hängt am Startverzeichnis. Projektübergreifende Grundsätze gehören deshalb in
  `~/.claude/CLAUDE.md`, das in jeder Sitzung geladen wird.
- `outward_action_guard.py` blockiert Pushes. Beabsichtigte setzen `CLAUDE_OUTWARD_OK=1`.
  Zu laut? Einträge aus `GUARDED` entfernen.
- `reply_check.py` arbeitet mit regulären Ausdrücken und erzeugt Fehlalarme. Dann
  **das Muster verengen — die Prüfung nicht löschen.**
- Die Laufzeitmeldungen der Hooks sind auf Japanisch. Sie werden vom Agenten gelesen und
  beeinflussen das Verhalten nicht; eine Übersetzung ist willkommen.

## Lizenz

MIT
