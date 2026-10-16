---
name: bim-viden
description: >-
  BIM-modellørens videnbase og værktøj: bygger, kontrollerer, tegner og redigerer IFC-modeller
  (IFC4) af huse med en deterministisk værktøjskæde (modelspec i YAML → IfcOpenShell → IFC),
  afkodning af scannede tegninger (PDF-oversigt, pixelgitter, kalibrering, kontrol af aflæste mål),
  sammenligning af tegning og model, kontrol mod buildingSMART-regler, IDS, kollisioner og
  BBR-arealer, planer/snit/facader/3D som PNG og redigering af fremmede IFC-filer. Bruges af
  bim-modelloer og bim-sammenligner og direkte, når nogen vil have en BIM- eller IFC-model af et
  hus, tegninger eller arealer fra en model, eller vil åbne, kontrollere eller rette en IFC-fil.
---

# BIM-modellør – videnbase og værktøj

## Værktøjet
```
BIM="${CLAUDE_PLUGIN_ROOT}/skills/bim-viden/scripts/bim.py"
python3 "$BIM" opsaet          # første gang: eget Python-miljø i ~/.local/share/byg-bim/venv (≈15 s)
```
Er `${CLAUDE_PLUGIN_ROOT}` ikke udfoldet, så find scriptet med Glob `**/bim-viden/scripts/bim.py` under `~/.claude/plugins/`.

| Kommando | Gør | Tid |
|---|---|---|
| `pdf <fil.pdf> --oversigt` · `pdf <fil.pdf> --sider 23,25 --dpi 200 --ud <mappe>` | Kontaktark over alle sider · rasterisering af tegningssider | 2–10 s |
| `gitter <png> [--beskaer x0,y0,x1,y1] [--trin 50] [--zoom 2]` | Pixelgitter i originale koordinater til aflæsning af punkter og mål | < 1 s |
| `linjer <png> --beskaer x0,y0,x1,y1 [--andel 0.5]` | Præcise pixelpositioner af lodrette og vandrette streger i et smalt udsnit (vægflader, lysninger, hjælpelinjer) – til kalibreringspunkter og målenes fod | < 1 s |
| `skala --kal "x1,y1,x2,y2=mm;…" [--maal …]` | Målestok fra kendte mål (X og Y hver for sig) | < 1 s |
| `afkod skabelon` · `afkod tjek <afkodning.yaml>` | Skabelon med alle nøgler · kontrol af afkodningen: format, kalibrering (rest, skala mod målestok), hvert aflæst mål mod afstanden på tegningen, målkæders sum | < 1 s |
| `forslag <model.yaml> <navn>` · `flet <forslag.yaml> [--proev] [--note …]` | Ny forslagsfil oven på hovedmodellen · godkendt forslag ind i hovedmodellen (kun berørte elementer, historik, konfliktstop) | < 2 s |
| `ejendomskort <model.yaml> [--tjek] [--importer <kort.md>]` | Ejendomskortet genereret fra hovedmodellens `fakta:` (`references/spec.md`, "Ejendomskort fra hovedmodellen") | < 1 s |
| `byg <model.yaml> [--ud fil.ifc]` | Spec → IFC + `<navn>.byg.json`. SPEC-FEJL vises samlet med sti til feltet | < 1 s |
| `tjek <fil.ifc> [--tegn]` | Skema/EXPRESS, buildingSMART-regler, geometri, kollisioner, Status/materialer, kildefordeling, arealer mod BBR, IDS. Skriver `<navn>.tjek.md` | 1–3 s |
| `sammenlign <fil.ifc> <afkodning.yaml> [--visning V1] [--ud <mappe>]` | Modellen tegnet i tegningens pixelramme: original · model · overlay (hele visningen og fliser) + automatisk sammenligning af alle afkodede mål, rum, åbninger og vægtykkelser med modellen | 3–10 s |
| `tegn <fil.ifc> plan|snit|facade|3d|alle [--etage] [--linje] [--side] [--id] [--maal]` | Plan (snit +1 m), lodret snit, facader, 3D | 2–8 s |
| `info` · `vis <id>` · `find "<selector>"` · `diff <gammel> <ny>` | Inspektion og ændringer | < 5 s |

Udskrifterne er korte med vilje. Detaljer står i filerne – læs dem kun, når udskriften ikke er nok.

