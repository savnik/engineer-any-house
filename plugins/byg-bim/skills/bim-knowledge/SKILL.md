---
name: bim-knowledge
description: >-
  BIM-modellørens videnbase og værktøj: bygger, kontrollerer, tegner og redigerer IFC-modeller
  (IFC4) af huse med en deterministisk værktøjskæde (modelspec i YAML → IfcOpenShell → IFC),
  afkodning af scannede tegninger (PDF-oversigt, pixelgitter, kalibrering, kontrol af aflæste mål),
  sammenligning af tegning og model, kontrol mod buildingSMART-regler, IDS, kollisioner og
  BBR-arealer, planer/snit/facader/3D som PNG og redigering af fremmede IFC-filer. Bruges af
  bim-modeller, bim-comparer og bim-lookup og direkte, når nogen vil have en BIM- eller IFC-model af et
  hus, tegninger eller arealer fra en model, eller vil åbne, kontrollere eller rette en IFC-fil.
---

# BIM-modellør – videnbase og værktøj

## Værktøjet
```
BIM="${CLAUDE_PLUGIN_ROOT}/skills/bim-knowledge/scripts/bim.py"
python3 "$BIM" setup          # første gang: eget Python-miljø i ~/.local/share/byg-bim/venv (≈15 s)
```
Er `${CLAUDE_PLUGIN_ROOT}` ikke udfoldet, så find scriptet med Glob `**/bim-knowledge/scripts/bim.py` under `~/.claude/plugins/`.

| Kommando | Gør | Tid |
|---|---|---|
| `pdf <fil.pdf> --overview` · `pdf <fil.pdf> --pages 23,25 --dpi 200 --out <mappe>` | Kontaktark over alle sider · rasterisering af tegningssider | 2–10 s |
| `grid <png> [--crop x0,y0,x1,y1] [--step 50] [--zoom 2]` | Pixelgitter i originale koordinater til aflæsning af punkter og mål | < 1 s |
| `lines <png> --crop x0,y0,x1,y1 [--fraction 0.5]` | Præcise pixelpositioner af lodrette og vandrette streger i et smalt udsnit (vægflader, lysninger, hjælpelinjer) – til kalibreringspunkter og målenes fod | < 1 s |
| `scale --cal "x1,y1,x2,y2=mm;…" [--measured …]` | Målestok fra kendte mål (X og Y hver for sig) | < 1 s |
| `decode template` · `decode check <decoding.yaml>` | Skabelon med alle nøgler · kontrol af afkodningen: format, kalibrering (rest, skala mod målestok), hvert aflæst mål mod afstanden på tegningen, målkæders sum | < 1 s |
| `propose <model.yaml> <navn>` · `merge <forslag.yaml> [--dry-run] [--note …]` | Ny forslagsfil oven på hovedmodellen · godkendt forslag ind i hovedmodellen (kun berørte elementer, historik, konfliktstop) | < 2 s |
| `property-card <model.yaml> [--check] [--import <kort.md>]` | Ejendomskortet genereret fra hovedmodellens `fakta:` (`references/spec.md`, "Ejendomskort fra hovedmodellen") | < 1 s |
| `build <model.yaml> [--out fil.ifc]` | Spec → IFC + `<navn>.byg.json`. SPEC-FEJL vises samlet med sti til feltet | < 1 s |
| `check <fil.ifc> [--draw]` | Skema/EXPRESS, buildingSMART-regler, geometri, kollisioner, Status/materialer, kildefordeling, arealer mod BBR, IDS. Skriver `<navn>.check.md` | 1–3 s |
| `compare <fil.ifc> <decoding.yaml> [--view V1] [--out <mappe>]` | Modellen tegnet i tegningens pixelramme: original · model · overlay (hele visningen og fliser) + automatisk sammenligning af alle afkodede mål, rum, åbninger og vægtykkelser med modellen | 3–10 s |
| `draw <fil.ifc> plan|section|elevation|3d|all [--storey] [--line] [--side] [--id] [--dims]` | Plan (snit +1 m), lodret snit, facader, 3D | 2–8 s |
| `export <fil.ifc> [--out <fil.glb>] [--transparent <glob>…] [--alpha 0.15]` | 3D til webvisning (model-viewer, three.js): glTF i modellens farver, uden rum og huller; `--transparent` gør elementer (id/Tag-glob, fx `"*-YV.1"`) gennemsigtige | 1–3 s |
| `measure <fil.ifc|model.yaml> <id> [<id2>]` · `--space <navn>` · `--storey <navn>` | Mål i mm i ét kald: væg (længde, tykkelse, højde, inder-/yderflade, åbninger), rum (indvendige mål, areal), fri afstand mellem to elementer, alle vægge på en etage – altid med kilden. En `model.yaml` bygges først, så målet er fra den aktuelle model | < 1 s |
| `elplan <fil.ifc|model.yaml> [--out <fil.md>]` | El-plan pr. rum: punktliste, stikkontakter mod § 57 (BEK 1082/2016, inkl. køkken ≥ 3 på ≥ 2 kredse), afbrydertype pr. lysgruppe og fund (lamper uden gruppe, grupper uden betjening). Exit 1 ved mangler | < 1 s |
| `info` · `show <id>` · `find "<selector>"` · `diff <gammel> <ny>` | Inspektion og ændringer | < 5 s |

