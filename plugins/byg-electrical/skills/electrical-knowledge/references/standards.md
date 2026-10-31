# El – normgrundlag

Sidst gennemgået: 2026-10-31. BR18 gælder i den version, der er aktuel fra 1/1-2026 (ældre versioner ligger under "Historisk" på bygningsreglementet.dk). §-numre kan være læst i en ældre version – tjek den aktuelle, før du citerer. **V** = verificeret (kilde), **T** = skal verificeres.

## Kilder
| Kilde | Emne og brug | Status |
|---|---|---|
| Elsikkerhedsloven (LBK nr. 57/2026) | Rammelov for elektriske anlæg, installationer og udstyr; ejerens ansvar (§ 10, se nedenfor) | V 2026-10-18 (retsinformation.dk/eli/lta/2026/57) |
| Installationsbekendtgørelsen, BEK nr. 1082 af 12/07/2016 (ændret ved BEK 639/2017) | Gør DS/HD 60364 gældende; krav til udførelse og dokumentation. Centrale §§ i tabellen nedenfor | V 2026-10-18 (retsinformation.dk/eli/lta/2016/1082) |
| DS/HD 60364-serien | Lavspændingsinstallationer | V (sik.dk) |
| DS/HD 60364-4-41 | Beskyttelse mod elektrisk stød, supplerende beskyttelse med RCD | T (afsnit) |
| DS/HD 60364-5-52 / -5-54 | Kabelinstallationer (strømværdier anneks B, se `calc-tools.md`) / jording og beskyttelsesledere | Tabelværdier V sekundær 2026-10-31; tekst T |
| DS/HD 60364-6 | Verifikation: eftersyn, afprøvning, rapportering | V (sik.dk-vejledninger om eftersyn, afprøvning og rapportering) |
| DS/HD 60364-7-701:2024 (= IEC 60364-7-701:2019) | Rum med badekar eller brusebad, se "Badeværelse – områder" | V 2026-10-31 (sik.dk-vejledning og huseftersynshåndbog) |
| DS/HD 60364-7-712 | Solcelleanlæg | T |
| DS/HD 60364-7-722 | Forsyning af elbiler; RCD-valg V via sik.dk, se "RCD" | T (pkt.-tekst) |
| Sikkerhedsstyrelsen – danske tolkninger | Udligningsforbindelser, potentialudligning i badeværelser, dokumentation ved afvigelse fra standarder | V (emner findes på sik.dk) |
| Sikkerhedsstyrelsen – solceller | Autorisation og tilslutning, se "Solceller" nedenfor; plugin-solceller med stikprop kan udgøre en risiko | V 2026-10-18 (sik.dk) |
| Autorisationsloven | Elinstallationsarbejde kræver autoriseret virksomhed – undtagen det, privatpersoner udtrykkeligt må | V |
| Fællesregulativet 2026 (Green Power Denmark, gyldig fra 1/1-2026) | Netselskabernes fælles tilslutningsbestemmelser: tilmelding og kortslutningsniveau, se nedenfor; lokale tillæg kan findes | V 2026-10-18 (elnet.dk/files/media/document/Fællesregulativet_2026.pdf) |
| Elinstallationsrapport ved ejerskifte | Del af huseftersynsordningen | T |

## Gør-det-selv (privatperson, strømmen afbrudt) – Sikkerhedsstyrelsens liste via Bolius (2026-09); stikkontakter og afbrydere V 2026-10-18 mod BEK nr. 560/2017 § 1 (retsinformation.dk/eli/lta/2017/560)
**Må selv:**
- Udskifte eller montere stikpropper, ledningsafbrydere, apparatkontakter og transportable stikkontakter (forlængerledninger, stikdåser).
- Reparere elapparater, fx udskifte tilledning eller fatning.
- Udskifte afbrydere op til 250 V, hvor der højst kræves IP20 (§ 1, nr. 1).
- Udskifte stikkontakter op til 250 V, hvor der højst kræves IP20 – **kun hvis installationen er beskyttet af HFI- eller HPFI-afbryder** (§ 1, nr. 2). Betingelsen gælder alle stikkontakter, også uden jord; sekundære kilder, der kun knytter den til stikkontakter med jord, er upræcise. Uden HFI/HPFI: installatør, og RCD anbefales.
- Erstatte almindelige afbrydere med lysdæmpere, tidsafbrydere o.l.
- Sætte lamper op og tage dem ned; lavvolt-lampesæt leveret komplet med transformer, lamper, ledninger og vejledning.
- Ændre og reparere svagstrømsstyring, der styrer stærkstrømsfunktioner (fx omprogrammering).

