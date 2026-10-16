# Versionsnoter

Feature-grene hæver **aldrig** versioner i `plugin.json` eller `marketplace.json` – det er den største kilde til merge-konflikter, når flere sessioner arbejder parallelt. Læg i stedet én note pr. gren her: `versionsnoter/<emne>.md` (et unikt navn, fx grenens navn).

```
---
byg-kontrol: minor
byg: patch
---
Kort beskrivelse af ændringen (bliver udgivelsesnoten i CHANGELOG.md).
```

Niveau: `major` (brud på sagsmapper, tilstand eller agentnavne) · `minor` (ny funktion, ny regel) · `patch` (rettelse, tekst).

Efter merge til main: `python3 scripts/udgiv.py` hæver versionerne (højeste niveau pr. plugin på tværs af noterne, marketplacet med det højeste samlet), skriver `CHANGELOG.md` og sletter de udgivne noter. `--proev` viser først, hvad der sker. `scripts/hooks/pre-commit` afviser versionsændringer uden for main.
