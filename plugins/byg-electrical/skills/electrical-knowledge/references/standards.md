# El – normgrundlag

Sidst gennemgået: 2026-10-31. BR18 gælder i den version, der er aktuel fra 1/1-2026 (ældre versioner ligger under "Historisk" på bygningsreglementet.dk). §-numre kan være læst i en ældre version – tjek den aktuelle, før du citerer. **V** = verificeret (kilde), **T** = skal verificeres.

## Kilder
| Kilde | Emne og brug | Status |
|---|---|---|
| Elsikkerhedsloven (LBK nr. 57/2026) | Rammelov for elektriske anlæg, installationer og udstyr; ejerens ansvar (§ 10, se nedenfor) | V 2026-10-18 (retsinformation.dk/eli/lta/2026/57) |
| Installationsbekendtgørelsen, BEK nr. 1082 af 12/07/2016 (ændret ved BEK 639/2017) | Gør DS/HD 60364 gældende; krav til udførelse og dokumentation. Centrale §§ i tabellen nedenfor | V 2026-10-18 (retsinformation.dk/eli/lta/2016/1082) |
| DS/HD 60364-serien | Lavspændingsinstallationer | V (sik.dk) |
| DS/HD 60364-4-41 | Beskyttelse mod elektrisk stød, supplerende beskyttelse med RCD | T (afsnit) |
| DS/HD 60364-5-52 / -5-54 | Kabelinstallationer (strømværdier anneks B, se "Dimensionering") / jording og beskyttelsesledere | Tabelværdier V sekundær 2026-10-31; tekst T |
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
Kilder: sik.dk "Elektrisk materiel i badeværelser (DS/HD 60364-7-701:2024)" (rev. 7/11-2025) og SIK-håndbog for huseftersyn version 19, bilag 4 (tegning "afstande på badeværelser efter juli 2019"), V 2026-10-31. Områderne er geometri – mål dem på planen:
- **Område 0:** inde i karret; i bruser uden kar 0,1 m over gulvet. Kun SELV ≤ 12 V AC/30 V DC, IPX7 [KRAV].
- **Område 1, bruser uden kar (også kun forhæng):** 1,2 m fra det faste vandudløb, målt med snor **uden om faste skillevægge** (fast = kan ikke fjernes uden værktøj), op til 2,25 m. **Der er intet område 2 for brusebade** [KRAV].
- **Badekar / bruser med kabine:** område 1 over karret op til 2,25 m; **område 2 = 0,6 m** ud fra karkanten/kabinen op til 2,25 m [KRAV].
- **IP:** IPX4 i område 1 og 2; hvor der spules: IP55 i område 1–2 og IP67 i område 0 (2024-udgaven) [KRAV]. Område 3 findes ikke længere.
- **Materiel:** ingen 230 V-stikkontakter i område 0–2 (SELV tilladt i område 1–2); afbrydere tidligst i område 2 [KRAV]. Hvilket fast materiel der må sidde i område 1 (vandvarmer, ventilation, armatur m.fl. efter leverandøren) – T.
- Stikkontakt i badeværelse placeres uden for område 0–2 – i praksis mindst 1,2 m fra åben bruser (V sekundær: Bolius).

## RCD – typer, kæde og undertavler
- **Mindst to RCD'er:** installationstavler skal som udgangspunkt fordeles på mindst to RCD'er (type A, 30 mA), så én fejl ikke afbryder hele installationen; projektér lækstrøm ≤ 0,3 × IΔn pr. RCD [ANVISNING sik.dk "Valg og installation af RCD" (4/4-2025), DS/HD 60364-5-53 pkt. 531.3.6 – V 2026-10-31].
- **Elbil:** egen RCD pr. ladepunkt; type B 30 mA er normalvalget; type A/F kun, når laderen selv detekterer glat DC ≥ 6 mA (RDC-DD, IEC 62955) og fabrikanten angiver det [ANVISNING sik.dk "Opladning af elbiler" – V 2026-10-31; 722-pkt.-tekst T].
- **Type B i kæde:** glat DC-fejlstrøm over 6 mA kan blinde en type A/F foran. Type B sættes derfor ikke efter type A/F – forsyn B'en fra tilgangssiden eller brug en type B, som begrænser DC til 6 mA ("B+"/fabrikantens datablad) [ERFARING fabrikant – V sekundær (Doepke, Schneider); 531.3-tekst T].
- **Frekvensomformere (varmepumpe):** 1-faset → type F, 3-faset → type B, medmindre fabrikanten angiver andet [ERFARING – T].
- **Undertavle:** før forsyningen med kappekabel fra tilgangssiden, eller beskyt den med en selektiv type S (fx 300 mA) foran; to 30 mA i serie er ikke selektive; endelige kredse må ikke kun sidde bag type S; undertavle deler ikke RCD med husets grupper; forsikringen foran en RCD må ikke overstige fabrikantens maks. back-up [ERFARING – T; ældre SIK-praksis: grupper i undertavle "beskyttet af HPFI foran tavlen", sik.dk-detaljer kun i video].
- Type AC er forbudt i boliger (§ 53); endelige kredse skal have RCD ≤ 30 mA (§ 35 stk. 1–2) – tabellen ovenfor.

