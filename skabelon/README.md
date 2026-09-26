# Skabelon til nye fag

Bruges af `scripts/nyt_fag.py`. Pladsholdere: `{{SLUG}}` (fag-id), `{{AGENT}}` (agentnavn), `{{FAGNAVN}}`, `{{PLUGIN}}` (byg-<fag-id>), `{{FARVE}}`, `{{DATO}}`. I stinavne: `__SLUG__` og `__AGENT__`.

- `fag-plugin/` → `plugins/byg-<fag-id>/`
- `kontrol/agents/__SLUG__-kontrol.md` → `plugins/byg-kontrol/agents/<fag-id>-kontrol.md`
- `kontrol/fag.md` → `plugins/byg-kontrol/skills/kontrol-viden/references/fag/<fag-id>.md`

Alle `TODO` skal udfyldes, og hvert normpunkt markeres V (kilde, dato) eller T, før faget tages i brug.
