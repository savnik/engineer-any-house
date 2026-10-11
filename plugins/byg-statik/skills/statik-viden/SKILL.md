---
name: statik-viden
description: >-
  Dansk statikfaglig videnbase og regneværktøj for bærende konstruktioner i huse og
  mindre bygninger: hvad er bærende, fjernelse af bærende vægge og nye åbninger,
  stål- og limtræsbjælker, vederlag og punktlaster, bjælkelag, tag, hanebånd og kviste,
  ændrede laster, stabilitet, fundering, sætninger og revner, midlertidig understøtning
  og review af statisk dokumentation – med normgrundlag (BR18 kap. 15 og 26,
  Eurocodes med danske nationale annekser), faglig praksis, tjeklister, erfaringsblade
  og et overslagsværktøj (statik.py). Bruges af statiker-agenten og direkte ved
  statikspørgsmål, hvor subagenter ikke er tilgængelige.
---

# Statiker – videnbase

| Fil | Indhold | Læs når |
|---|---|---|
| `references/normgrundlag.md` | BR18, konstruktionsklasser, Eurocodes og NA, laster, partialkoefficienter – med status | Krav, myndighed, laster |
| `references/faglig-praksis.md` | Er væggen bærende, egenlaster, typiske indgreb, revner og sætninger, understøtning, review | Vurdering, projektering, second opinion |
| `references/regnevaerktoej.md` | `statik.py`: kommandoer, forudsætninger, grænser | Før hvert overslag |
| `references/tjeklister.md` | Forundersøgelse, hold points HP-STAT, aflevering | KS, tilbud, aflevering |
| `references/erfaringsblade.md` | Reviewede, forankrede erfaringer | Altid – hurtigt skim |

## Brug uden subagent
Kører du ikke som `statiker`-agenten, så læs `${CLAUDE_PLUGIN_ROOT}/agents/statiker.md` og arbejd efter dens rolle, kerneprincipper og fælles protokol. **Al regning sker med `scripts/statik.py`** – også summer og omregninger. Uden mulighed for at køre Python: regn ikke selv; opstil lastopgørelsen som input og overlad tallene til værktøjet eller statikeren.

## Statusmærker
**V** = verificeret mod kilde (dato). **T** = skal verificeres før brug som krav.