## Jordingssystem – TT eller TN
- Forsyning fra det offentlige net er **TT** som udgangspunkt. TN må kun bruges med egen transformerstation, stikledning direkte fra transformerstationen udført med kabel, hvor TN allerede bruges, eller med netejerens særlige tilladelse; ingen TN-C efter første tavle [KRAV BEK 1082 §§ 27–28 – V 2026-10-31].
- I TT sker udkobling ved jordfejl ved RCD'en; overstrømsbeskyttelsen skal stadig klare kortslutning L–N (Ik,min, se nedenfor). Udkoblingstider TN 0,4 s / TT 0,2 s ved 230 V, endelige kredse (tabel 41.1) [V sekundær (IET, Schneider EIG); omfanget efter 2017-tillægget – stikkontaktkredse ≤ 63 A og fast materiel ≤ 32 A – T].

## Overspændingsbeskyttelse (SPD)
- Fra 1/7-2019 skal behovet vurderes: "Overspændinger må ikke medføre fare" (§ 13). Typisk type 2 SPD i tavlen. Ikke krav i installationer fra før 1/7-2019 og udvidelser af dem, i tæt bymiljø, når risikovurderingen (DS/HD 60364-4-443 pkt. 443.5) viser, at der ikke er behov, eller når installationens og apparaternes værdi højst er 5 × SPD'ens pris [KRAV § 13; ANVISNING sik.dk-nyhed 2019 og huseftersynshåndbog pkt. 10a – V 2026-10-31]. Skriv "vurderet", ikke "krævet".

## Dimensionering – kabler og kortslutning
Regnes med `scripts/el.py` (se `calc-tools.md`); her står forudsætningerne.
- **Strømværdi Iz:** DS/HD 60364-5-52 anneks B (kobber, 30 °C) tabel B.52.2–B.52.5 (metode A1–C) og B.52.10/B.52.12 (metode E) [NORM – værdierne V sekundær 2026-10-31 mod Prysmian 2024/Top Cable]. Ruten dimensioneres efter den værste del. NOIKLX 90 er PEX/XLPE 90 °C (NKT-data, V sekundær); ældre NOIKLX (før maj 2015), PVIKLX og ukendt kabel regnes med PVC 70 °C-tabellerne (T).
- **Kabel helt omgivet af isolering** (fx efter efterisolering af loft): faktor på metode C – 50 mm 0,88 · 100 mm 0,78 · 200 mm 0,63 · 400 mm 0,51 · ≥ 0,5 m 0,50 [V sekundær: BS 7671 tabel 52.2, gælder til 10 mm²; om tabellen findes i DS/HD: T].
- **Overbelastning:** Ib ≤ In ≤ Iz og I2 ≤ 1,45 × Iz (433.1); automatsikring I2 = 1,45 In, gG 1,6 In (In ≥ 16 A) [V sekundær].
- **Spændingsfald:** DS/HD 60364-5-52 pkt. 525 anbefaler højst 4 % fra installationens begyndelse – en anbefaling, ikke et dansk krav; Fællesregulativet har intet krav (V 2026-10-31). Anneks G (offentligt net): 3 % lys / 5 % andet [V sekundær, svag].
- **Kortslutning:** Ik max 16 kA (3-faset, cos φ 0,3) og Ik min L–N = 5 × stikledningssikringen gælder **umiddelbart foran stikledningen** – læg stikledningens impedans til for værdien ved tavlen [KRAV Fællesregulativet 2026 Del B pkt. 13–14 – V 2026-10-31]. Ik,min i gruppens ende ≥ Ia (B 5 In, C 10 In, D 20 In efter EN 60898-1 – V sekundær; mange D-automater 10–14 In); ellers dokumentér udkoblingstiden mod kablets grænse (k²S²/I²). Automatsikringers brydeevne 6 eller 10 kA (EN 60898-1); mindre end Ik,max kræver back-up efter fabrikantens tabel [NORM 434.5.1 – T].

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
