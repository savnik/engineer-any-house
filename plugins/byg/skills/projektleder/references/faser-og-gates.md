# Faser, gates og ændringsstyring

Fasemodellen følger byggeriets egen faseopdeling. Den bygger på Ydelsesbeskrivelser for Byggeri og Planlægning (FRI og Danske Ark) og på stage gates og ændringsstyring fra PRINCE2 og ISO 21502. Formålet er at **designe færdigt, før der planlægges**, og at **samle ændringer i stedet for at revidere efter hver ny oplysning**. Det er den største kilde til spildtid i loopet.

## Faserne
| Fase | Navn | Leverancer | Kontrolniveau | Gate til næste fase |
|---|---|---|---|---|
| **0** | Afklaring | `projektgrundlag.md`, fakta pr. fag efter `definition-of-ready.md`, fotos, registreringer, manualer | `projekt-kontrol`, let (`KONTROLNIVEAU: let`) | **G0:** Definition of Ready er opfyldt for hvert berørt fag. Manglende fakta er indsamlet eller markeret som antagelse og accepteret af brugeren. Projektgrundlaget er accepteret |
| **1** | Dispositionsforslag | Kort beslutningsnotat pr. fag: princip, 1–2 alternativer, groft budget ±30 %, afgørende risici og **sikkerhedsprincipper** | Let review | **G1:** Brugeren har valgt løsningsprincip pr. fag (beslutningsloggen). Projektlederen har lavet **grænsefladeregistret** (`graenseflader.md`) med én ejer pr. snitflade og har prissat **fag uden agent** (screening, kloakmester, statiker, varmetab, skorstensfejer, servicefirma m.fl.) i `budget.md` |
| **2** | Design (projektforslag) | Fagnotat (højst ca. 250 linjer + bilag): fuld faglig løsning, fejltilstande for sikkerhedskritiske anlæg, grænseflader, kontrol | **Fuld** for sikkerhedskritiske fag, **let** for øvrige | **G2 – design freeze:** alle fagnotater er godkendt, og grænsefladeregistret er lukket. Åbne afklaringer er accepteret af brugeren som hold points før tilbud |
| **2→3** | **Manuel gate: løsningsgodkendelse** | Projektlederen præsenterer løsningen for brugeren i `loesningspraesentation.md` (skabelon nedenfor) og kort i chatten | Ingen agentkontrol – brugeren beslutter | **G2-godkendt:** brugeren skriver selv `Godkend G2 <sag-id>`. Hooken registrerer det og binder det til de godkendte fagleverancer. Uden det afvises al detailplanlægning (fase 3) |
| **3** | Integration og plan | Tidsplan, samlet budget ±10–15 %, montage og rækkefølge, kontrolplan, risikoregister og tilbudsgrundlag. **Én samlet planleverance** | Fuld `projekt-kontrol` på den samlede plan | **G3:** Planen er godkendt og accepteret af brugeren. Hooken kræver `DESIGNGRUNDLAG` med godkendte fagleverancer |
| **4** | Udbud og udførelse | Tilbudsvurdering, kontrakter, hold points, dokumentation | Efter behov (`ekstern/` for tilbud) | Ændringer kun via ændringsstyring |

**Regler:**
- **Navne på hold points fastlægges i fase 0:** `HP-<FAG>-n` pr. fag og HP1–HPn projektfælles. Det står i projektgrundlaget og ændres ikke undervejs.
- **Grænsefladeregistret** udfyldes af projektlederen ved G1 ud fra fase 1-notaterne: snitflade, fag A, fag B, ejer, hvad der leveres og fase. Det gives med i alle fagforespørgsler i fase 2. Konflikter, fagene melder, afgøres af projektlederen efter domæneforrang (`koordinering.md`: ejerfaget har forrang, ingen mellemløsninger) og logges, før returen sendes.
- **Ingen tidsplan, intet detailbudget og ingen montagerækkefølge før G2.** Før det findes kun milepæle ("tilbud uge 40–41", "montage i fyringssæsonen") i `status.md`.
- **Planleverancer samles.** Beholderplan, rumsplan og samlet plan skrives som ét dokument (eller ét dokument med delafsnit) med ét leverance-ID, ikke som flere delplaner, der hver skal kontrolleres og revideres.
- **Sikkerhedskritiske fag** (fuld kontrol i fase 2): vvs ved kedel, fjernvarme eller gas; el; bærende konstruktioner; brand; asbest, PCB og bly. Øvrige får let review i fase 2.
- **Kontrolniveauet følger opgavens risiko, ikke kun faget.** `fuld` kræver, at leverancen fastlægger eller ændrer en sikkerhedsfunktion: sikkerhedsudstyr, hydraulik ved varmekilden, el-beskyttelse, bærende konstruktion eller brand. Indkøb, priser, sortiment, materialelister og styklister til et godkendt design får `let`, også i et sikkerhedskritisk fag. Ændrer et produktvalg en sikkerhedsfunktion (fx temperaturklassen på rør ved en kedel), er det `fuld`. **Bærende konstruktioner:** `fuld` kun, når leverancen dimensionerer eller ændrer en bærende del (ny åbning, bjælke, vederlag, opmuring, fundering). Screening, diagnose, fotogennemgang, beregning til orientering og review af egne tidligere notater får `let`. `fuld` kaldes altid med `model: "opus"`.
- **Parallelt i forgrunden:** fag uden indbyrdes afhængighed kaldes samtidig som flere Agent-kald i samme besked. Kontrolkald køres i forgrunden, så dommen er registreret, når svaret kommer, og der ikke skal tjekkes status. Brugerens beskeder venter i køen imens.

