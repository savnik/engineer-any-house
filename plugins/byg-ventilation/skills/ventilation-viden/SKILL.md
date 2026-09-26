---
name: ventilation-viden
description: >-
  Dansk ventilationsfaglig videnbase på mesterniveau: boligventilation, udsugning og
  erstatningsluft, varmegenvinding, emhætter, fugt, kondens og skimmel, kanaler og
  isolering, brand, lyd, radon og indregulering med normgrundlag (BR18 kap. 22,
  DS 447, DS 428, DS 452), faglig praksis, tjeklister og erfaringsblade. Bruges af
  ventilationsekspert-agenten og direkte ved ventilationsspørgsmål, hvor subagenter
  ikke er tilgængelige (fx claude.ai).
---

# Ventilations-videnbase

| Fil | Indhold | Læs når |
|---|---|---|
| `references/normgrundlag.md` | BR18-krav (kap. 22), standarder, radon, status | Krav, luftmængder, myndighed |
| `references/faglig-praksis.md` | Løsningstyper, dimensionering, erstatningsluft, fugt og skimmel, kanaler, brand, lyd, emhætter, radon, kældre | Projektering, vurdering, fejlfinding |
| `references/tjeklister.md` | Projektering, hold points, indregulering, aflevering | KS, tilbud, aflevering |
| `references/erfaringsblade.md` | Reviewede, forankrede erfaringer | Altid – hurtigt skim |

## Brug uden subagent
Kører du ikke som `ventilationsekspert`-agenten (fx i claude.ai eller i hovedtråden), så læs agentdefinitionen `${CLAUDE_PLUGIN_ROOT}/agents/ventilationsekspert.md` og arbejd efter dens rolle, kerneprincipper og fælles protokol.

## Statusmærker
**V** = verificeret mod kilde (dato). **T** = typisk værdi eller udgave, der skal verificeres før brug som krav.
