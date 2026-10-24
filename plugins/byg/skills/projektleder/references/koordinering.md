# Koordinering af fag

## Fagvalg efter opgavetype
| Opgave | Primære fag | Ofte også | Fag uden agent |
|---|---|---|---|
| Badeværelse | vvs, murer (vådrum/fliser), el, ventilation | tømrer (træunderlag, vægge), maler (fugtig zone, loft) | kloakmester (afløb i jord) |
| Køkken | vvs, el, tømrer | ventilation (emhætte, erstatningsluft), maler, murer og statik (vægfjernelse), arkitekt (ny planløsning) | snedker, ansvarlig statiker |
| Kælderfugt | murer, ventilation | vvs (lækager, dræn), anlaeg (terrænfald, nedløb, regnvand, omfangsdræn), maler, tømrer (gulve) | kloakmester (dræn), geotekniker |
| Efterisolering af loft/tag | tømrer, ventilation | el (spots, kabler), vvs (rør i tagrum) | tagdækker |
| Facade og ydervægge | murer, maler | tømrer (vinduer, inddækning), ventilation, arkitekt (nye åbninger, udtryk, lokalplan og bevaring) | blikkenslager |
| Vinduer og døre | tømrer, murer | maler, ventilation (friskluft) | glarmester |
| Varmepumpe og varmeanlæg | vvs, el | tømrer/murer (gennemføringer, fundament), ventilation (luft-luft) | energikonsulent |
| Tilbygning | alle (arkitekt først: myndighed og disposition) | anlaeg (terræn, regnvand og udearealer omkring tilbygningen) | ansvarlig arkitekt, ansvarlig statiker, geotekniker, kloakmester, tagdækker, landinspektør |
| Vægfjernelse, tagetage, kvist | statik, tømrer, murer, arkitekt (tagetage, kvist: etageareal og tilladelse) | el og vvs (føringer), maler, ventilation | ansvarlig arkitekt, ansvarlig statiker, smed |
| Ny planløsning og ombygning | arkitekt, statik | tømrer, murer, el, vvs, ventilation, bim | ansvarlig arkitekt |
| Revner og sætninger | statik, murer | vvs (utætte afløb), anlaeg (træer og rødder, terrænfald), tømrer | geotekniker, kloakmester |
| Skimmel og indeklima | ventilation, murer, tømrer | maler, vvs (lækager) | skimmelsvampeekspert |
| Have, terrasse og regnvand | anlaeg | murer (sokkel og fugt), statik (støttemur, udgravning ved fundament), vvs (tagnedløb), tømrer (hævet eller overdækket terrasse), arkitekt (afstand til skel, lokalplan), el (havebelysning) | kloakmester (tilslutning og afkobling), landinspektør (skel) |
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
Ejendomskort: <sti> – læs "Fælles", afsnittet for dit fag og "Problemstoffer og kendte skader"; citér fakta med ID
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
- Konflikter mellem fag afgøres efter **domæneforrang** (næste afsnit), ikke ved at mægle et kompromis.
- Koordineringsbeslutninger (fx hvem der leverer fald, rækkefølge, manchetfordeling) logføres og sendes eksplicit til **alle** berørte fag samtidig – i nye fagkald og i returer – ikke kun til det fag, der udløste dem.
- Ændres en grundforudsætning undervejs (fx rummets placering), så suspendér de bindende detaljer, der bygger på den gamle forudsætning, i beslutningsloggen, og revidér alle berørte fagnotater under nye leverance-ID'er.

## Konflikter mellem fag – domæneforrang
Når to fagnotater er uenige, er den typiske fejl at mægle: at sammensætte en mellemløsning af begge forslag eller tage gennemsnittet af to tal. Hold af sprogmodeller gør netop det og ender under deres bedste ekspert (målt op til 41 % tab, Apple/Stanford 2026). Derfor:
1. **Find domænet.** Hvilket spørgsmål handler konflikten om, og hvilket fag ejer det? Brug ejeren i `graenseflader.md`, ellers tabellen nedenfor.
2. **Ejerfaget har forrang i sit domæne.** Det andet fag tilpasser sig og får beslutningen i sin næste retur eller sit næste fagkald.
3. **Ingen mellemløsning.** Sammensæt aldrig en løsning af dele fra begge forslag, og tag aldrig gennemsnit eller "et sted midt imellem" af dimensioner, mål, luftmængder, budgetter eller tider. Vælg ét fags løsning som helhed med en begrundelse på én linje.
4. **Uklart eller nyt argument?** Send det andet fags indvending til ejerfaget i ét fagkald. Spørg ikke begge fag om det samme, og lad dem ikke debattere.
5. **Brugerens beslutning,** når konflikten står mellem to legitime domæner (fx funktion i ét fag mod økonomi eller æstetik i et andet), eller ejerfaget selv markerer sit svar som usikkert (T). Præsentér da ejerfagets løsning og det andet fags løsning hver for sig med konsekvenser, ikke en blanding.
6. **Sikkerhed og lovkrav går forud** for funktion, æstetik og pris (grundregel 5). En løsning under et lovkrav er aldrig et valg.
7. **Log** afgørelsen i `beslutningslog.md` som "Domæneforrang: <fag> (<domæne>)".

