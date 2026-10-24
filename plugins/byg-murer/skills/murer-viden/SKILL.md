---
name: murer-viden
description: >-
  Dansk murerfaglig videnbase på mesterniveau: murværk, mørteltyper og omfugning,
  puds og kalkning, fugt i murværk og kældre, revner, murbindere og hulmure,
  bærende indgreb og vådrum (afretning, membran, fliser) med normgrundlag (BR18,
  DS/EN 1996, BUILD 252, Slots- og Kulturstyrelsens retningslinjer), faglig praksis,
  tjeklister og erfaringsblade. Bruges af murermester-agenten og direkte ved
  murerspørgsmål, hvor subagenter ikke er tilgængelige (fx claude.ai).
---

# Murer-videnbase

| Fil | Indhold | Læs når |
|---|---|---|
| `references/rammer.md` | Standardløsninger inden for rammer (hvad en mester gør uden ingeniør), status V/T/P | **Først – før henvisning til statiker** |
| `references/normgrundlag.md` | Kilder, bindende krav, mørtelbetegnelser, status | Krav, normer, myndighed |
| `references/faglig-praksis.md` | Mørtelvalg, omfugning, puds, fugt, kældre, revner, bærende indgreb, vådrum | Projektering, vurdering, fejlfinding |
| `references/tjeklister.md` | Forundersøgelse, projektering, hold points, aflevering | KS, tilbudsgennemgang, aflevering |
| `references/erfaringsblade.md` | Reviewede, forankrede erfaringer | Altid – hurtigt skim |

## Brug uden subagent
Kører du ikke som `murermester`-agenten (fx i claude.ai eller i hovedtråden), så læs agentdefinitionen `${CLAUDE_PLUGIN_ROOT}/agents/murermester.md` og arbejd efter dens rolle, kerneprincipper og fælles protokol.

## Statusmærker
**V** = verificeret mod kilde (dato). **T** = typisk værdi eller udgave, der skal verificeres før brug som krav. **P** = anerkendt praksis godkendt af en fagperson (dato) – kun i `rammer.md`, se dér. **P – mangler** = ikke udfyldt endnu; brug den normale arbejdsgang.
