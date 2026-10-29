---
name: structural-knowledge
description: >-
  Dansk statikfaglig videnbase og regneværktøj for bærende konstruktioner i huse og
  mindre bygninger: hvad er bærende, fjernelse af bærende vægge og nye åbninger,
  stål- og limtræsbjælker, vederlag og punktlaster, bjælkelag, tag, hanebånd og kviste,
  ændrede laster, stabilitet, fundering, sætninger og revner, midlertidig understøtning
  og review af statisk dokumentation – med normgrundlag (BR18 kap. 15 og 26,
  Eurocodes med danske nationale annekser), faglig praksis,
  betonskader i fundamenter og kældervægge (diagnose, prøver og reparation efter
  DS/EN 1504), tjeklister, erfaringsblade, en FEM-model (fem.py: bjælker, søjler, rammer, spær og
  vægge/dæk som skalelementer med PNG-tegninger, farvekort og interaktiv 3D-HTML) og et overslagsværktøj (statik.py). Bruges af statiker-agenten og direkte ved
  statikspørgsmål, hvor subagenter ikke er tilgængelige.
---

# Statiker – videnbase

| Fil | Indhold | Læs når |
|---|---|---|
| `references/frames.md` | Standardløsninger inden for rammer (triage: inden for / på grænsen / uden for), status V/T/P | **Først – før der regnes** |
| `references/standards.md` | BR18, konstruktionsklasser, Eurocodes og NA, laster (inkl. snelast C_e efter DK NA), partialkoefficienter – med status | Krav, myndighed, laster |
| `references/practice.md` | Er væggen bærende, egenlaster, typiske indgreb, revner og sætninger, understøtning, review | Vurdering, projektering, second opinion |
| `references/concrete-damage.md` | Betonskader i fundament, sokkel og kældervæg: mekanismer, revner og overvågning, undersøgelse, tre udfald, reparation efter DS/EN 1504 | Smuldrende beton, revner i fundament eller kælder |
| `references/fem.md` | `fem.py`: FEM-model (spec, kommandoer, fortegn, grænser, bilag) – bruges til alle konkrete beregninger, der ikke er dækket af en ramme | Før hver beregning |
| `references/calc-tools.md` | `statik.py`: lastopgørelse, udnyttelse, håndkontrol – kommandoer, forudsætninger, grænser | Før hvert overslag |
| `references/checklists.md` | Forundersøgelse, hold points HP-STAT, aflevering | KS, tilbud, aflevering |
| `references/lessons.md` | Reviewede, forankrede erfaringer | Altid – hurtigt skim |

## Brug uden subagent
Kører du ikke som `structural-engineer`-agenten, så læs `${CLAUDE_PLUGIN_ROOT}/agents/structural-engineer.md` og arbejd efter dens rolle, kerneprincipper og fælles protokol. Tjek først `references/frames.md`: inden for en ramme regnes der ikke. Ellers: **snitkræfter, reaktioner og nedbøjninger regnes i FEM-modellen (`scripts/fem.py`), al anden regning med `scripts/statik.py`** – også summer og omregninger. Uden mulighed for at køre Python: regn ikke selv; opstil lastopgørelsen som input og overlad tallene til værktøjet eller statikeren.

## Statusmærker
**V** = verificeret mod kilde (dato). **T** = skal verificeres før brug som krav. **P** = anerkendt praksis godkendt af en fagperson (dato) – kun i `frames.md`, se dér. **P – mangler** = ikke udfyldt endnu; brug den normale arbejdsgang.
