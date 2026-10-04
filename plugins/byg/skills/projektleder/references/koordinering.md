# Koordinering af fag

## Fagvalg efter opgavetype
| Opgave | Primære fag | Ofte også | Fag uden agent |
|---|---|---|---|
| Badeværelse | vvs, murer (vådrum/fliser), el, ventilation | tømrer (træunderlag, vægge), maler (fugtig zone, loft) | kloakmester (afløb i jord) |
| Køkken | vvs, el, tømrer | ventilation (emhætte, erstatningsluft), maler, murer (vægfjernelse) | snedker, statiker |
| Kælderfugt | murer, ventilation | vvs (lækager, dræn), maler, tømrer (gulve) | kloakmester (dræn), geotekniker |
| Efterisolering af loft/tag | tømrer, ventilation | el (spots, kabler), vvs (rør i tagrum) | tagdækker |
| Facade og ydervægge | murer, maler | tømrer (vinduer, inddækning), ventilation | blikkenslager |
| Vinduer og døre | tømrer, murer | maler, ventilation (friskluft) | glarmester |
| Varmepumpe og varmeanlæg | vvs, el | tømrer/murer (gennemføringer, fundament), ventilation (luft-luft) | energikonsulent |
| Tilbygning | alle | – | statiker, kloakmester, tagdækker, landinspektør |
| Skimmel og indeklima | ventilation, murer, tømrer | maler, vvs (lækager) | skimmelsvampeekspert |
| Elbillader og solceller | el | tømrer/tagdækker (tag), maler | netselskab |

## Fagforespørgsel (skabelon)
```
LEVERANCE: <sag-id>/<fag-id>/<nr>
FASE: <1|2> · KONTROLNIVEAU: <let|fuld> (efter opgavens risiko, se faser-og-gates.md)
Sagsmappe: <sti>
Grænsefladeregister: <sagsmappe>/graenseflader.md (fra G1; i fase 1: "udfyldes af PL efter fase 1")
Hold point-præfiks: HP-<FAG>-n (HP1–HPn projektfælles)
Opgave: <præcist spørgsmål eller leverance>
Kontekst: kort resumé: <2–3 linjer>
Læs: <de filer og afsnit, opgaven bygger på, fx "projektgrundlag.md afsn. 3; vvs-r2.md afsn. 4–5; beslutningslog M3–M4">
Afgrænsning: <hvad er ikke med>
Grænseflader, der skal belyses: <fag + emne>
Relevante lokale erfaringer: <fra videnbanken, eller "ingen">
Leverance: fagnotat til <sagsmappe>/fagnotater/<fag-id>.md efter den fælles protokol
Omfang: <fase 1: beslutningsnotat (højst ca. 2 sider) | fase 2: fagnotat uden tilbudsgrundlag>
Projektets rammer: <krav- og begrænsningsliste fra projektgrundlag og beslutningslog, fx ét firma pr. dag>
Enkelhed: den enkleste sikre standardløsning. Højst ét alternativ. Ekstra komponenter og scenarier kun med begrundelse på én linje.
```
Ændrer opgaven en varmekilde, dens sikkerhedsudstyr eller hydraulikken omkring den, så skriv i opgaven: "Lav en fejltilstandstabel (normal drift, overtemperatur/dump, strømsvigt, fastlåst ventil, lækage) for alle berørte kredse, før du anbefaler." Spørg ikke kun, om en komponent kan udgå.

## Rækkefølge og parallelitet
- Kald uafhængige fag parallelt. Kald afhængige fag i rækkefølge, og giv det næste fag stien til det forriges godkendte notat.
- Typiske afhængigheder: konstruktion og fugt (murer/tømrer) → installationer (vvs/el/ventilation) → overflader (maler).
- Konflikter mellem fag: beskriv konflikten neutralt, spørg de berørte fag med samme spørgsmål, og præsentér brugeren for muligheder med konsekvenser, hvis fagene ikke kan løse den.
- Koordineringsbeslutninger (fx hvem der leverer fald, rækkefølge, manchetfordeling) logføres og sendes eksplicit til **alle** berørte fag samtidig – i nye fagkald og i returer – ikke kun til det fag, der udløste dem.
- Ændres en grundforudsætning undervejs (fx rummets placering), så suspendér de bindende detaljer, der bygger på den gamle forudsætning, i beslutningsloggen, og revidér alle berørte fagnotater under nye leverance-ID'er.

