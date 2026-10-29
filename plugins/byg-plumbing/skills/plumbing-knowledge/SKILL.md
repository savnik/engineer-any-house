---
name: plumbing-knowledge
description: >-
  Dansk VVS-faglig videnbase på mesterniveau: vand, afløb, varme, varmepumper og
  vådrumsinstallationer med normgrundlag (BR18 kap. 21 Vand m.fl., DS 439, DS 432,
  DS 452, BUILD 252), faglig praksis, tjeklister og forankrede erfaringsblade.
  Bruges af plumber-agenten og direkte ved VVS-spørgsmål, hvor subagenter
  ikke er tilgængelige (fx claude.ai).
---

# VVS-videnbase

Indgang til den kuraterede VVS-viden. Læs kun de filer, opgaven kræver.

| Fil | Indhold | Læs når |
|---|---|---|
| `references/standards.md` | Kilder, hvad der er bindende, verifikationsstatus, opslagsrækkefølge | Spørgsmål om krav, normer, autorisation – også vådrum (§339), fyringsanlæg og aftræk, gaseftersyn, jordvarme |
| `references/practice.md` | Principper, løsninger, ældre huse, fejlfinding, grænseflader | Projektering, vurdering, fejlfinding |
| `references/checklists.md` | Projektering, hold points, idriftsættelse, aflevering, gaseftersyn | KS, tilbudsgennemgang, aflevering, eftersyn |
| `references/schematic.md` | Principdiagram: indhold, layout, farver, SVG-symbolbibliotek, tjekliste | Diagram over varme, brugsvand og afløb – projektering, kedel- og VVB-skift, fejlfinding, aflevering |
| `assets/schematic-example-house.svg` | Færdigt principdiagram for eksempelhuset | Udgangspunkt for et nyt diagram |
| `references/lessons.md` | Reviewede, forankrede erfaringer | Altid – hurtigt skim |

## Brug uden subagent
Kører du ikke som `plumber`-agenten (fx i claude.ai eller i hovedtråden), så læs agentdefinitionen `${CLAUDE_PLUGIN_ROOT}/agents/plumber.md` og arbejd efter dens rolle, kerneprincipper og fælles protokol.

## Statusmærker i videnbasen
- **V** = verificeret mod kilde (dato angivet). Må bruges som fakta med kildeangivelse.
- **T** = typisk værdi eller udgave, der skal verificeres før den bruges som krav.
