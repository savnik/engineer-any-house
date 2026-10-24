# Statiker – FEM-model (`fem.py`)

**Alle konkrete beregninger af snitkræfter, reaktioner og nedbøjninger laves i en FEM-model**, også en simpel bjælke over en åbning (én bjælke, to understøtninger). Undtagelse: situationer inden for en ramme i `rammer.md` regnes ikke. Modellen er dokumentationen: den ligger i sagsmappen, kan genkøres af kontrollen og åbnes af bygherren. `statik.py` bruges til det, FEM-modellen ikke gør: lastopgørelse (`last`), tværsnitsværdier, udnyttelse efter Eurocode (`bjaelke`, `tryk`), anden aritmetik (`regn`) og som uafhængig håndkontrol af FEM-resultatet.

Værktøjet bygger på PyNite (MIT-licens): lineær-elastisk 3D-analyse af stangelementer og flader (vægge, dæk som skalelementer, MITC4) med lastkombinationer og valgfri andenordensanalyse (P-Δ). Det kører i sit eget Python-miljø (`~/.local/share/byg-statik/venv`).

Kør: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/statik-viden/scripts/fem.py <kommando> …`

## Kommandoer
| Kommando | Formål |
|---|---|
| `opsaet` | Opret miljøet (én gang, ca. 1 min) |
| `test` | Selvtest mod håndformler: simpel, delt og kontinuert bjælke (qL²/8, 5qL⁴/384EI), udkraget bjælke (PL, PL³/3EI), ramme (ligevægt, fortegn), plade (Navier), vægskive (n = q, σ = n/t, vind), bjælke på væg (forbindelse) |
| `skabelon [flader]` | Komplet eksempel på `fem.yaml` med alle muligheder; `flader`: hus med vægge, dæk og stålbjælke over en åbning |
| `regn <fem.yaml>` | Analyse → resumé på skærmen og `<navn>.fem.json` i `fem/`-mappen (ligger spec'en i `<sagsmappe>/fem/`, så dér; ellers `<specmappe>/fem/`) (reaktioner, N/V/M, δ og L/δ pr. element og kombination, ligevægtskontrol, spec-sha) |
| `tegn <fem.yaml> [model\|deformation\|M\|V\|N\|spaending\|n_u\|n_v\|pladmoment\|flytning\|alle] [--kombi K]` | PNG til notatet. **Se altid `model`-billedet efter, før du bruger tallene**: geometri, understøtninger, led og laster (pile pr. lasttilfælde). Fladevisningerne er farvekort med maks. markeret |
| `vis <fem.yaml>` | Én HTML-fil til bygherren og fagfolk: drej/zoom, laster som pile (klik i forklaringen for at skjule et lasttilfælde), menu med kombination og størrelse, flader der kan skjules (fx dækket, så væggene ses), værdier ved musen, tabeller |

`regn`, `tegn` og `vis` tager `--saet sti=værdi` (kan gentages), der ændrer ét input uden at røre filen – fx `--saet lasttilfaelde.Q.laster.0.linjelast=4.0` eller `--saet elementer.B1.profil=HEB180`. Kontrollen bruger det til egne input; du kan bruge det til hurtige varianter, men den endelige model står i filen.

## Arbejdsgang
1. **Lastopgørelse med `statik.py last`** (kN/m² × opland → kN/m). Skriv kørslerne i bilaget.
2. **Skriv `<sagsmappe>/fem/fem.yaml`** ud fra `fem.py skabelon`. Ét lasttilfælde pr. lasttype (G, Q, S, W), kommentar med kilde ved hver last.
3. `fem.py regn` → tjek at **ligevægt OK** i alle kombinationer (scriptet returnerer fejl ellers).
4. `fem.py tegn … model` og læs billedet: rigtige knuder, understøtninger, led og lastretninger? Derefter `tegn … alle`.
5. **Håndkontrol:** mindst ét afgørende resultat eftervises uafhængigt med `statik.py` (`bjaelke` for en simpel bjælke, ellers `regn` med en håndformel, fx qL²/8 eller ΣR = Σlast). Afvigelse over 2 % skal forklares.
6. Udnyttelse: brug FEM-resultatets M, V, N og δ i eftervisningen (`statik.py bjaelke` for simple bjælker; ellers `regn` med formlen og kilden). Kipning, søjlestabilitet og samlinger regnes ikke af `fem.py` – se grænserne.
7. `fem.py vis` → HTML-filen lægges i `<sagsmappe>/fem/` og nævnes i notatet, så bygherren kan åbne den.

## Spec (`fem.yaml`)
- **Enheder:** m, kN, kNm; profiler og egne tværsnit i mm. **Akser:** x, y vandret, z lodret op. Knuder `[x, z]` giver en plan model (ramme i x-z-planen); `[x, y, z]` giver 3D.
- **Elementer:** `fra`, `til`, `profil` (IPE/HEA/HEB fra `statik.py`-tabellen, `rekt BxH` i mm, eller eget under `tvaersnit:` med `A`, `I_staerk`, `I_svag`, `J`), `materiale` (C18, C24, GL24h, GL30c, GL32h, S235, S355, C20/25, C25/30, C30/37 eller eget under `materialer:` med `E`, `G` i MPa og `rho` i kN/m³). Valgfrit: `led: [start, slut]` (momentfrit), `udkragning: true`, `graense: 400`, `kun_traek`/`kun_tryk`, `drej` (grader, 3D: tværsnittets rotation om elementaksen).
- **Understøtninger:** `indspaendt`, `charnier`, `rulle` (kun lodret), `rulle-x`, `rulle-y` eller en liste af frihedsgrader `[x, y, z, rx, ry, rz]`.
- **Lasttilfælde:** `egenvaegt: true` (A·rho) og `laster:` – `linjelast` (kN/m pr. m element, ikke vandret projektion; trapez som `[w1, w2]` med `fra`/`til` i m fra elementets start), `punktlast` på element (`x` i m fra start) eller knude, `moment` på knude (`akse`). `retning: ned` (tyngde, positiv nedad – standard) eller `x`, `y`, `z` med fortegn.
- **Kombinationer:** `type: brud` eller `anvendelse`, `faktorer` pr. lasttilfælde, valgfrit `graense` (L/…). Faktorer efter EN 1990 DK NA (se `regnevaerktoej.md`), fx `STR-6.10a: {G: 1.2}`, `STR-6.10b: {G: 1.0, Q: 1.5}`, KFI ganget på.
- `analyse: andenorden` (P-Δ) for rammer og søjler med væsentlig normalkraft.

## Flader – vægge og dæk som skalelementer
Brug flader, når **lastens vej gennem vægge og dæk** er spørgsmålet: hvor samler lasten sig, når en bærende væg fjernes eller får en åbning, hvordan fordeler et dæk lasten, og hvordan afstiver væggene huset mod vind (skivevirkning). En enkelt bjælke over en åbning regnes stadig som element – flader er overblikket over helheden.
- **Spec:** `flader: {navn: {hjoerner: [A, B, C, D], tykkelse: mm, materiale, aabninger: [{x, y, b, h}], mesh: m}}`. Hjørnerne er fire knuder rundt om et rektangel; u går langs A→B, v langs A→D. Tegn vægge med A→B vandret og A→D op, så n_v er den lodrette kraft. Åbninger angives i (u, v) fra A. `mesh:` (standard 0,25 m) kan sættes for hele modellen eller pr. flade.
- **Materialer** skal være isotrope: betonklasserne, S235/S355, `gasbeton` (E 2 500 MPa, ρ 6 kN/m³) og `tegl` (E 6 000 MPa, ρ 18 kN/m³) – typiske overslagsværdier med E = 1000·f_k (EN 1996-1-1, 3.7.2). Kendes f_k, så angiv et eget materiale med `E`, `nu` og `rho`. Træ (bjælkelag, spær) modelleres som elementer.
- **Forbindelser:** flader, der mødes, deler knuder langs fællesranden; spec-knuder og bjælker, der ligger på en flade, forbindes med den i alle knuder på linjen. En bjælke under et dæk virker derfor sammen med dækket.
- **Understøtning langs en linje:** `understoetninger_linje: [{fra, til, type}]` (fx væggenes fod).
- **Laster:** `{flade: navn, tryk: kN/m², retning: ned|x|y|z|normal}` (pr. m² flade), `{linje: [knude, knude], linjelast: kN/m}` (fx tag på murkrone) og `egenvaegt: true` (t·ρ).
- **Resultater** pr. flade og kombination: σ_vM (MPa, største af over- og underside: membran ± bøjning), membrankræfter n_u, n_v, n_uv (kN/m, **tryk < 0**), pladmomenter m_u, m_v (kNm/m), flytning (mm) og de tre steder med størst spænding. `udtraek: {navn: {flade, x: [a, b], y: [c, d]}}` giver maks./min. for et område – fx en vægende under en bjælke. n_v ved foden af en vægende (kN/m) er lasten pr. m væg, der skal eftervises for murværket.
- **Fortolkning:** lineært-elastisk uden revner. Spændinger i hjørner af åbninger og under punktlaster vokser, når meshet gøres finere (singulariteter): brug dem som **markering af, hvor lasten samler sig**, og eftervis vægenden med kraften over en bredde (n_v integreret, eller reaktionen fra bjælken), ikke med toppunktet. Farveskalaen klippes ved 99,5 %-fraktilen; maks. står i noten.
- **Kontrol:** ligevægt OK; se `tegn … model` (pile og flader rigtigt placeret); håndkontrol af en samlet størrelse (ΣR = Σlast, eller n_v midt i en væg ≈ last pr. m).

## Fortegn og resultater
- **N > 0 er træk.** **M > 0 giver træk i elementets underside** (lokal −y; for et vandret element tegnet fra venstre mod højre: undersiden). Momentkurven tegnes på trækssiden.
- **δ** er nedbøjning i forhold til **spændets** korde (mm, negativ = nedad): linjen mellem spændets endeknuder. Et spænd kan bestå af flere elementer på linje – en knude uden understøtning, hvor præcis to elementer mødes på linje (fx ved en punktlast), deler ikke spændet, og L i L/δ er så hele spændets længde (`L_spaend` i JSON). Spændet deles ved understøtninger, samlinger med flere elementer, knæk og `udkragning: true`. For `udkragning: true` er δ absolut, og L/δ regnes med 2L.
- I 3D vises også `M_svag` og `δ_svag` (bøjning om den svage akse). Tjek i 3D tværsnittets orientering (`drej`), især for søjler.

## Grænser – det regner `fem.py` IKKE
Udnyttelse og normkrav (sker i eftervisningen) · kipning, søjle- og pladeinstabilitet (P-Δ giver kun andenordensmomenter, ikke knæklængder) · samlinger, beslag og vederlagstryk · murværkets bæreevne, revner og ikke-lineær opførsel (flader er lineært-elastiske; spændingstoppe er mesh-afhængige) · ortotrope flader (træ, CLT) · jord og fundament (understøtninger er stive) · ikke-lineært materiale, krybning (k_def håndteres i eftervisningen) · dynamik og svingninger · brand. Står opgaven her, så beskriv den, og overlad den til den ansvarlige statiker.

## Bilaget
For hver model: formål · stien til `fem.yaml` og spec-sha fra `regn` · kommandoen præcis som udskrevet · de afgørende resultatlinjer (reaktioner, maks. M, V, N og δ med kombination; for flader σ_vM, n_v og udtræk med sted) · billederne (`model` og det afgørende diagram eller farvekort) · håndkontrollen med `statik.py` og afvigelsen i %.