## Budget – budget.md
Projektlederen ejer den samlede budgetsum fra første fagnotat. **Fag uden agent** (screening og analyser, affaldsanmeldelse, kloakmester, statiker, varmetabsberegning, skorstensfejer, servicefirma, midlertidige løsninger) prissættes af PL med skøn [T] ved G1, så R-rammen vurderes på et komplet tal. Fagene angiver kun eget skøn inkl. moms, med grundydelse og optioner adskilt; de vurderer ikke den samlede ramme.
- Tjek altid, hvem der leverer selve produkterne (sanitet, armaturer, glasvæg, dør, vindue) og fælles poster (container/affald, faldsikring og stillads, tagdækker, PSS, screening, midlertidige løsninger). De glemmes let i fagenes skøn.
- Bufferen (typisk 10–15 %) lægges oveni grundydelsen.
- Afviger det sandsynlige niveau fra rammen, forelægges det bygherren som beslutningspunkt (hæv rammen eller vælg besparelser), før tilbud indhentes.

| Post | Lav | Høj | Kilde |
|---|---:|---:|---|

## Grænsefladeregister – graenseflader.md (laves ved G1, lukkes ved G2)
| # | Snitflade | Fag A | Fag B | **Ejer** (leverer og dokumenterer) | Hvad | Fase/hvornår | Status (åben/afgjort/lukket) | Beslutning (link til beslutningslog) |
|---|---|---|---|---|---|---|---|---|
- Én ejer pr. snitflade. Komponenter på tværs af fag (fx sikkerhedskomponent, der skal el-tilsluttes) står med **leverandør, montør og tilslutter** hver for sig.
- Fagene må ikke selv ændre en ejer. Afvigelser meldes til PL, som afgør dem og opdaterer registret, før næste fagkald eller retur.
- Omfatter også **fag uden agent** (screening, kloakmester, servicefirma, skorstensfejer, statiker).

## Fagsekvenser (typiske – tilpasses sagen)
**Badeværelse:** screening (asbest/PCB/bly) → nedrivning og affald → vvs-råføring (afløb, vand; tæthedsprøvning) + el-råinstallation → vægge/underlag (tømrer/murer) → fald og afretning → membran (hold point: kontrol og tørretid) → fliser → vvs- og el-montering → ventilation → maler (fugtig zone/loft) → funktions- og slutkontroller.
- Screeningen omfatter alle flader, arbejdet berører: også loft/skråvæg, tagdækning ved afkast og ovenlys, eksisterende afkast og lofter/vægge på kabel- og rørveje.
- Standardgrænseflade for manchetter ved gennemføringer: tømrer leverer og monterer dampspærremanchet, murer vådrumssystemets manchet (også ved gulvafløb, wc-afløb og forvæg), tagdækker undertagsmanchet og inddækning; installationsfaget leverer selve rør, kanal eller kabel.
- Bad i tagetage/under skråvæg: afklar zoneskel på skråvæggen, ét tæt lag i vådzonen, skunk varm/kold og ovenlysvinduets egnethed ved besigtigelse før tilbud; tagarbejde kræver faldsikring og typisk PSS.

**Køkken:** afklaring af vægge og statik → vvs- og el-råinstallation → ventilation (emhætte, erstatningsluft) → vægge og lofter → gulv → montage → vvs- og el-tilslutning → maler.

**Kælderfugt:** registrering og målinger → årsag (murer, ventilation, vvs) → udvendige tiltag (terræn, tagrender, dræn) → indvendige tiltag → udtørring og ny måling → overflader.

**Efterisolering af loft:** undersøgelse af tagrum → tætning af den varme side (el, vvs, tømrer) → tagfod og ventilation → isolering → kontrol efter første vinter.

**Tilbygning:** myndighed og statik → fundament og kloak → råhus og tag → lukning (vinduer) → installationer → indvendig lukning → overflader → færdigmelding.

**Vinduer:** opmåling og valg → screening (PCB i fuger, bly i maling) → montage (tømrer) → murer (lysninger, sålbænke) → ventilation (friskluft) → maler.

## Tidsplan – tidsplan.md (først i fase 3, efter design freeze)
| Uge/dato | Aktivitet | Fag | Afhænger af | Hold point / kontrol | Tørretid/ventetid |
|---|---|---|---|---|---|
Afsæt tid til kontrol-loopet (op til 3 forsøg) og til tørretider efter produktdatablade.

## Risikoregister – risici.md
| Risiko | Sandsynlighed (L/M/H) | Konsekvens (L/M/H) | Tiltag | Ejer | Status |
|---|---|---|---|---|---|

## Kontrolplan – kontrolplan.md
| Hold point / kontrol | Fag | Hvornår | Krav/kilde | Dokumentation | Ansvarlig | Status |
|---|---|---|---|---|---|---|
Tag altid lovpligtige kontroller med, når de er relevante: tæthedsprøvning af vand og afløb, el-verifikation og KLS-slutkontrol, funktionsafprøvning af ventilation, statisk dokumentation, tæthedsprøvning af bygning ved nybyggeri, affaldsanmeldelse.

## Beslutningslog – beslutningslog.md
| Dato | Beslutning | Muligheder | Begrundelse | Besluttet af | Konsekvens |
|---|---|---|---|---|---|