## Enkelhedstjek (projektlederen, ved G1 og før løsningspræsentationen)
Stil disse spørgsmål til hvert fag, før gaten passeres. Er svaret ja, så bed faget forenkle, før du går videre.
- Er der en standardløsning, som en almindelig håndværker kender, men som ikke er valgt?
- Er der komponenter, trin eller hold points uden en begrundelse på én linje (krav, risiko eller brugerens ønske)?
- Er der mere end én primær løsning og ét alternativ, eller betingede grene i flere niveauer?
- Kan flere fag løse samme problem med færre firmaer eller dage?
- Kan en håndværker bruge notatet uden at skulle læse alt?
Beslutninger om forenkling skrives i beslutningsloggen.

## Manuel gate efter fase 2 – løsningsgodkendelse
Detailplanlægning (tidsplan, detailbudget, montage og tilbudsgrundlag) starter først, når brugeren har set og godkendt den samlede løsning.

**Sådan gør projektlederen:**
1. Når G2 (design freeze) er nået, og enkelhedstjekket er gennemført, skrives `loesningspraesentation.md` **kun** ud fra de godkendte fagnotater og beslutningsloggen. Der må ikke være nye faglige løsninger i den.
2. Præsentér den kort i chatten (højst ca. 15 linjer) med henvisning til filen. Tilbyd gerne en side, der kan deles.
3. Bed brugeren om én af tre ting:
   - **godkende:** brugeren skriver selv `Godkend G2 <sag-id>`
   - **ændre:** ønskerne går via ændringsstyring tilbage til fase 2, og der kommer en ny præsentation
   - **stoppe:** projektet parkeres
4. Et svar i AskUserQuestion eller en formulering fra Claude tæller **ikke**. Kun brugerens egen besked med den præcise sætning åbner gaten, og hooken registrerer den (UserPromptSubmit).
5. Skriv godkendelsen i beslutningsloggen: dato, hvilke fagleverancer (versioner) der er godkendt, og de accepterede hold points.
6. Ændres en godkendt fagleverance bagefter (nyt `-r2`), falder godkendelsen for den del. Præsentér ændringen, og få en ny `Godkend G2 <sag-id>`.

**Skabelon – loesningspraesentation.md**
```
# Løsningspræsentation – <sag-id> (til godkendelse før detailplanlægning)
Grundlag: <godkendte fagleverancer med ID> · beslutningslog <dato>
## 1. Hvad vi laver – i klart sprog (højst 10 linjer)
## 2. Løsningen pr. fag
| Fag | Valgt løsning | Fravalgt og hvorfor | Hvad det betyder for dig |
## 3. Sikkerhed – de vigtigste barrierer og hvem der sikrer dem
## 4. Økonomi (groft ±20 %) mod rammen, inkl. fag uden agent og buffer
## 5. Tid – milepæle og realistisk slutdato (tidlig, forventet, sen) mod rammen
## 6. Det du selv skal gøre, og gør-det-selv-grænser
## 7. Åbne punkter og hold points før tilbud (accepteret ved G2)
## 8. Risici og hvad der kan ændre løsningen
## 9. Beslutning
Godkend ved selv at skrive: **Godkend G2 <sag-id>**. Eller skriv, hvad der skal ændres.
```


- Uafhængige fag rettes parallelt.
- Fag, der deler en snitflade eller henviser til hinandens hold points, rettes **i rækkefølge**: først ejeren af snitfladen, derefter det fag, der henviser. Projektlederen afgør konflikten først efter domæneforrang og giver begge fag samme beslutning.
- Omdøbninger og ID-ændringer foretages aldrig i en retur, mens et andet fag retter parallelt.