**Må ikke selv (kræver autoriseret el-installatør):**
- Nye installationer og udvidelser – fx en ny stikkontakt ved siden af en eksisterende.
- Arbejde i tavlen.
- Materiel over 250 V i den faste installation.
- Udendørs afbrydere, stikkontakter og lamper i den faste installation.
- Lavvoltbelysning, hvor transformer, lamper og ledninger er købt hver for sig.
- Tilslutning af solcelleanlæg.

Det, en privatperson må lave, ændrer ikke installationen grundlæggende – den skal fortsat opfylde reglerne fra etableringstidspunktet. Slå altid sik.dk op ved tvivl.

## Installationsbekendtgørelsen (BEK 1082/2016) – centrale krav
Alle rækker V 2026-10-18 mod retsinformation.dk/eli/lta/2016/1082, medmindre andet står.

| § | Krav | Faldgrube |
|---|---|---|
| 25 | Installationen skal følge reglerne på udførelsestidspunktet. Ved senere ændringer, **herunder flytning af tavler**, gælder reglerne på ændringstidspunktet for de dele, der ændres | "Det var lovligt dengang" gælder kun det, der ikke røres |
| 35 | Nye installationer: stikkontakter ≤ 20 A og andre tilslutningssteder med overstrømsbeskyttelse ≤ 32 A skal have beskyttelse med RCD ≤ 30 mA. Undtagelse for enkelte brugsgenstande af driftstekniske grunde (anden automatisk afbrydelse + mærkning) | "RCD efter standarden" er ikke nok – skriv ≤ 30 mA |
| 61 | Eksisterende installationer: stikkontakter ≤ 16 A og tilslutningssteder ≤ 20 A skal også have RCD ≤ 30 mA | Gælder uanset installationens alder; en fejlspændingsafbryder (FSA) er ikke en RCD |
| 53 | RCD type AC må ikke bruges som fejlbeskyttelse i boliger | Tjek typen på eksisterende RCD/HFI ved ændring |
| 45 | Kortslutningsbeskyttelse foran stikkontakter: 10 A og 13 A stikkontakter → højst 13 A; 16 A stikkontakter → højst 16 A. Gælder uanset kablets strømværdi | 16 A eller større gruppe til almindelige 10/13 A-stikkontakter er ulovlig |
| 55 | Beskyttelsesudstyr skal sidde i den bolig, det hører til; højst 2,2 m over gulv; under 1 m over gulv kun i aflåseligt skab | Gælder også ved flytning af tavle |
| 57 | Stikkontakter (250 V) pr. rum: mindst én pr. påbegyndt 4 m² gulv, dog højst krav om 10. **Køkkenregion: mindst 3 stikkontakter, hvor brugsgenstande bruges, fordelt på mindst 2 grupper.** Kogeniche: mindst 1. Bad og wc: mindst 1, medmindre rummet er for lille | Se "Ændring og udvidelse" for, hvornår kravet udløses i eksisterende boliger |
| 62 | Ved udvidelse/ændring skal eksisterende materiel, der får ekstra belastning (stikledning, tavle, kabler), være tilstrækkeligt; jording og udligning skal være tilstrækkelig | Ny lader/varmepumpe/sol → kontrollér det eksisterende |
| 63 | Udvidelse/ændring med **højst 2 tilslutningssteder**: beskyttelsesleder må udelades, hvis den mangler i forvejen, når det nye får RCD ≤ 30 mA | Flere end 2 → beskyttelsesleder skal fremføres |
| 64 | Stikkontakter med jord, som er omfattet af en udvidelse eller ændring, skal tilsluttes en **virksom beskyttelsesleder** | Jordet stikkontakt med tom jordklemme bag RCD er ikke lovlig |
| 68 | Eksisterende tavle kan serviceres, ændres og udvides inden for den eksisterende kapsling efter reglerne fra dens installation. Udvidelse uden for kapslingen = ny tavle (nugældende krav). **Flyttes tavlen, skal den opfylde kravene på flytningstidspunktet** | Ingen bagatelgrænse for flytningens længde (sik.dk: Ændring og udskiftning af eltavle, V 2026-10-18) |
| 73 | Klasse I-materiel må tilsluttes en installation uden virksom beskyttelsesleder, når installationen har RCD ≤ 30 mA. Gælder ikke materiel, der kræver beskyttelsesleder for sikker funktion, og elektromedicinsk udstyr | RCD erstatter ikke beskyttelseslederen ved nye jordede stikkontakter (§ 64) |
| Elsikkerhedsloven § 10 | Ejer/bruger er ansvarlig for, at installationen overholder reglerne og drives og vedligeholdes forsvarligt, og skal **lade fejl og mangler afhjælpe snarest muligt** og hurtigst muligt hindre, at de giver fare (LBK 57/2026, V 2026-10-18) | Sig det til ejeren ved fund – og skriv det |