## Metoder
- **Tegningsimport** (PDF → afkodning → model → uafhængig sammenligning → rettelse, højst 3 runder): skill `tegningsimport`. Hovedtråden orkestrerer; `bim-modelloer` afkoder og bygger; `bim-sammenligner` sammenligner. Afkodningens format: `references/afkodning.md`.
- **Ny model uden tegninger** (opmåling, fotos, BBR): spec direkte efter `references/spec.md`.
- **Ændringer i en eksisterende model:** altid som forslag oven på hovedmodellen – `forslag` → byg/kontrol → `flet` efter godkendelse (`references/spec.md`, "Hovedmodel og forslag"). Hovedmodellen rettes aldrig direkte.
- **Renovering:** projektspec med `basis:` (`references/spec.md`, "Renovering") – også et forslag; den valgte variant flettes ind.
- **Fremmed IFC:** kopi → `info`/`tjek` → ret efter `references/rediger.md` → `diff` → `tjek`.

## Filer i sagen
```
<sagsmappe>/bim/model.yaml                     hovedmodellen – eneste source of truth (ændres kun med `flet`)
<sagsmappe>/bim/forslag/<navn>.yaml            forslag/varianter oven på hovedmodellen (her arbejdes der)
<sagsmappe>/bim/historik/                      versioner før/efter hver fletning, flettede forslag, flettelog.md
<sagsmappe>/bim/kilder/<K-id>/                 sider som PNG, gitter, beskæringer og afkodning.yaml
<sagsmappe>/bim/ud/<ejendom-id>.ifc            genereret – aldrig håndredigeret (+ .byg.json, .tjek.md)
<sagsmappe>/bim/ud/tegninger/                  planer, snit, facader, 3D
<sagsmappe>/bim/sammenligning/<K-id>-<visning>-r<n>/   sammenligningsbilleder og -tabeller pr. runde
<sagsmappe>/bim/ind/                           fremmede originalfiler (urørte)
```

## Referencer
| Fil | Indhold | Læs når |
|---|---|---|
| `references/spec.md` | Modelspecens format: sektioner, felter, konventioner, art-tabel, mønstre, renovering | Altid, når du skriver eller retter model.yaml |
| `references/afkodning.md` | Afkodning af tegninger: format, fremgangsmåde, kalibrering, faldgruber i gamle tegninger | Tegningsimport |
| `references/sammenligning.md` | Sammenligningens metode, kategorier, alvor og JSON-svar | bim-sammenligner; rettelser efter sammenligning |
| `references/faglig-praksis.md` | LOIN for husmodeller, koordinater og koter, danske byggemål, modelleringsregler | Opstart, tvivl om detaljering |
| `references/rediger.md` | Fremmede IFC-filer: ifcquery/ifcedit, IfcOpenShell 0.9-opskrifter, ifcpatch | Redigering af andres filer, nødudgang |
| `references/normgrundlag.md` | IFC/ISO, buildingSMART-regler, IDS, LOIN, danske forhold – status V/T | Krav, aflevering til fagfolk |
| `references/tjeklister.md` | Før modellering, pr. etage, før aflevering, fremmed fil | KS og aflevering |
| `references/erfaringsblade.md` | Verificerede faldgruber i værktøj og modellering | Altid – hurtigt skim |

## Visning hos brugeren
Gratis viewere til Mac: **BIMcollab Zoom** (gratis tilstand) og **Open IFC Viewer** (ODA); desuden **Bonsai** i Blender og webviewere bygget på web-ifc (filen bliver lokalt i browseren). Ved aflevering til fagfolk: upload IFC-filen til **validate.buildingsmart.org** (gratis login) for den officielle kontrol.

## Brug uden subagent
Kører du ikke som `bim-modelloer`, så læs `${CLAUDE_PLUGIN_ROOT}/agents/bim-modelloer.md` og arbejd efter dens rolle og kerneprincipper. Uden Bash (fx claude.ai-chat) kan værktøjet ikke køres; så kan du kun rådgive og skrive spec og afkodning. Sammenligningen skal altid laves i en separat kontekst (subagent), aldrig af den, der byggede modellen.

## Statusmærker
**V** = verificeret mod kilde (dato). **T** = skal verificeres før brug som krav.
