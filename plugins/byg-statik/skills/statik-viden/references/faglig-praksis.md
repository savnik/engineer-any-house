# Statiker – faglig praksis

Værdier markeret **(T)** er typiske branche- eller erfaringsværdier. Verificér mod norm, producent eller undersøgelse, før de bruges som krav. Alle beregnede værdier er **OVERSLAG**, til den ansvarlige statiker har eftervist dem.

## 1. Er væggen bærende? – screening
Ingen enkeltindikator er nok. Saml mindst tre, og åbn konstruktionen ved tvivl.

| Indikator | Taler for bærende | Taler imod |
|---|---|---|
| Bjælkelagets retning (fra loft og kælder, sømrækker i gulvbrædder, loftslem) | Bjælker ligger *på* væggen eller ender over den | Bjælker løber parallelt med væggen |
| Placering | Midt i huset, under kip eller midterrem, over væg eller drager i kælderen | Kun mellem to rum i samme bjælkefelt |
| Materiale og tykkelse | Muret ½ sten eller mere, gennemgående fra kælder til loft | Let væg (træskelet, gips, tynd letbeton) uden noget ovenpå |
| Tagkonstruktion | Hanebåndsspær med midterunderstøtning, åse, skunkvægge ved spærfod | Gitterspær med vederlag kun på ydervæggene (T: tjek spærtegning) |
| Gamle tegninger | Væggen vist med bjælkelag på eller med fundament | – |
| Stabilitet | Tværvæg i lang bygning, væg ved trappehul, gavlafstivning | – |

Konklusionen skrives som **sandsynlig / uafklaret / usandsynlig** med det, der skal åbnes eller måles for at afgøre det.

**Typiske husperioder (T – erfaring, varierer lokalt):**
- **Før ca. 1930:** murede ydervægge, ofte massive; træbjælkelag med indskudsler og lerindskud (tung egenlast); midtervæggen bærer ofte bjælkelaget.
- **1930–1960:** murede hulmure; træbjælkelag; mange mindre huse med bærende midtervæg og hanebåndsspær, der kræver understøtning.
- **1960–1980:** gitterspær med spænd mellem ydervæggene er almindelige; indvendige vægge bærer ofte ikke taget, men kan bære loftbjælker eller være stabiliserende; letbetonvægge.

## 2. Laster i boliger (overslag)
Normværdier (nyttelast, sne, vind, partialkoefficienter) står i `normgrundlag.md`. Egenlaster herunder er typiske værdier til overslag.

| Egenlast | Typisk karakteristisk værdi (T – producent eller opmåling) |
|---|---|
| Tagdækning inkl. lægter, pr. m² tagflade | Tagpap/stål ca. 0,15–0,25 · fibercement ca. 0,25 · betontagsten ca. 0,5–0,55 · tegl ca. 0,5–0,7 kN/m² |
| Solceller inkl. skinner | ca. 0,15–0,25 kN/m² + vind på fastgørelserne |
| Træetageadskillelse med indskud og ler (før 1930) | ca. 1,5–2,5 kN/m² – undersøg opbygningen |
| Moderne træbjælkelag med gips og trægulv | ca. 0,5–0,8 kN/m² |
| Flisebelagt vådrumsgulv på trædæk (afretning, membran, fliser) | ca. 0,8–1,5 kN/m² ekstra – afhænger af afretningens tykkelse |
| Murværk af tegl | ca. 18 kN/m³ |
| Letbeton | ca. 5–8 kN/m³ |
| Armeret beton | ca. 25 kN/m³ |

**Lastnedføring:** oplandet er halvdelen af spændet til hver side. Følg lasten tag → spær/ås → rem → væg/bjælke → søjle → fundament → jord, og summer i hvert led. Skriv lastopgørelsen som tabel i bilaget.