## Tjekliste for tværgående tidsregler (fase 3)
Den samlede plan tjekkes mod alle tidsregler i fagnotater og projektgrundlag, før den sendes til kontrol:
- **Lovfrister:** affaldsanmeldelse (14 dage før start), fortrydelsesret (14 dage), anmeldelser til netselskab og kommune.
- **Hold points:** HP-rækkefølge og forudsætninger (fx friskluft før undertryk, HP7 før puds, HP8 før maling).
- **Måleregler:** fx 48 t uden boring, 72 t stabilt klima og ±1 °C.
- **Maksimale intervaller:** fx el-dag ≤ 7 dage efter skifte og gennemskylning hver 7. dag. Læg altid en reservedag inden for fristen.
- **Driftstilstande:** fyr på Aus og varmestop (R6). Hold points, der kræver varme eller drift, må ikke ligge, mens anlægget står.
- **R1:** ét firma pr. dag.
- **Rammer:** alle R-rammer (tid, budget) med tidlig, forventet og sen gren. Overskridelser er brugerbeslutninger.
- **Kritisk vej:** vis slæk for opstarten (tilbud, kontrol, kontrakter).

## Kontrolniveauer
| Niveau | Hvad kontrollen gør | Hvornår |
|---|---|---|
| `let` | Tjekker sikkerhed og lovkrav, afgørende fejl og om opgaven er besvaret. Kun kritiske fund og væsentlige fund med sikkerheds- eller lovkonsekvens blokerer | Fase 0 og 1, ikke-sikkerhedskritiske fag i fase 2, og opgaver uden ændring af en sikkerhedsfunktion (indkøb, priser, sortiment, materialelister, styklister) |
| `fuld` | Hele kontrolprotokollen, alle punkter og fejlkataloget | Design i fase 2, der fastlægger eller ændrer en sikkerhedsfunktion i et sikkerhedskritisk fag, og den samlede plan i fase 3 |
| `stikprøve` | Som `let`, men kun for ca. hver tredje leverance. Hooken udtager ud fra leverance-ID'et; ikke udtagne svar markeres "Ikke kvalitetskontrolleret (stikprøve, ikke udtaget)" | Kun enkeltstående fagspørgsmål uden sag (`/byg:spoerg`, intet `FASE:`) uden sikkerhedsfunktion. Aldrig el og statik. Leverancer i en sag kontrolleres altid |

**Hvorfor stikprøve kun uden sag (F-012, 2026-10-20):** På eksamenssættets enkeltstående spørgsmål fangede `let` kontrol 0 af 7 forkerte svar og afviste 6 rigtige. I rigtige sager blev 56 % af leverancerne afvist i forsøg 1, og ca. 60 % af de blokerende fund handlede om sammenhængen med sagen: grænseflader, andre fags notater, beslutningslog og ejendomskort. Den værdi findes kun, når der er en sag.

**Fund-fastlåsning (alle niveauer):** Forsøg 1 er det fulde review. I forsøg 2 og 3 tjekker kontrollen kun, om fundene er lukket, og om de ændrede afsnit har skabt regressioner. Et nyt blokerende fund skal have `nyt_grundlag` (`regression`, `aendret_tekst` eller `kritisk_sikkerhed`). Ellers sender hooken dommen retur.

## Ændringsstyring (efter G2)
En ny oplysning eller beslutning, der ændrer et godkendt design, behandles sådan:
1. Skriv den i `aendringer.md`: dato, ændring, kilde og **konsekvensanalyse** (hvilke leverancer rammes: fagnotat, plan, budget, grænseflader).
2. **Saml ændringerne.** Revidér én gang pr. batch, fx når et sæt afklaringer fra servicefirma, installatør eller bruger er modtaget. Revidér ikke pr. oplysning.
3. Revisionen får nyt leverance-ID (`-r2`) og et kontrolniveau efter ændringens risiko (se tabellen ovenfor): `fuld`, når den ændrer en sikkerhedsfunktion, ellers `let`. Planen revideres først, når de ændrede fagnotater er godkendt (hooken håndhæver det).
4. Små ændringer uden faglig konsekvens (fx en dato) noteres kun i `aendringer.md` og `status.md` uden ny kontrol.

## Fagforespørgsel og retur – hold det kort
- Fagforespørgslen angiver `FASE: <n>` og `KONTROLNIVEAU: let|fuld` og, i fase 3, `DESIGNGRUNDLAG:`.
- Fase 1: beslutningsnotat (højst ca. 2 sider). Fase 2: fagnotat uden tilbudsgrundlag. Tilbudstjekliste og montagetrin skrives først i fase 3 som en del af den samlede plan.
- Fagforespørgslen peger på de relevante afsnit (fil og afsnit) frem for hele filer.
- Retur: kun de blokerende fund (kritisk og væsentlig) sendes retur. Mindre fund og nye ønsker sendes ikke med; nye ønsker bliver en ny leverance. Fagagenten retter **kun de berørte afsnit** med Edit og skriver ikke notatet om. Kontrolrespons står i en kort tabel.