## Ændring og udvidelse – Sikkerhedsstyrelsens tolkning
Kilde: sik.dk "Hvis du skal ændre eller udvide eksisterende installationer" (opdateret 25/2-2025), V 2026-10-18.
- Kun den del, der ændres, skal følge de nye regler; resten skal følge reglerne fra udførelsen **og** RCD-kravet i § 61. Ekstra tilslutningssteder udløser ikke § 57's antal for hele rummet.
- Total renovering, hvor alt fjernes og placering og omfang ændres: ny installation efter gældende regler.
- **Køkken:** elementer skiftes uden ændring af installationen → ingen nye krav. Ændring/udvidelse med højst 2 tilslutningssteder → beskyttelsesleder kan udelades med RCD ≤ 30 mA (§ 63), ingen krav om 2 grupper. **Flere end 2 → mindst 3 stikkontakter i køkkenregionen på mindst 2 grupper (§ 57, stk. 2) og beskyttelsesleder til tilslutningsstederne.**
- Ny gruppe (> 2 tilslutningssteder og nyt kabel til tavlen): RCD ≤ 30 mA; installationen fordeles på mindst 2 RCD'er (krav ved ny gruppe, "bør" ved køkkenudvidelse). Tavlens sikkerhedsniveau må ikke forringes.
- En flyttet stikkontakt er en ny stikkontakt. Den gamle lempelse om udeladt beskyttelsesleder i boliger fra før 1/4-1975 findes ikke længere.

## Solceller – autorisation og tilslutning
Kilde: sik.dk "Det kræver autorisation at tilslutte et solcelleanlæg" og "Krav til installation af solcelleanlæg", V 2026-10-18.
- Tilslutning til den faste installation er **altid** autorisationskrævende. Tilslutningspunktet er det første sted, anlægget leverer 230/400 V AC – typisk inverterens a.c.-afgangsklemmer.
- Montage og sammenkobling: samlesæt købt som ét produkt med samlet montage- og sammenkoblingsbeskrivelse må alle udføre. **Komponenter købt hver for sig** må kun monteres og sammenkobles af autoriseret elinstallatør eller virksomhed, der erhvervsmæssigt servicerer solcelleanlæg (autorisationslovens § 2, nr. 4).
- Inverterens a.c.-kabel tilsluttes **som generatoranlæg på tilgangssiden af beskyttelsesudstyret i fordelingstavlen** (HD 60364-5-551 pkt. 551.7), ikke på en vilkårlig gruppe. **Stikprop og stikkontakt er udelukket.**
- RCD for inverterkredsen: type B, medmindre inverteren giver mindst enkel adskillelse eller fabrikanten oplyser, at type B ikke kræves.
- Mærkning: tavlen skal have solcelleskilt (HD 60364-7-712 pkt. 712.514), og spændingsførende dele mærkes med, at de kan være strømførende efter adskillelse.
- Verifikation: HD 60364-6 og EN 62446. Service på fast tilsluttet anlæg kræver samme kvalifikation som sammenkobling. Installatøren kan lovligt tilkoble et anlæg, andre har monteret, uden at overtage ansvaret for det.