## 3. Typiske indgreb
### 3.1 Fjernelse af bærende væg / ny åbning
1. **Funktion:** bærer væggen lodret last, er den stabiliserende, og bærer den skorsten eller trappe?
2. **Princip:** bjælke under loftet (synlig, enklest) eller i bjælkelaget (skjult, kræver bjælkesko eller udveksling). Stål (HEB/IPE, lav byggehøjde) eller limtræ (let og nem at montere, men højere).
3. **Overslag** med `statik.py beam` – moment, forskydning, nedbøjning og reaktioner.
4. **Vederlag:** murpille eller søjle under hvert vederlag; kontakttryk (`statik.py pressure`) og pillens størrelse. Vederlagsplade, betonbjælke eller udstøbning under punktlasten. Vederlagslængden fastlægges af statikeren (T: ofte mindst 100–150 mm for stål på murværk).
5. **Lasten ned til jorden:** står vederlaget på et fundament – eller på et terrændæk eller strøgulv? En punktlast på et ufunderet gulv kræver nyt punktfundament.
6. **Midlertidig understøtning** og rækkefølge (afsnit 5).
7. **Brand:** skal bjælken have brandmodstand? Afklares efter BR18 kap. 5 (fx etageboliger og adskillelse mod garage) – brandrådgiver ved tvivl.
8. **Stabilitet:** fjernes en stabiliserende væg, skal anden afstivning eftervises (skive, ramme, indspændt søjle).

### 3.2 Tag og tagetage
- **Hanebånd og spærfod:** hanebåndene holder spærene sammen. Fjernes eller hæves de, skubber taget ydervæggene ud. Det kræver ny rygningsbjælke eller ås, eller en stålramme, efter statikerens projekt.
- **Gitterspær skæres aldrig** uden producentens eller statikerens projekt, og de kan ikke bære en tagetage uden forstærkning.
- **Kviste og ovenlys:** udveksling med dobbelte spær og bjælker; kvistens laster og snesække omkring den.
- **Tungere tagdækning** (fx fibercement → tegl): eftervis spær, lægter, remme og vederlag. Ældre tage har ofte ingen reserve.
- **Solceller:** ekstra egenlast og vind (sug og tryk) på fastgørelserne; vurder tagets reserve.

### 3.3 Etagedæk og bjælkelag
- **Nyt bad på træbjælkelag:** mere egenlast og krav til stivhed (fliser revner ved nedbøjning). Tjek spænd, dimension, afstand og vederlag; forstærk med ekstra bjælker, sidebjælker eller limtræ.
- **Hængende bjælkelag:** mål nedbøjningen og find årsagen (overbelastning, råd ved vederlag, fjernet væg, krybning). Råd ved bjælkeender i fugtige ydervægge er typisk.
- **Huller i bjælker** til rør og kanaler: kun efter statikerens anvisning og nær neutralaksen (T); en udveksling er ofte bedre end gennembrydning.
- **Svingninger:** lette trædæk med store spænd føles "levende" – stivheden og bjælkeafstanden afgør det.

### 3.4 Fundering og kælder
- **Eksisterende fundamenter** i ældre huse er ofte uarmerede, smalle og kan være lavt funderede. Undersøg ved prøvegravning (dybde, bredde, materiale, jord).
- **Udgravning ved fundament** (dræn, kloak, kældersænkning): grav aldrig under fundamentets underkant på længere strækninger uden projekt. Udfør etapevis og underfundér efter statikerens eller geoteknikerens projekt.
- **Tilbygning:** frostfri fundering (`normgrundlag.md`), jordbundsundersøgelse ved tvivl om bæredygtig jord og en sætningsfuge mod det eksisterende hus – eller sammenbygning, hvor forskellige sætninger er vurderet.
- **Smuldrende beton eller sokkel:** afgør, om delen er bærende (fundament eller sokkel under ydervæg) eller kun en beklædning. Vurder nedbrydningens dybde, armering og korrosion. Udskift etapevis med understøtning (sammen med murer). Diagnose, prøver og reparation: `betonskader.md`.

