# VVS – principdiagram

Et principdiagram viser, **hvordan installationen hænger sammen**: hvad der forsyner hvad, i hvilken rækkefølge komponenterne sidder, og hvor sikkerhedsudstyret er. Det er ikke målfast og viser ikke rørføringen i plan. Det er det første, en VVS'er, en kontrollant eller en ny ejer skal se for at forstå huset.

Eksempel: `assets/schematic-example-house.svg` er eksempelhusets installation (BIM-eksemplet `byg-bim/skills/bim-knowledge/assets/example/model.yaml`). Den bruger alle symboler og konventioner nedenfor. Tag udgangspunkt i den, når du tegner et nyt diagram.

## Hvornår
- Ved projektering af ny eller ændret varme-, brugsvands- eller afløbsinstallation. Diagrammet viser løsningen, før detaljerne regnes.
- Ved kedel-, varmekilde- eller VVB-skift. Diagrammet er grundlaget for fejltilstandstabellen og funktionstjekket af sikkerhedskæden (se `checklists.md`).
- Ved fejlfinding i et ukendt anlæg. Tegn det, du har set, og markér resten som ikke verificeret.
- Ved aflevering, som en del af som-udført- og D&V-materialet (kerneprincip 8).

## Indhold
1. **Varme:** varmekilde, pumpe, ekspansion, sikkerhedsventil med ført afløb, manometer, fremløb og retur til hver varmeflade, ventiler (termostat-, afspærrings-, kontraventil), shunt eller blandesløjfe, VVB-spiral eller veksler.
2. **Brugsvand:** stik, hovedhane, vandmåler, tilbagestrømningssikring, VVB med sikkerhedsaggregat (afspærring, kontraventil og sikkerhedsventil på koldtvandstilgangen), cirkulation hvis den findes, og hvert tapsted.
3. **Afløb:** hvert afløbspunkt med dimension, faldstamme med udluftning over tag (eller undertryksventil), ledning under gulv med fald, rensebrønd og grænsen til offentlig kloak. Arbejde på kloakken er autoriseret kloakmesters (se `practice.md`, Grænseflader).
4. **Etager og rum** som vandrette bånd med kote. Rum med ID, så diagrammet kan slås op mod planen.

## Layout
- Etager som vandrette bånd, øverste etage øverst. Ude og terræn til højre eller nederst.
- Lodrette stigstrenge og vandrette fordelinger. Kun retvinklede knæk.
- Fremløb og retur følges ad med fremløb over eller til venstre for retur.
- Forbindelser markeres med en fyldt prik. En krydsning uden prik er ingen forbindelse.
- Komponenterne tegnes i den rækkefølge, de sidder i strømningsretningen.
- Signaturforklaring nederst til venstre og tegningshoved nederst til højre (titel, grundlag, "ikke målfast", udarbejdet af, status og revision med dato).

## Farver og stregtyper
Farverne er de samme som i BIM-modellens systemer, så diagram og 3D-model kan læses sammen.

| System | ID | Farve | Streg |
|---|---|---|---|
| Centralvarme fremløb | CV-F | `#D92626` rød | fuld, 3 px |
| Centralvarme retur | CV-R | `#8228A0` lilla | stiplet `9 5`, 3 px |
| Brugsvand koldt | BV-K | `#2673D9` blå | fuld, 2,5 px |
| Brugsvand varmt | BV-V | `#E6731A` orange | fuld, 2,5 px |
| Varmt brugsvand cirkulation | BV-C | `#E6731A` orange | stiplet `6 4`, 2 px |
| Spildevand | AF | `#735940` brun | fuld, 5 px for stamme og ledning, 3 px for afgrening |
| Regnvand | RV | `#1E9E8F` turkis | fuld, 4 px |

Skriv dimension og materiale ved hver streng, fx `BV-K Ø22 PEX` og `AF Ø110 PVC`.

## Mærkning
- Brug **de samme ID'er som i BIM-modellen og ejendomskortet** (KEDEL, VVB, RAD1, HV, VM, WC, GA, BRØND …). Har huset ingen model, så giv komponenterne korte ID'er og brug dem konsekvent i notat og diagram.
- ID med fed skrift og derefter en kort betegnelse, fx **RAD3** nord eller **EKSP** 18 l.
- Det, der kun er vist i princippet, ikke er set eller skal verificeres, skrives med rødt (`#b42318`) med "verificeres" eller "ikke vist". Fx kedelsikkerhed, der følger fyrets manual.
- Skriv "Principdiagram – ikke målfast" i tegningshovedet. Et principdiagram er aldrig en udførelsestegning.

## Symbolbibliotek (SVG)
Du kan ikke køre kode. Skriv derfor diagrammet direkte som SVG med Write. Kopiér denne `<defs>`-blok ind, og placér symbolerne med `<use href="#id" x=".." y=".."/>`. Alle symboler er centreret om (0,0), undtagen radiatoren, der har øverste venstre hjørne i (0,0) og måler 80 × 44. Drej et symbol til en lodret streng med `transform="rotate(90 x y)"`. Tegn rørene først og symbolerne bagefter, så de hvide symboler dækker røret.

