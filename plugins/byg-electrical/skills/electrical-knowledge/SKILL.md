---
name: electrical-knowledge
description: >-
  Dansk el-faglig videnbase på mesterniveau: boliginstallationer, tavler, RCD,
  badeværelser, elbilladning, solceller, varmepumper, gør-det-selv-grænser og
  verifikation med normgrundlag (Elsikkerhedsloven, DS/HD 60364-serien,
  Sikkerhedsstyrelsen), faglig praksis, tjeklister og erfaringsblade. Bruges af
  electrician-agenten og direkte ved el-spørgsmål, hvor subagenter ikke er tilgængelige.
---

# El-videnbase

| Fil | Indhold | Læs når |
|---|---|---|
| `references/standards.md` | Lov, bekendtgørelser, standarder, gør-det-selv-listen, installationsbekendtgørelsens centrale §§, ændring og udvidelse (køkken, tavleflytning, beskyttelsesleder), solceller, netselskab (tilmelding, kortslutningsniveau), badeværelsesområder (701:2024), RCD-typer/kæde/undertavle, TT/TN, SPD, dimensioneringsforudsætninger, status | Krav, grænseværdier, rumkrav, ombygning af eksisterende installation, autorisation, gør-det-selv |
| `references/practice.md` | Principper, løsninger, tavleskabeloner, ældre installationer, fejlfinding, grænseflader | Projektering, vurdering, fejlfinding |
| `references/calc-tools.md` | Regneværktøjet `scripts/el.py`: Iz med korrektion, spændingsfald, Ik,min/Ik,max, tavlekontrol og fast gruppeskema | Dimensionering af gruppe, kabel eller tavle |
| `references/schematic.md` | Tavlediagram (enstregsdiagram): indhold, symboler, `scripts/diagram.py`, eksempel i `assets/` | Ny eller ændret tavle, aflevering |
| `references/checklists.md` | Projektering, hold points, verifikation, aflevering | KS, tilbud, aflevering |
| `references/field-experience.md` | Praktisk erfaring fra udførelse: fejlfinding, tavleudskiftning, ladestander, service og montage | Udførelse, fejlfinding, serviceopgaver |
| `references/lessons.md` | Reviewede, forankrede erfaringer | Altid – hurtigt skim |

## Brug uden subagent
Kører du ikke som `electrician`-agenten, så læs `${CLAUDE_PLUGIN_ROOT}/agents/electrician.md` og arbejd efter dens rolle, kerneprincipper og fælles protokol.

## Statusmærker
**V** = verificeret mod kilde (dato). **T** = skal verificeres før brug som krav.
