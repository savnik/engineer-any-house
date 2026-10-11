# BIM-modellør – forankrede erfaringsblade

Reviewede, generaliserbare erfaringer. Nye blade kommer via `/byg:erfaring`.

Format: `### EB-BIM-<nr>: <titel>` med Situation/Problem/Løsning, Grundlag, Gyldighed, Status og dato.

### EB-BIM-01: Skriv ikke selv IfcOpenShell-kode til egne modeller
- **Problem:** Sprogmodeller skriver forældet IfcOpenShell-kode: `api.run(...)`, `product=` i stedet for `products=[...]`, modulet `void` (nu `feature`) og manglende import af undermoduler (`import ifcopenshell.api.root` osv.). I et benchmark (BIM-Edit 2026) løste fri kodegenerering kun 3,4 % af redigeringsopgaverne fuldt.
- **Løsning:** Egne modeller laves kun via `model.yaml` + `bim.py byg`. Fremmede filer redigeres efter `rediger.md`.
- **Grundlag:** test af IfcOpenShell 0.9.0; arxiv.org/abs/2606.20146. **Status:** V 2026-10-10.

### EB-BIM-02: Faldgruber i IfcOpenShell 0.9.0 (løst i bim.py)
- `geometry.edit_object_placement` **ændrer den matrix, den får** (enhedsomregning på stedet). Giv altid en kopi.
- `pset.edit_pset` skriver `Status` som IfcLabel (strider mod PSE001) og fejler på IfcLogical = True. Standardsæt oprettes derfor direkte ud fra skabelonens datatyper.
- `geometry.add_window_representation`/`add_door_representation` giver forkerte mål i 0.9.0, så egen karm-, glas- og dørbladsgeometri bruges.
- API-geometrifunktioner tager **meter** (SI). ShapeBuilder tager **projektenheder** (mm). Blandes de, bliver mål 1000× forkerte.
- `ifcopenshell.util.style` findes ikke. `ifcopenshell.draw` crasher med standardindstillinger (svgfill). `geom.tree`-kollision kræver brep-kerne, der ikke virker. Værktøjet bruger egne tegninger og snitbaseret kollisionstjek.
- **Status:** V 2026-10-10 (testet på macOS arm64, Python 3.14).

### EB-BIM-03: Venstre/højre forveksles – brug yderside/inderside
- **Problem:** En vægjustering "venstre" i tegneretningen lagde gavlene uden for huset, så rummet ikke lukkede.
- **Løsning:** `justering: yderside|inderside` (også på åbne vægge – bygningens midte er "inde"). Kontrollér altid planen.
- **Status:** V 2026-10-10.

### EB-BIM-04: Indervægge og søjler slutter under dækket
- **Problem:** Indervægge og søjler i fuld etagehøjde stak op gennem etagedækket (kollision), og bjælker blev lagt med overkant i gulvniveau.
- **Løsning:** Værktøjets standardhøjde stopper ved undersiden af næste etages dæk. Bjælkers z er overkanten under dækket.
- **Status:** V 2026-10-10.

### EB-BIM-05: Læs tal, mål ikke – og zoom først
- **Problem:** Sprogmodeller læser tekst sikkert, men aflæser afstande i billeder upræcist. Arealskøn fra billeder kan afvige ca. 40 %. Et A3-ark nedskaleres, så målteksten bliver ulæselig.
- **Løsning:** Kontaktark → én side → `gitter --beskaer --zoom 2` pr. målkæde. Påskrevne tal er grundlaget. Kalibrér X og Y hver for sig med ≥ 3 punkter. `afkod tjek` fanger fejllæste tal (mål mod tegning, kædesum).
- **Grundlag:** AECV-Bench (arxiv 2601.04819); test i bim.py. **Status:** V 2026-10-10.

### EB-BIM-06: Målpunkter ved bygningsdelen
- **Problem:** Med målpunkter på målelinjen kunne sammenligningen matche en flade et helt andet sted på samme koordinat (fx en dørlysning) og godkende en flyttet væg.
- **Løsning:** Afkod `fra`/`til` ved hjælpelinjens fod. Brug kun `paa_maalelinje: true`, når foden ikke kan ses.
- **Status:** V 2026-10-11.
