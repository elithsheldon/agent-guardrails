# agent-guardrails

[English](README.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [한국어](README.ko.md) · **Français** · [Español](README.es.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Bahasa Melayu](README.ms.md) · [ไทย](README.th.md)

Garde-fous pour Claude Code. Bloque **mécaniquement** les erreurs répétées, au lieu
d'écrire une note de plus demandant à l'agent d'être prudent.

> Le garantir par la mécanique, pas par l'attention humaine.

## Pourquoi

J'ai mesuré 30 sessions — 887 messages utilisateur. L'utilisateur a dû me corriger
**44 fois**, et ces corrections se réduisent à 6 schémas. Chacun d'eux n'était défendu
que par **du texte dans un fichier de notes**. La note existait déjà. L'erreur s'est
produite quand même.

| Mesuré | Schéma | Défense actuelle |
| --- | --- | --- |
| 12 | Qualité de rédaction | `reply_check.py` détecte |
| 9 | Annoncer « terminé » trop tôt | `reply_check.py` détecte |
| 9 | Livrer ce que personne n'a demandé | `outward_action_guard.py` **refuse** |
| 7 | Dire « impossible » sans avoir essayé | `reply_check.py` détecte |
| 4 | Instruction manquée | fichier de critères (sous le seuil) |
| 3 | Mauvais dépôt / environnement | fichier de critères (sous le seuil) |

Règle d'adoption : **≥5 occurrences = c'est récurrent = une note n'y changera rien** —
la note a déjà échoué. En dessous de 5, cela reste du texte. Tout verrouiller sature
les avertissements jusqu'à ce que plus personne ne les lise.

## Contenu

### Hooks (déclarés dans `~/.claude/settings.json`, actifs partout)

| Fichier | Événement | Rôle |
| --- | --- | --- |
| `reply_check.py` | Stop | Signale un bloc de statut manquant, une affirmation d'achèvement sans preuve, un « impossible » non testé, les tics de rédaction machine (contraste `X, not Y`, ouvertures énumératives, phrases clivées, raclements de gorge) et les formules de chatbot. **Avertit seulement** — bloquer sur Stop risque une boucle |
| `outward_action_guard.py` | PreToolUse(Bash) | **Refuse** les actions difficilement réversibles (PR/push/création de dépôt/release/gist). Refuse aussi `<check> \| tail; echo $?` — cela lit le code de sortie de `tail`, pas celui du contrôle |
| `guard_the_guards.py` | PreToolUse(Edit/Write) | Demande confirmation avant de modifier un contrôleur, un hook, la configuration ou la mémoire. Empêche l'agent de réécrire le juge au lieu de corriger le produit |
| `daily-retro-reminder.sh` | PostToolUse | Relance la rétrospective quand un rapport quotidien est écrit |

### Compétence

`skills/daily-retro/` — une boucle d'amélioration déclenchée par la rédaction du rapport
quotidien. Fait descendre chaque erreur aussi **bas** que possible sur cette échelle :

> mémoire → documentation → script → contrôle préalable → test → permission

### Scripts

| Fichier | Objet |
| --- | --- |
| `mistake-frequency.py` | **Compte** les schémas de correction sur toutes les sessions passées, pour que « c'est déjà corrigé » soit mesuré et non ressenti |
| `verify-gates.py` | **Auto-test des garde-fous.** Fournit à chacun une entrée qui doit le déclencher et une qui ne doit pas |

### Référence

`reference/anti-self-deception/` — 24 règles, 15 scripts et 29 contrôles permanents issus
du système mature d'une autre équipe, inclus avec autorisation et anonymisés.
Voir `ATTRIBUTION.md`.

## Les deux qui ont le plus compté

**`guard_the_guards.py`.** Toutes les autres défenses surveillaient les *produits*. Rien
n'empêchait la partie auditée de réécrire le juge.

**`verify-gates.py`.** J'ai écrit trois fois un détecteur d'obsolescence, et les trois fois
il a validé les 18 mémoires. Sans lire les chiffres, j'aurais rapporté « tout va bien »
trois fois de suite. **Un contrôle qui n'a jamais échoué ne protège peut-être rien.**

## Installation

Clonez, puis `bash install.sh`. Copie dans `~/.claude/hooks/` et `~/.claude/skills/`,
puis déclare les hooks dans `~/.claude/settings.json` — en ajout seulement, la
configuration existante est préservée.

Lisez `CLAUDE.example.md`, adaptez-le à votre machine (chemin de la mémoire, emplacement
du rapport quotidien), puis placez-le en `~/.claude/CLAUDE.md`.

Ensuite, lancez toujours l'auto-test :

    python3 ~/.claude/skills/daily-retro/scripts/verify-gates.py

Testé à 21/21 sur une machine neuve et 26/26 sur une machine configurée.

## Remarques

- Les hooks vivent dans `~/.claude/`, donc ils s'appliquent **dans tous les répertoires**.
  Pas la mémoire : elle dépend du répertoire de démarrage, donc les principes transverses
  vont dans `~/.claude/CLAUDE.md`, chargé à chaque session.
- `outward_action_guard.py` bloque les push. Les push voulus utilisent
  `CLAUDE_OUTWARD_OK=1`. Trop bruyant ? Retirez des entrées de `GUARDED`.
- `reply_check.py` repose sur des expressions régulières et produira des faux positifs.
  Dans ce cas, **restreignez le motif — ne supprimez pas le contrôle.**
- Les messages d'exécution des hooks sont en japonais. Ils sont lus par l'agent, donc sans
  effet sur le comportement, mais une traduction est bienvenue.

## Remerciements

Les règles, scripts et contrôles permanents de `reference/anti-self-deception/`
sont l'œuvre de [@Karas-cnk](https://github.com/Karas-cnk), inclus avec son autorisation. `guard_the_guards.py`
et la règle pipe/code de sortie en sont issus.

## Licence

MIT
