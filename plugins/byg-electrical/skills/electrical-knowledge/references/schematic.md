# El – tavlediagram (enstregsdiagram)

Et tavlediagram viser, **hvordan tavlen er bygget op**: forsyning, stikledning, måler, hovedafbryder, overspændingsbeskyttelse, fejlstrømsafbrydere og hver gruppe med sikring, kurve, fase, kabel, tværsnit, RCD og hvad gruppen forsyner. Det er ikke målfast og viser ikke kabelføringen i plan. Det er det, en elinstallatør, en kontrollant eller en ny ejer skal se for at forstå tavlen. Gruppefortegnelsen i tavlen er en tabel; diagrammet er den samme information tegnet.

Eksempel: `assets/schematic-example-house.svg` er eksempelhusets tavle (BIM-eksemplet `byg-bim/skills/bim-knowledge/assets/example/model.yaml`). Den bruger alle symboler og konventioner nedenfor.

## Hvornår
- Ved projektering af ny tavle, tavleudskiftning eller nye grupper (køkken, elbillader, varmepumpe). Diagrammet viser løsningen sammen med gruppeskemaet fra `el.py panel`.
- Ved vurdering af en eksisterende tavle. Tegn det, du har set, og markér resten som ikke verificeret.
- Ved aflevering, som en del af som-udført-dokumentationen sammen med gruppefortegnelsen.

## Sådan laves det
- **Fra en BIM-model** (hvem der har Bash, fx hovedtråden eller bim-modeller):
  `bim.py panel <model.yaml> --out panel.json`, derefter `python3 scripts/diagram.py panel.json --out schematic-<emne>.svg --date ÅÅÅÅ-MM-DD`. Grupperne er modellens systemer med `under: <tavlens system>`; længderne måles langs kabelsegmenterne. Kør også `el.py panel panel.json` – diagrammet viser den samme kontrol og de samme fund.
- **Fra en tavlefil** skrevet med Write (format som `el.py template`, plus valgfrit `rcd`-liste, `tavle.udstyr`, `tavle.kabelskab` og `forsyner` pr. gruppe som i eksemplet): kør `diagram.py` på filen.
- **Uden Bash** (electrician-agenten kan kun køre `el.py`): skriv SVG'en direkte med Write ud fra symbolbiblioteket nedenfor og tabellen fra `el.py panel`. Ret aldrig tal i hånden – tag dem fra `el.py`-resultatet.

## Indhold
1. **Forsyning:** netselskabets kabelskab med stikledningssikringer (antal × A, gG), stikledningen (kabel, ledere × tværsnit, længde) og jordingssystem (TT/TN).
2. **Tavlen:** måler, hovedafbryder, overspændingsbeskyttelse (type) til jord, skinne.
3. **Fejlstrømsafbrydere:** ID, type (A, F, B, B-EV), mærkestrøm, IΔn i mA og poltal. Grupperne under hver RCD tegnes på RCD'ens egen skinne.
4. **Hver gruppe:** nummer, automatsikring med kurve og mærkestrøm, brydeevne (kA), fase(r), kabel (fx `NOIKLX 3G1,5`) og referenceinstallationsmetode, længde og spændingsfald fra `el.py`, RCD (ID, type, mA), betegnelse og hvad gruppen forsyner (antal lamper, stikkontakter, faste apparater).
5. **Kontrol:** én linje med Ik,min, Ik,max ved tavlen og faselast fra `el.py panel` og alle fund med alvor `advarsel` eller `vejledende`.

## Layout
- Forsyningen kommer oppefra til venstre; tavlen er en stiplet ramme; hovedskinnen er vandret.
- Hver RCD hænger lodret på hovedskinnen og har sin egen vandrette skinne med grupperne under sig. Grupperne står i nummerorden inden for hver RCD.
- Gruppens tekst står i en kolonne under tavlerammen, én kolonne pr. gruppe, i samme rækkefølge hver gang: nummer, fase, sikring, kabel, længde og ΔU, RCD, betegnelse, forsyner, status.
- Forbindelser markeres med en fyldt prik. Antal faseledere vises med skrå streger på lederen (1 eller 3).
- Signaturforklaring nederst til venstre og tegningshoved nederst til højre (titel, grundlag, "ikke målfast", udarbejdet af, status og revision med dato).

## Farver og mærkning
- Faser som mærker med lederfarverne: L1 brun `#7a4a1e`, L2 sort `#1d2330`, L3 grå `#8a8f98`. Fordel enfasede grupper, så faselasten bliver jævn.
- Status fra `el.py`: OK grøn `#1a7f37`, vejledende gul `#9a6700`, advarsel og alt ikke verificeret rødt (`#b42318`). En RCD af type AC eller en gruppe uden RCD skrives med rødt.
- Brug **de samme ID'er som i BIM-modellen og ejendomskortet** (TAVLE, HA, SPD, RCD1, Q1 …), og gruppenumre som i gruppefortegnelsen.
- Skriv "Ikke målfast · ikke til udførelse" i tegningshovedet.