## 4. Skader: revner og sætninger
| Mønster | Sandsynlig årsag | Næste skridt |
|---|---|---|
| Skrå revner fra hjørner af åbninger, bredest i den ene ende | Differenssætning | Revnemålere og nivellement over en sæson; geotekniker ved aktive sætninger |
| Vandret revne under tagfod, ydervæg skubbet ud | Udskub fra taget (manglende eller fjernede hanebånd, rådne spærfødder) | Mål lod og revnebredde; statiker – trækforbindelser |
| Lodrette revner i lange facader og ved hjørner | Svind og temperatur | Overvåg; dilatationsfuge eller armering (murer) |
| Revne over åbning, nedbøjet overligger | Overbelastet eller korroderet overligger | Udskiftning efter projekt |
| Knuste sten under bjælkeender | Overbelastet vederlag | Statiker – vederlagsplade eller udstøbning |
| Revner efter tørre somre eller nær store træer | Svind i lerjord | Geotekniker; træer og dræn |
| Revner nær nyt byggearbejde eller udgravning | Udgravning, vibrationer, grundvandssænkning | Dokumentér; stop arbejdet, hvis revnerne udvikler sig |

**Revneovervågning (T):** revnemålere aflæst med fast interval; nivellement af sokkel og gulve; fotos med dato og målestok. En aktiv revne ændrer bredde over tid eller med årstiden.

## 5. Midlertidig understøtning (princip)
- Justerbare stålstempler med åg eller rem under bjælkelaget på begge sider af væggen – eller nåle gennem væggen, når murværket ovenover skal bæres.
- Stemplerne skal stå på et underlag, der kan bære dem (ikke et svagt strøgulv eller et terrændæk uden lastfordeling), om nødvendigt helt ned til fundament.
- Rækkefølge: understøt → fjern → montér ny bjælke → udstøb eller udkil vederlag → hærdning → fjern understøtning.
- Antal og placering af stempler fastlægges efter lasterne af statikeren eller den udførende.

## 6. Review af statisk dokumentation fra en rådgiver
Dokumentationen bør:
- have et **konstruktionsgrundlag** (normer og udgaver, konsekvens- og konstruktionsklasse, laster, materialer, forudsætninger om de eksisterende konstruktioner)
- følge lasten til jord og eftervise **vederlag, punktlaster og fundament**, ikke kun selve bjælken
- behandle **stabiliteten**, når vægge eller hanebånd fjernes
- angive **nedbøjningskrav**, der passer til de efterfølgende overflader
- have **detaljer** (vederlag, samlinger, beslag, brandbeskyttelse) og **udførelsesforudsætninger** (midlertidig understøtning, rækkefølge)
- bygge på **undersøgte** eksisterende forhold eller tydeligt markerede antagelser, der skal verificeres på stedet
- have en **kontrolplan** for udførelsen (hvem kontrollerer hvad og hvornår)

## 7. Ingeniørydelsen – hvad bygherren bør bestille (T – typisk omfang)
Besigtigelse · konstruktionsgrundlag · beregninger · tegning eller skitse med detaljer · udførelsesbeskrivelse med midlertidig understøtning · statisk dokumentation til kommunen, når den kræves · kontrol af det udførte ved hold points. Prisen afhænger især af, om de eksisterende forhold er undersøgt på forhånd.

## Grænseflader set fra statiker
| Fag | Statiker forventer | Statiker leverer |
|---|---|---|
| Murer | Oplysninger om murværk, mørtel og revner; udførelse af vederlag, udstøbning og piller | Vederlagsdetaljer, krav til piller og murværk under punktlast, rækkefølge |
| Tømrer | Opmåling af spær, bjælker, remme, vederlag og råd | Dimensioner, samlinger og beslag, krav til styrkeklasse og træfugt |
| VVS, ventilation, el | Føringsveje gennem bjælker, vægge og dæk før projekteringen | Tilladte huller og riller, udvekslinger |
| Geotekniker | Jordbundsforhold, bæreevne, grundvand | Laster på fundamenterne, krav til fundering |
| Brandrådgiver | Brandkrav til bærende konstruktioner | Hvilke konstruktioner der skal beskyttes |
| BIM-modellør | Modellens geometri som kilde | Godkendt løsning til modellen (bjælke, søjle, vederlag) |
| Smed / entreprenør | Udførelse efter projekt; dokumentation for stålkvalitet | Profiler, kvalitet, detaljer, overfladebehandling |