Udskrifterne er korte med vilje. Detaljer står i filerne – læs dem kun, når udskriften ikke er nok.

## Metoder
- **Tegningsimport** (PDF → afkodning → model → uafhængig sammenligning → rettelse, højst 3 runder): skill `drawing-import`. Hovedtråden orkestrerer; `bim-modeller` afkoder og bygger; `bim-comparer` sammenligner. Afkodningens format: `references/decoding.md`.
- **Ny model uden tegninger** (opmåling, fotos, BBR): spec direkte efter `references/spec.md`.
- **Ændringer i en eksisterende model:** altid som forslag oven på hovedmodellen – `propose` → byg/kontrol → `merge` efter godkendelse (`references/spec.md`, "Hovedmodel og forslag"). Hovedmodellen rettes aldrig direkte.
- **Renovering:** projektspec med `basis:` (`references/spec.md`, "Renovering") – også et forslag; den valgte variant flettes ind.
- **Fremmed IFC:** kopi → `info`/`check` → ret efter `references/editing.md` → `diff` → `check`.

## Filer i sagen
```
<sagsmappe>/bim/model.yaml                     hovedmodellen – eneste source of truth (ændres kun med `merge`)
<sagsmappe>/bim/proposals/<navn>.yaml          forslag/varianter oven på hovedmodellen (her arbejdes der)
<sagsmappe>/bim/history/                       versioner før/efter hver fletning, flettede forslag, merge-log.md
<sagsmappe>/bim/sources/<K-id>/                sider som PNG, gitter, beskæringer og decoding.yaml
<sagsmappe>/bim/out/<property-id>.ifc          genereret – aldrig håndredigeret (+ .byg.json, .check.md)
<sagsmappe>/bim/out/drawings/                  planer, snit, facader, 3D
<sagsmappe>/bim/comparison/<K-id>-<visning>-r<n>/   sammenligningsbilleder og -tabeller pr. runde
<sagsmappe>/bim/in/                            fremmede originalfiler (urørte)
```

## Referencer
| Fil | Indhold | Læs når |
|---|---|---|
| `references/spec.md` | Modelspecens format: sektioner, felter, konventioner, art-tabel, mønstre, renovering | Altid, når du skriver eller retter model.yaml |
| `references/decoding.md` | Afkodning af tegninger: format, fremgangsmåde, kalibrering, faldgruber i gamle tegninger | Tegningsimport |
| `references/comparison.md` | Sammenligningens metode, kategorier, alvor og JSON-svar | bim-comparer; rettelser efter sammenligning |
| `references/practice.md` | LOIN for husmodeller, koordinater og koter, danske byggemål, modelleringsregler | Opstart, tvivl om detaljering |
| `references/editing.md` | Fremmede IFC-filer: ifcquery/ifcedit, IfcOpenShell 0.9-opskrifter, ifcpatch | Redigering af andres filer, nødudgang |
| `references/standards.md` | IFC/ISO, buildingSMART-regler, IDS, LOIN, danske forhold – status V/T | Krav, aflevering til fagfolk |
| `references/checklists.md` | Før modellering, pr. etage, før aflevering, fremmed fil | KS og aflevering |
| `references/lessons.md` | Verificerede faldgruber i værktøj og modellering | Altid – hurtigt skim |

## Visning hos brugeren
Gratis viewere til Mac: **BIMcollab Zoom** (gratis tilstand) og **Open IFC Viewer** (ODA); desuden **Bonsai** i Blender og webviewere bygget på web-ifc (filen bliver lokalt i browseren). Ved aflevering til fagfolk: upload IFC-filen til **validate.buildingsmart.org** (gratis login) for den officielle kontrol.

## Brug uden subagent
Kører du ikke som `bim-modeller`, så læs `${CLAUDE_PLUGIN_ROOT}/agents/bim-modeller.md` og arbejd efter dens rolle og kerneprincipper. Uden Bash (fx claude.ai-chat) kan værktøjet ikke køres; så kan du kun rådgive og skrive spec og afkodning. Sammenligningen skal altid laves i en separat kontekst (subagent), aldrig af den, der byggede modellen.

## Statusmærker
**V** = verificeret mod kilde (dato). **T** = skal verificeres før brug som krav.
