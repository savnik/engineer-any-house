---
name: {{SLUG}}-viden
description: >-
  Dansk videnbase for {{FAGNAVN}} på mesterniveau: normgrundlag, faglig praksis,
  tjeklister og erfaringsblade. Bruges af {{AGENT}}-agenten og direkte ved
  spørgsmål om faget, hvor subagenter ikke er tilgængelige. TODO: præcisér emner.
---

# {{FAGNAVN}} – videnbase

| Fil | Indhold | Læs når |
|---|---|---|
| `references/normgrundlag.md` | Krav, normer, anvisninger med status | Krav, myndighed |
| `references/faglig-praksis.md` | Metoder, løsninger, fejlfinding | Projektering, vurdering |
| `references/tjeklister.md` | Forundersøgelse, hold points, aflevering | KS, tilbud, aflevering |
| `references/erfaringsblade.md` | Reviewede, forankrede erfaringer | Altid – hurtigt skim |

## Brug uden subagent
Kører du ikke som `{{AGENT}}`-agenten, så læs `${CLAUDE_PLUGIN_ROOT}/agents/{{AGENT}}.md` og arbejd efter dens rolle, kerneprincipper og fælles protokol.

## Statusmærker
**V** = verificeret mod kilde (dato). **T** = skal verificeres før brug som krav.
