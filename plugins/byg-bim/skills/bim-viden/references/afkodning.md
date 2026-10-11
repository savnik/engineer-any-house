# Afkodning af tegninger

Afkodningen er det strukturerede udtræk af **alt** på en tegning, før der bygges. Den er grundlaget for modellen, for sammenligningen og for sporbarheden (hvert modelmål kan føres tilbage til et mål-id på en tegning). `bim.py afkod tjek` kontrollerer den mod tegningen selv.

## Grundregler
1. **Læs tal, mål ikke.** Påskrevne mål har altid forrang. Skalering fra billedet bruges kun, hvor der ikke står et mål, og bliver en usikkerhed på ca. 3 px × skala. Sprogmodeller læser tekst sikkert, men aflæser afstande i billeder upræcist.
2. **Zoom, før du læser.** Brug `gitter --beskaer x0,y0,x1,y1 --trin 50 --zoom 2` på hver målkæde og hvert rum. Et helt A3-ark i ét billede bliver skaleret ned, og så er tallene ulæselige.
3. **Alt skal med, også det, modellen ikke skal bruge:** tekster om materialer, "bærende", koter, rettelser og stempler med betydning. Det ulæselige skrives under `usikre`. Personnavne udelades.
4. **Pixelkoordinater er originalbilledets** (gitterets tal). Brug altid samme rasterisering (samme dpi) som `kilde.fil`.

## Fremgangsmåde
1. `pdf <fil> --oversigt` → find tegningssiden. `pdf <fil> --sider <n> --dpi <d>` → `kilder/K<m>/`. Vælg en dpi tæt på scanningens ppi (udskriften viser den), typisk 200–300.
2. **Overblik:** `gitter <side.png> --trin 200`. Find titelblok, målestok, nordpil og visningerne (plan, snit, facade), og notér hver visnings bbox.
3. **Pr. visning, systematisk:** ydre målkæder (alle sider), indre målkæder, vægtykkelser, rum, døre og vinduer, trapper, skorsten/søjler/bjælker, koter, tekster og snitmarkeringer.
4. **Præcise punkter:** aflæs ikke pixelkoordinater med øjet, når der skal bruges præcision. Læg et smalt udsnit over stregen, og kør `linjer <png> --beskaer x0,y0,x1,y1`. Den giver stregens midte i originale pixel. Brug den til kalibreringspunkter (ydre hjørner = skæringen af to vægflader) og til hjælpelinjernes fod.
5. **Origo og kalibrering:** vælg origo (fx ydervæggenes SV-hjørne) og regn modelkoordinaterne for 3–4 veldefinerede punkter langt fra hinanden **ud fra de påskrevne mål**: ydre hjørner, eller for snit og facade gulvlinjer og hjørner. Kalibreringen er affin, så X- og Y-skala kan afvige (papirkrymp, scanner).
6. `afkod tjek` → 0 fejl. Passer et mål ikke med tegningen, så se på det igen i originalen. Enten er tallet fejllæst ("4,50"/"4,30", "1,18"/"1,78"), endepunkterne er forkerte, eller tegningen er ikke målfast. I det sidste tilfælde gælder det påskrevne tal for modellen, og stedet noteres under `usikre`.