## Netselskab – Fællesregulativet 2026
Kilde: Fællesregulativet 2026, V 2026-10-18.
- **Tilmelding før arbejdet påbegyndes** (Del A pkt. 2): altid ved nye tilslutninger, ændring af bestående installationer, produktionsanlæg (fx solceller), elektriske energilageranlæg (batteri), varmepumper og ladestandere, afmelding og plombebrud. Udvides det tilmeldte, kræves ny tilmelding.
- **Kortslutningsniveau** (Del B pkt. 13–14), når netselskabet ikke oplyser andet: største kortslutningsstrøm 16 kA (3-faset, cos φ 0,3) foran stikledningen; **mindste fase-nul-kortslutningsstrøm Ik min = 5 × stikledningssikringens mærkestrøm** i kabelnet (også i luftledningsnet, medmindre andet oplyses). I maskenet (Radius Frederiksberg/City, Elektrus) og ved direkte tilslutning i transformerstation skal værdierne altid indhentes.

## Badeværelse – områder (DS/HD 60364-7-701:2024)
Kilde: sik.dk-vejledning om 701:2024 og SIK-huseftersynshåndbog v19 bilag 4, V 2026-10-31. Mål områderne på planen [KRAV]:
- **Bruser uden kar (også kun forhæng):** område 1 = 1,2 m fra vandudløbet, målt uden om faste skillevægge, op til 2,25 m. **Intet område 2.** Område 0 = i karret eller 0,1 m over brusegulvet, kun SELV ≤ 12 V AC, IPX7.
- **Badekar/kabine:** område 1 over karret, **område 2 = 0,6 m** ud fra kanten.
- IPX4 i område 1–2 (spuling: IP55, område 0 IP67). Ingen 230 V-stikkontakter i område 0–2 (i praksis ≥ 1,2 m fra åben bruser, V sekundær Bolius). Afbrydere tidligst i område 2. Område 3 findes ikke længere.

## RCD, jordingssystem og SPD
- **Mindst to RCD'er** (type A, 30 mA) i nye tavler, lækstrøm ≤ 0,3 × IΔn pr. RCD [ANVISNING sik.dk "Valg og installation af RCD", 531.3.6 – V 2026-10-31].
- **Elbil:** egen RCD, normalt type B 30 mA. Type A/F kun med RDC-DD (6 mA DC) i laderen efter fabrikanten [ANVISNING sik.dk "Opladning af elbiler" – V 2026-10-31]. Type B sættes ikke efter type A/F, fordi glat DC blinder den, medmindre B'en begrænser DC til 6 mA [ERFARING fabrikant – V sekundær]. Frekvensomformer: 1-faset F, 3-faset B (T).
- **TT er udgangspunktet** fra det offentlige net. TN kun med egen transformerstation, kabelstikledning direkte fra stationen, eksisterende TN eller netejerens tilladelse. Ingen TN-C efter første tavle [KRAV BEK 1082 §§ 27–28 – V 2026-10-31].
- **SPD er et betinget krav:** fra 1/7-2019 skal behovet vurderes (§ 13), typisk type 2 i tavlen. Det er ikke krav før 2019, i tæt bymiljø, efter risikovurdering (443.5) eller når værdien er ≤ 5 × SPD-prisen [ANVISNING sik.dk og huseftersynshåndbog pkt. 10a – V 2026-10-31]. Skriv "vurderet", ikke "krævet".

## Opslagsrækkefølge
1. sik.dk – regler, gør-det-selv, vejledninger, autorisationsregisteret
2. retsinformation.dk – lov og bekendtgørelser
3. ds.dk – standardernes udgave og status
4. Netselskabets tilslutningsbestemmelser og producentens installationsvejledning

## Kontrol og dokumentation
| Kilde | Krav | Status |
|---|---|---|
| Installationsbekendtgørelsen § 75 | Verifikation skal foretages, inden installationen idriftsættes: eftersyn, afprøvning og rapportering efter gældende DS/HD 60364-6; rapporten indgår i KLS-slutkontrollen | V 2026-09 (elsikkerhed.dk-gengivelse; sik.dk-vejledninger) |
| Sikkerhedsstyrelsen – vejledninger om eftersyn, afprøvning og rapportering | Eftersyn før afprøvning og før spænding; tjekliste efter DS/HD 60364-6:2016 (anneks E rapport, F eftersyn, G prøveresultater) | V 2026-09 (sik.dk) |
| BEK nr. 725 af 12/06/2024 (KLS) | Slutkontrol ved nyinstallation, udvidelse og ændring; dokumentation af udfører, kontrollant, dato og resultat; opbevares 5 år | V 2026-09 |