| Spørgsmålet handler om | Forrang |
|---|---|
| Bærende konstruktion: hvad er bærende, laster, bjælker og vederlag, åbninger, fundering, midlertidig understøtning | statik (og ansvarlig statiker for dokumentationen) |
| Elektrisk sikkerhed: beskyttelse, kabler og dimensionering, el-materiel i vådrumszoner | el |
| Vand, afløb og fald, tæthed, varmeanlæggets sikkerhed (sikkerhedsventil, ekspansion, dump) | vvs |
| Luftskifte og luftmængder, trykforhold, erstatningsluft, aftræk, fugtbelastning i luften | ventilation |
| Vådrumsmembran og fliser, murværk, puds, fugt i murværk og kælder | murer |
| Klimaskærm i træ: undertag, dampspærre, isolering; træværk inden for statikerens rammer | toemrer |
| Underlag og overfladebehandling, bly og PCB i maling | maler |
| Mål og geometri i modellen (ikke fagkrav) | bim |
| Rækkefølge, tid, budgetsum, ejerskab af snitflader | projektleder |

## Budget – budget.md
Projektlederen ejer den samlede budgetsum fra første fagnotat. **Fag uden agent** (screening og analyser, affaldsanmeldelse, kloakmester, ansvarlig statiker, varmetabsberegning, skorstensfejer, servicefirma, midlertidige løsninger) prissættes af PL med skøn [T] ved G1, så R-rammen vurderes på et komplet tal. Fagene angiver kun eget skøn inkl. moms, med grundydelse og optioner adskilt; de vurderer ikke den samlede ramme.
- Tjek altid, hvem der leverer selve produkterne (sanitet, armaturer, glasvæg, dør, vindue) og fælles poster (container/affald, faldsikring og stillads, tagdækker, PSS, screening, midlertidige løsninger). De glemmes let i fagenes skøn.
- Bufferen (typisk 10–15 %) lægges oveni grundydelsen.
- Afviger det sandsynlige niveau fra rammen, forelægges det bygherren som beslutningspunkt (hæv rammen eller vælg besparelser), før tilbud indhentes.

| Post | Lav | Høj | Kilde |
|---|---:|---:|---|

## Grænsefladeregister – graenseflader.md (laves ved G1, lukkes ved G2)
| ID | Snitflade | Fag A | Fag B | **Ejer** (leverer og dokumenterer) | Hvad | Fase/hvornår | Status (åben/afgjort/lukket) | Beslutning (link til beslutningslog) |
|---|---|---|---|---|---|---|---|---|
- Én ejer pr. snitflade. Komponenter på tværs af fag (fx sikkerhedskomponent, der skal el-tilsluttes) står med **leverandør, montør og tilslutter** hver for sig.
- ID'et (`G-01`, `G-02` …) står i første kolonne, så fagenes forslag kan flettes på rækkeniveau. Fagene skriver ikke selv i registret; nye eller ændrede snitflader kommer som forslag (`forslag/<fag-id>-<nr>__graenseflader.md`) og flettes ind, når leverancen godkendes (skill `kvalitetskontrol`, afsnit 8). Det samme gælder `risici.md` (`R-01` …) og `kontrolplan.md` (hold point-navnet som ID).
- Fagene må ikke selv ændre en ejer; fletningen afviser et forslag, der gør det. Afvigelser meldes til PL, som afgør dem og opdaterer registret, før næste fagkald eller retur.
- Omfatter også **fag uden agent** (screening, kloakmester, servicefirma, skorstensfejer, ansvarlig statiker).

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
Afsæt tid til kontrol-loopet (op til 2 forsøg) og til tørretider efter produktdatablade.

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