## Format (`kilder/K<m>/afkodning.yaml`)
Formatet herunder er udtømmende. `bim.py afkod skabelon > afkodning.yaml` giver en kopi at udfylde. Værktøjets kildekode skal ikke læses.
```yaml
kilde:
  id: K1
  fil: byggesag-s24.png                 # rasteriseret side (relativ sti)
  dokument: "Byggesagsarkiv, sag 1, s. 24"
  titel: "Kælderplan 1:100"
  maalestok: "1:100"
  dpi: 200                                 # rasteriseringens dpi – bruges til kontrol af målestokken
  dato: 1937
  enhed_paa_tegning: m                     # sådan står tallene: m ("4,50"), cm ("450") eller mm
  maaltype: raahus                         # raahus (murværk) | faerdig | akse | ukendt
visninger:
  - id: V1
    type: plan                             # plan | snit | facade | detalje | situationsplan | tekst
    etage: K                               # modellens etage-id (plan) · snit: linje: [x1,y1,x2,y2] · facade: side: syd
    bbox: [180, 220, 1650, 1480]           # visningen i pixel
    snithoejde: 1000                       # valgfri – snithøjden i modellens plantegning
    kal:                                   # px → model-mm (plan: x,y · snit/facade: u langs visningen, z = højde)
      - {px: [212, 1402], model: [0, 0], note: "SV-hjørne yderside"}
      - {px: [1590, 1398], model: [10500, 0], note: "SØ-hjørne yderside (M1)"}
      - {px: [1593, 300], model: [10500, 8300], note: "NØ-hjørne (M9)"}
      - {px: [209, 305], model: [0, 8300]}
    maal:
      - {id: M1, tekst: "10,50", vaerdi: 10500, fra: [212, 1402], til: [1590, 1398], retning: x, kaede: S, total: true}
      - {id: M2, tekst: "1,20", vaerdi: 1200, fra: [212, 1402], til: [370, 1401], retning: x, kaede: S}
      - {id: M3, tekst: "4,50", vaerdi: 4500, fra: [250, 1450], til: [841, 1450], retning: x, paa_maalelinje: true}
    rum:
      - {navn: Fyrrum, punkt: [500, 900], areal: null, tekst: "Fyr"}
    aabninger:
      - {id: O1, type: vindue, punkt: [450, 1400], bredde: 800, tekst: "80"}
      - {id: O2, type: doer, punkt: [930, 860], bredde: 800, slag: "mod øst, hængsel nord"}
    vaegge:
      - {punkt: [215, 900], tykkelse: 300, materiale: beton, tekst: "30 Beton"}
    koter:
      - {punkt: [300, 1500], kote: 34.60, beskrivelse: kældergulv, datum: "ukendt (DNN?)"}   # m; datum: DVR90 | DNN | lokalt | relativ (til ±0)
    trapper:
      - {punkt: [900, 700], stigninger: 13, retning: "op mod nord", tekst: "13 Tr."}
    tekster:
      - {punkt: [800, 1550], tekst: "Kælderen må ikke benyttes til beboelse", betydning: myndighed}
    snitmarkeringer:
      - {navn: A-A, fra: [600, 200], til: [600, 1500]}
    usikre:
      - {punkt: [1200, 700], beskrivelse: "mål ved trappen ulæseligt (2,?5)"}
```
- **Mål:** `vaerdi` i mm, `tekst` som skrevet. `fra`/`til` er **hjælpelinjernes fod ved bygningsdelen**, så sammenligningen kan finde præcis den flade, målet går til. Kan foden ikke ses, så sæt punkterne på målelinjen og `paa_maalelinje: true`. Delmål i en kæde får samme `kaede`, og totalen `total: true`. Kontrollen summerer kæden. `retning` er x|y i plan, u|z i snit/facade, ellers fri.
- **Snit og facader:** `model` i `kal` er (u, z). For facader er u den vandrette akse set udefra (venstre → højre), og z er højden i mm i modellens system (±0 = stueetagens gulv). For snit er u afstanden langs snitlinjen fra dens første punkt.
- Ekstra nøgler (`trapper`, `snitmarkeringer`, `slag`) er tilladte og bruges af sammenligneren som tjekliste.

## Gamle danske tegninger (1900–1980) – faldgruber
- **Mål:** typisk i m med komma ("4,50") eller cm ("450"), ofte til **murværk (råhus)** uden puds. Delmål for murpiller og åbninger står i ydre kæder. Indre mål står i rummene. En hævet lille skrift er centimeter ("4,50⁵" = 4505 mm). [ERFARING]
- **Murværk:** ½ sten ≈ 108 mm (pudset ≈ 130), 1 sten ≈ 228 mm, hulmur "30 cm" = 2 × ½ sten + hulrum. Vægtykkelser står som tal ("30", "½ Sten") eller kan ses af skraveringen. [ERFARING – kontrollér mod tegningens tal]
- **Målfasthed:** håndtegnede planer er sjældent helt målfaste. Påskrevne tal går forud. Kopier og mikrofilm er ofte formindskede, så stol på kalibreringen frem for den påtrykte målestok. [ERFARING]
- **Koter:** gamle koter kan være i DNN eller et lokalt nulpunkt (fx vejmidte), ikke DVR90. Notér `datum`, og brug dem kun relativt, indtil datum er kendt. [T]
- **Ændringer:** byggesager indeholder ofte flere versioner (ansøgning, rettelse, "som udført"). Notér versionen. Den nyeste godkendte er ikke nødvendigvis den udførte. Ombygninger (fx tagetage 1977) har egne tegninger.
- **Signaturer:** stiplede linjer er over snittet (bjælker, overkanter) eller nedrives. Skravering er snit/materiale. Pile med "OP" er trappens retning. Krydsede firkanter er skorstene og aftræk.
- **Kildens egen usikkerhed følger med:** "ca.", "?", "skønnet", blyantsrettelser, signaturforklaringer (fx en markering for antagelser) og "ikke opmålt" skal afkodes og føres videre til modellen som kilde A eller `usikkerhed`, ikke som D.
- **Tegningen er ikke virkeligheden:** sammenligningen viser kun, at modellen svarer til tegningen. Huset kan være bygget anderledes, så kritiske mål skal på opmålingslisten.