## Symbolbibliotek (SVG)
Symbolerne følger EN 60617 i forenklet form og er centreret om (0,0) på en lodret leder. Tegn lederne først og symbolerne bagefter, så de hvide masker dækker lederen. Placér med `<use href="#id" x=".." y=".."/>`.

```svg
<defs>
  <g id="sikring"><rect x="-6" y="-13" width="12" height="26" fill="#fff" stroke="#1d2330" stroke-width="1.4"/><path d="M0,-13 V13" stroke="#1d2330" stroke-width="1.2"/></g>
  <g id="automat"><rect x="-12" y="-11" width="24" height="22" fill="#fff"/><path d="M0,11 L-10,-8 M-4,-15 L4,-7 M4,-15 L-4,-7" fill="none" stroke="#1d2330" stroke-width="1.5"/></g>
  <g id="rcd"><use href="#automat"/><ellipse cy="20" rx="11" ry="4.5" fill="none" stroke="#1d2330" stroke-width="1.3"/><path d="M-11,20 L-7,1" fill="none" stroke="#1d2330" stroke-width="1.1" stroke-dasharray="3 2"/></g>
  <g id="hovedafbryder"><rect x="-12" y="-11" width="24" height="22" fill="#fff"/><path d="M0,11 L-10,-8 M-5,-11 H5" fill="none" stroke="#1d2330" stroke-width="1.5"/><circle cy="-11" r="2.2" fill="#fff" stroke="#1d2330" stroke-width="1.2"/></g>
  <g id="maaler"><rect x="-22" y="-15" width="44" height="30" fill="#fff" stroke="#1d2330" stroke-width="1.4"/><text y="4.5" text-anchor="middle" font-size="12" font-weight="700">kWh</text></g>
  <g id="spd"><rect x="-8" y="-15" width="16" height="30" fill="#fff" stroke="#1d2330" stroke-width="1.4"/><path d="M-11,11 L8,-9 H12" fill="none" stroke="#1d2330" stroke-width="1.3"/></g>
  <g id="jord"><path d="M0,0 V8 M-11,8 H11 M-7,12.5 H7 M-3,17 H3" fill="none" stroke="#1d2330" stroke-width="1.5"/></g>
  <g id="udtag"><circle r="4" fill="#fff" stroke="#1d2330" stroke-width="1.4"/></g>
  <g id="leder"><path d="M-5,4 L5,-4" stroke="#1d2330" stroke-width="1.3"/></g>
</defs>
```

| ID | Komponent | Bemærkning |
|---|---|---|
| `sikring` | Smeltesikring | Stikledningssikring (gG) |
| `automat` | Automatsikring | Kurve og A ved siden af, fx **B13** |
| `rcd` | Fejlstrømsafbryder | Type og mA ved siden af |
| `hovedafbryder` | Hovedafbryder | |
| `maaler` | Elmåler | |
| `spd` | Overspændingsbeskyttelse | Tegnes til `jord` |
| `jord` | Jord | |
| `udtag` | Gruppeafgang | Under hver gruppe |
| `leder` | Én faseleder | Tre streger = trefaset |

SVG'en skal have hvid baggrund (første element), `viewBox` og `<title>`. Brug systemskrift (`font-family="system-ui, Helvetica, Arial, sans-serif"`) og 11–13 px tekst, så den kan læses ved udskrift i A3.

## Tjekliste før aflevering
- [ ] Alle grupper fra gruppefortegnelsen og BIM-modellen er med. Tæl dem.
- [ ] Hver gruppe har sikring med kurve, fase, kabel med tværsnit, RCD og hvad den forsyner.
- [ ] Tallene (længde, ΔU, Ik, faselast) er fra `el.py panel`, og fundene er vist.
- [ ] Hver RCD har type og mA. Elbillader har egen type B (type A/F kun, når laderen selv detekterer DC ≥ 6 mA), og en type B sidder ikke efter en type A/F, jf. `standards.md`.
- [ ] Trefasede grupper har tre ledere og 5G-kabel.
- [ ] Forsyning, hovedafbryder og SPD er vist; forsikring stemmer med netselskabets oplysning eller er markeret med rødt.
- [ ] Alt, der ikke er set eller verificeret, er markeret med rødt.
- [ ] ID'er stemmer med BIM-model, ejendomskort og notat.
- [ ] Filen er gyldig XML (alle tags lukket, `&` skrevet som `&amp;`).

## Lagring
Gem diagrammet i sagen som `attachments/electrical/schematic-<emne>.svg` og henvis til det fra fagnotatet. Når det beskriver husets faste installation, gemmes det også under ejendommens `attachments/`, så det følger huset.
