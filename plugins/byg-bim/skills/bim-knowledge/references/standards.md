# BIM-modellør – normgrundlag

Sidst gennemgået: 2026-10-10. **V** = verificeret (kilde, dato), **T** = skal verificeres før brug som krav.

| Kilde | Indhold | Status |
|---|---|---|
| ISO 16739-1:2018 (IFC4 ADD2 TC1) | IFC4 – standardformat for bygningsmodeller. Header `IFC4`. Understøttet bredt (Revit link/eksport, ArchiCAD, BIMcollab Zoom, Solibri, Bonsai, web-ifc) | V (buildingsmart.org, 2026-10-10) |
| ISO 16739-1:2024 (IFC 4.3 ADD2) | IFC4X3 – fokus på infrastruktur. Endnu ingen certificeret software til 4.3 (NordicBIM 2026-05). Brug kun efter aftale | V (buildingsmart.org; nordicbim.com, 2026-10-10) |
| buildingSMART Validation Service | Syntaks, skema, normative regler (fejl) og industry practice (advarsler). Gratis login, maks. 256 MB, ingen IDS | V (github.com/buildingSMART/validate, 2026-10-10) |
| Normative regler (ifc-gherkin-rules) | SPS001 højst én IfcSite · SPS002 rumlig struktur · SPS005/007 containment, IfcSpace aggregeres · GEM002 IfcSpace har Body · GEM111 polylinjer · SWE001 profiler må ikke skære sig selv · PSE001 Pset_-navne, datatyper og enumererede værdier · QTY001 Qto_ med BaseQuantities · GRF000/003/005 georeference, IfcProjectedCRS, Scale 0,001 ved mm · IFC102 *StandardCase forældet · OJT001/BLT001 USERDEFINED kræver ObjectType | V (github.com/buildingSMART/ifc-gherkin-rules, 2026-10-10) |
| IDS 1.0 (buildingSMART, 2024-06-03) | Informationskrav, der kan maskintjekkes (ifctester). Værktøjets standard: `assets/ids/byg-bolig.ids` | V (github.com/buildingSMART/IDS/releases, 2026-10-10) |
| ISO 7817-1:2024 (LOIN) | Detaljeringsniveau efter formål. Afløser EN 17412-1. Udgivelse som DS/EN ikke verificeret | V / T (DS-udgave) (iso.org, 2026-10-10) |
| EPSG:25832 · EPSG:5799 (DVR90) · EPSG:7416 | Danske koordinater (ETRS89/UTM32N) og højder (DVR90) til IfcMapConversion | V (epsg.io, 2026-10-10) |
| IKT-bekendtgørelsen (BEK nr. 118 af 06.02.2013) | Kun offentligt byggeri (stat ≥ 5 mio. kr., kommuner/regioner ≥ 20 mio. kr.). **Gælder ikke private boligejere** | V (retsinformation.dk, 2026-10-10) |
| CCS/CCI (Molio) | Dansk klassifikation, identifikation, egenskaber og informationsniveauer 1–7. Gratis | V (molio.dk, 2026-10-10) |
| BIMTypeCode 2022 DK (BIM7AA) | Typekoder (3 tegn) og psetfil `BIMTypeCode` på IfcElementType | V (bimtypecode.com; github.com/bimtypecode, 2026-10-10) |
| BR18 | Ingen krav om BIM/IFC ved private enfamiliehuse. Byggetilladelse kræver tegninger efter kommunens krav | T |

## Opslagsrækkefølge
1. buildingsmart.org · github.com/buildingSMART (IFC, regler, IDS) · ifc43-docs.standards.buildingsmart.org
2. docs.ifcopenshell.org (værktøj) · molio.dk · bimtypecode.com
3. retsinformation.dk · bygningsreglementet.dk (myndighedskrav)
