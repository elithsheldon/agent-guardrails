# agent-guardrails

[English](README.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [한국어](README.ko.md) · [Français](README.fr.md) · **Español** · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Bahasa Melayu](README.ms.md) · [ไทย](README.th.md)

Barreras de protección para Claude Code. Detiene **mecánicamente** los errores repetidos,
en vez de escribir otra nota pidiendo al agente que tenga cuidado.

> Garantízalo con mecanismos, no con la atención humana.

## Por qué

Medí 30 sesiones — 887 mensajes del usuario. El usuario tuvo que corregirme **44 veces**,
y esas correcciones se reducen a 6 patrones. Todos ellos estaban defendidos únicamente
por **texto en un archivo de notas**. La nota ya estaba escrita. El error ocurrió igual.

| Medido | Patrón | Defensa actual |
| --- | --- | --- |
| 12 | Calidad de la redacción | `reply_check.py` lo detecta |
| 9 | Declarar «terminado» demasiado pronto | `reply_check.py` lo detecta |
| 9 | Entregar lo que nadie pidió | `outward_action_guard.py` lo **rechaza** |
| 7 | Decir «no puedo» sin haberlo intentado | `reply_check.py` lo detecta |
| 4 | Pasar por alto una instrucción | archivo de criterios (bajo el umbral) |
| 3 | Repositorio o entorno equivocado | archivo de criterios (bajo el umbral) |

Regla de adopción: **≥5 apariciones = es recurrente = una nota no lo va a arreglar** — esa
nota ya falló una vez. Por debajo de 5 se queda como texto. Convertirlo todo en barrera
satura los avisos hasta que nadie los lee.

## Contenido

### Hooks (registrados en `~/.claude/settings.json`, activos en todas partes)

| Archivo | Evento | Qué hace |
| --- | --- | --- |
| `reply_check.py` | Stop | Señala la falta del bloque de estado, afirmaciones de finalización sin evidencia, un «no puedo» sin intentarlo, tics de escritura de máquina (contraste `X, not Y`, aperturas enumerativas, oraciones hendidas, carraspeos) y muletillas de chatbot. **Solo avisa** — bloquear en Stop arriesga un bucle |
| `outward_action_guard.py` | PreToolUse(Bash) | **Rechaza** acciones difíciles de deshacer (PR/push/crear repositorio/release/gist). También rechaza `<check> \| tail; echo $?` — eso lee el código de salida de `tail`, no el de la comprobación |
| `guard_the_guards.py` | PreToolUse(Edit/Write) | Pide confirmación antes de editar un verificador, un hook, la configuración o la memoria. Evita que el agente reescriba al juez en lugar de arreglar el producto |
| `daily-retro-reminder.sh` | PostToolUse | Recuerda la retrospectiva al escribir el informe diario |

### Habilidad

`skills/daily-retro/` — un ciclo de mejora que arranca al escribir el informe diario.
Empuja cada error tan **abajo** como sea posible en esta escalera:

> memoria → documento → script → comprobación previa → prueba → permiso

### Scripts

| Archivo | Propósito |
| --- | --- |
| `mistake-frequency.py` | **Cuenta** los patrones de corrección en todas las sesiones pasadas, para que «eso ya lo arreglé» sea medido y no una impresión |
| `verify-gates.py` | **Autoprueba de las barreras.** A cada una le da una entrada que debe dispararla y otra que no |

### Referencia

`reference/anti-self-deception/` — 24 reglas, 15 scripts y 29 comprobaciones permanentes
del sistema maduro de otro equipo, incluidos con permiso y anonimizados.
Véase `ATTRIBUTION.md`.

## Los dos que más importaron

**`guard_the_guards.py`.** Todas las demás defensas vigilaban *productos*. Nada impedía
que la parte auditada reescribiera al juez.

**`verify-gates.py`.** Escribí un detector de obsolescencia tres veces y las tres veces
aprobó las 18 memorias. Sin leer los números habría informado «todo sano» tres veces.
**Una comprobación que nunca ha fallado puede no estar protegiendo nada.**

## Instalación

Clona y ejecuta `bash install.sh`. Copia en `~/.claude/hooks/` y `~/.claude/skills/`, y
registra los hooks en `~/.claude/settings.json` — solo añade, conserva lo existente.

Lee `CLAUDE.example.md`, adáptalo a tu máquina (ruta de la memoria, ubicación del informe
diario) y colócalo en `~/.claude/CLAUDE.md`.

Después ejecuta siempre la autoprueba:

    python3 ~/.claude/skills/daily-retro/scripts/verify-gates.py

Probado con 21/21 en una máquina nueva y 26/26 en una configurada.

## Notas

- Los hooks viven en `~/.claude/`, así que aplican **en todos los directorios**. La memoria
  no: depende del directorio donde arranca Claude, así que los principios transversales van
  en `~/.claude/CLAUDE.md`, que se carga en cada sesión.
- `outward_action_guard.py` bloquea los push. Los intencionados usan `CLAUDE_OUTWARD_OK=1`.
  ¿Demasiado ruido? Quita entradas de `GUARDED`.
- `reply_check.py` usa expresiones regulares y dará falsos positivos. Cuando ocurra,
  **acota el patrón — no borres la comprobación.**
- Los mensajes de ejecución de los hooks están en japonés. Los lee el agente, así que no
  afectan al comportamiento, pero una traducción es bienvenida.

## Licencia

MIT
