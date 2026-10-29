# Skabelon til nye fag

Bruges af `scripts/new_trade.py`. Pladsholdere: `{{SLUG}}` (fag-id), `{{AGENT}}` (agentnavn), `{{TRADE_NAME}}`, `{{PLUGIN}}` (byg-<trade-id>), `{{COLOR}}`, `{{DATE}}`. I stinavne: `__SLUG__` og `__AGENT__`.

- `trade-plugin/` → `plugins/byg-<trade-id>/`
- `review/agents/__SLUG__-review.md` → `plugins/byg-review/agents/<trade-id>-review.md`
- `review/trade.md` → `plugins/byg-review/skills/review-knowledge/references/trades/<trade-id>.md`

Alle `TODO` skal udfyldes, og hvert normpunkt markeres V (kilde, dato) eller T, før faget tages i brug.