```svg
<defs>
  <g id="ventil"><path d="M-7,-5 L7,5 L7,-5 L-7,5 Z" fill="#fff" stroke="#1d2330" stroke-width="1.2"/></g>
  <g id="trv"><use href="#ventil"/><path d="M0,0 V-11 M-4,-11 H4" fill="none" stroke="#1d2330" stroke-width="1.2"/><circle cy="-14" r="3" fill="#fff" stroke="#1d2330" stroke-width="1.2"/></g>
  <g id="kontraventil"><path d="M-7,-5 L5,0 L-7,5 Z" fill="#1d2330"/><path d="M6,-6 V6" stroke="#1d2330" stroke-width="1.6"/></g>
  <g id="sv"><path d="M-9,-5 L0,0 L-9,5 Z M-5,9 L0,0 L5,9 Z" fill="#fff" stroke="#1d2330" stroke-width="1.2"/><path d="M0,0 V-4 l4,-2 l-8,-3 l8,-3 l-8,-3 l4,-2 V-20" fill="none" stroke="#1d2330" stroke-width="1.2"/></g>
  <g id="pumpe"><circle r="10" fill="#fff" stroke="#1d2330" stroke-width="1.4"/><path d="M-5,-8 L9,0 L-5,8" fill="none" stroke="#1d2330" stroke-width="1.4"/></g>
  <g id="manometer"><circle r="7" fill="#fff" stroke="#1d2330" stroke-width="1.2"/><path d="M0,0 L4,-4" stroke="#1d2330" stroke-width="1.2"/></g>
  <g id="vm"><circle r="10" fill="#fff" stroke="#1d2330" stroke-width="1.4"/><text y="4" text-anchor="middle" font-size="11" font-weight="700">M</text></g>
  <g id="eksp"><rect x="-14" y="-18" width="28" height="36" rx="12" fill="#fff" stroke="#1d2330" stroke-width="1.4"/><path d="M-14,0 H14" stroke="#1d2330" stroke-dasharray="3 2"/></g>
  <g id="rad"><rect width="80" height="44" fill="#fff" stroke="#1d2330" stroke-width="1.4"/><path d="M10,0V44M20,0V44M30,0V44M40,0V44M50,0V44M60,0V44M70,0V44" stroke="#1d2330" stroke-width=".6"/></g>
  <g id="ga"><rect x="-9" y="-9" width="18" height="18" fill="#fff" stroke="#1d2330" stroke-width="1.4"/><path d="M-9,-9 L9,9 M9,-9 L-9,9" stroke="#1d2330" stroke-width="1"/></g>
  <g id="broend"><circle r="22" fill="#fff" stroke="#1d2330" stroke-width="1.6"/><circle r="15" fill="none" stroke="#1d2330" stroke-width="1"/></g>
</defs>
```

| ID | Komponent | Bemærkning |
|---|---|---|
| `ventil` | Afspærringsventil | Også hovedhane |
| `trv` | Termostatventil | Sidder på radiatorens fremløb |
| `kontraventil` | Kontraventil | Spidsen peger i strømningsretningen |
| `sv` | Sikkerhedsventil | Tegn altid det førte afløb med (stiplet streg til GA eller tragt) |
| `pumpe` | Cirkulationspumpe | Trekanten peger i strømningsretningen |
| `manometer` | Manometer | |
| `vm` | Vandmåler | |
| `eksp` | Ekspansionsbeholder | Membranen er den stiplede linje |
| `rad` | Radiator | Fremløb til venstre foroven, retur til højre forneden |
| `ga` | Gulvafløb | |
| `broend` | Brønd | Rense- eller skelbrønd |

Komponenter uden symbol, fx kedel, VVB, varmepumpe, fordeler, WC og vaske, tegnes som enkle rektangler eller konturer med ID og betegnelse indeni eller ved siden af (se eksemplet). En varmespiral tegnes som zigzag i fremløbsfarven inde i beholderen.

SVG'en skal have hvid baggrund (`<rect width="100%" height="100%" fill="#fff"/>` som første element), `viewBox` og `<title>`. Brug systemskrift (`font-family="system-ui, Helvetica, Arial, sans-serif"`) og 11–13 px tekst, så den kan læses ved udskrift i A3.

## Tjekliste før aflevering
- [ ] Alle varmeflader, tapsteder og afløbspunkter fra planen og BIM-modellen er med. Tæl dem.
- [ ] Hver streng har system-ID, dimension og materiale.
- [ ] Sikkerhedsudstyret er vist på varme- og brugsvandsside: sikkerhedsventil med ført afløb, ekspansion, sikkerhedsaggregat ved VVB og tilbagestrømningssikring. For fastbrændselskedler skal varmedump og termisk afløbssikring også være med, eller være markeret med rødt som "efter fyrets manual – verificeres".
- [ ] Fremløb og retur er ikke byttet om. Følg vandet fra kilde til varmeflade og tilbage.
- [ ] Afløb har fald mod brønden, og stammen har udluftning.
- [ ] Grænsen til kloakmester og forsyning er markeret.
- [ ] Alt, der ikke er set eller verificeret, er markeret med rødt.
- [ ] ID'er stemmer med BIM-model, ejendomskort og notat.
- [ ] Filen er gyldig XML (alle tags lukket, `&` skrevet som `&amp;`).

## Lagring
Gem diagrammet i sagen som `attachments/plumbing/schematic-<emne>.svg` og henvis til det fra fagnotatet. Når det beskriver husets faste installation, gemmes det også under ejendommens `attachments/`, så det følger huset.
