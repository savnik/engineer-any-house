# Faser, gates og ændringsstyring

Fasemodellen følger byggeriets egen faseopdeling. Den bygger på Ydelsesbeskrivelser for Byggeri og Planlægning (FRI og Danske Ark) og på stage gates og ændringsstyring fra PRINCE2 og ISO 21502. Formålet er at **designe færdigt, før der planlægges**, og at **samle ændringer i stedet for at revidere efter hver ny oplysning**. Det er den største kilde til spildtid i loopet.

## Faserne
| Fase | Navn | Leverancer | Kontrolniveau | Gate til næste fase |
|---|---|---|---|---|
| **0** | Afklaring | `projektgrundlag.md`, fakta pr. fag efter `definition-of-ready.md`, fotos, registreringer, manualer | `projekt-kontrol`, let (`KONTROLNIVEAU: let`) | **G0:** Definition of Ready er opfyldt for hvert berørt fag. Manglende fakta er indsamlet eller markeret som antagelse og accepteret af brugeren. Projektgrundlaget er accepteret |
| **1** | Dispositionsforslag | Kort beslutningsnotat pr. fag: princip, 1–2 alternativer, groft budget ±30 %, afgørende risici og **sikkerhedsprincipper** | Let review | **G1:** Brugeren har valgt løsningsprincip pr. fag (beslutningsloggen). Projektlederen har lavet **grænsefladeregistret** (`graenseflader.md`) med én ejer pr. snitflade og har prissat **fag uden agent** (screening, kloakmester, statiker, varmetab, skorstensfejer, servicefirma m.fl.) i `budget.md` |
| **2** | Design (projektforslag) | Fagnotat (højst ca. 250 linjer + bilag): fuld faglig løsning, fejltilstande for sikkerhedskritiske anlæg, grænseflader, kontrol | **Fuld** for sikkerhedskritiske fag, **let** for øvrige | **G2 – design freeze:** alle fagnotater er godkendt, og grænsefladeregistret er lukket (alle konflikter afgjort og logget). Åbne spørgsmål er enten afklaret, eller **brugeren har accepteret dem skriftligt som hold points før tilbud** (AskUserQuestion, logget). Uden accept er G2 ikke nået |
| **3** | Integration og plan | Tidsplan, samlet budget ±10–15 %, montage og rækkefølge, kontrolplan, risikoregister og tilbudsgrundlag. **Én samlet planleverance** | Fuld `projekt-kontrol` på den samlede plan | **G3:** Planen er godkendt og accepteret af brugeren. Hooken kræver `DESIGNGRUNDLAG` med godkendte fagleverancer |
| **4** | Udbud og udførelse | Tilbudsvurdering, kontrakter, hold points, dokumentation | Efter behov (`ekstern/` for tilbud) | Ændringer kun via ændringsstyring |

**Regler:**
- **Navne på hold points fastlægges i fase 0:** `HP-<FAG>-n` pr. fag og HP1–HPn projektfælles. Det står i projektgrundlaget og ændres ikke undervejs.
- **Grænsefladeregistret** udfyldes af projektlederen ved G1 ud fra fase 1-notaterne: snitflade, fag A, fag B, ejer, hvad der leveres og fase. Det gives med i alle fagforespørgsler i fase 2. Konflikter, fagene melder, afgøres af projektlederen og logges, før returen sendes.
- **Ingen tidsplan, intet detailbudget og ingen montagerækkefølge før G2.** Før det findes kun milepæle ("tilbud uge 40–41", "montage i fyringssæsonen") i `status.md`.
- **Planleverancer samles.** Beholderplan, rumsplan og samlet plan skrives som ét dokument (eller ét dokument med delafsnit) med ét leverance-ID, ikke som flere delplaner, der hver skal kontrolleres og revideres.
- **Sikkerhedskritiske fag** (fuld kontrol i fase 2): vvs ved kedel, fjernvarme eller gas; el; bærende konstruktioner; brand; asbest, PCB og bly. Øvrige får let review i fase 2.
- **Parallelt og i baggrunden:** fag uden indbyrdes afhængighed kaldes samtidig. Kontrolkald køres i baggrunden, så brugeren kan stille spørgsmål imens. Kvalitetskontrollen afsnit 2.10 beskriver, hvordan en baggrundsdom registreres.

## Rækkefølge ved returer
- Uafhængige fag rettes parallelt.
- Fag, der deler en snitflade eller henviser til hinandens hold points, rettes **i rækkefølge**: først ejeren af snitfladen, derefter det fag, der henviser. Projektlederen afgør konflikten først og giver begge fag samme beslutning.
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
| `let` | Tjekker sikkerhed og lovkrav, afgørende fejl og om opgaven er besvaret. Kun kritiske fund og væsentlige fund med sikkerheds- eller lovkonsekvens blokerer | Fase 0 og 1, ikke-sikkerhedskritiske fag i fase 2 |
| `fuld` | Hele kontrolprotokollen, alle punkter og fejlkataloget | Sikkerhedskritiske fag i fase 2 og den samlede plan i fase 3 |

**Fund-fastlåsning (alle niveauer):** Forsøg 1 er det fulde review. I forsøg 2 og 3 tjekker kontrollen kun, om fundene er lukket, og om de ændrede afsnit har skabt regressioner. Et nyt blokerende fund skal have `nyt_grundlag` (`regression`, `aendret_tekst` eller `kritisk_sikkerhed`). Ellers sender hooken dommen retur.

## Ændringsstyring (efter G2)
En ny oplysning eller beslutning, der ændrer et godkendt design, behandles sådan:
1. Skriv den i `aendringer.md`: dato, ændring, kilde og **konsekvensanalyse** (hvilke leverancer rammes: fagnotat, plan, budget, grænseflader).
2. **Saml ændringerne.** Revidér én gang pr. batch, fx når et sæt afklaringer fra servicefirma, installatør eller bruger er modtaget. Revidér ikke pr. oplysning.
3. Revisionen får nyt leverance-ID (`-r2`) og fuldt kontrolniveau på det ændrede. Planen revideres først, når de ændrede fagnotater er godkendt (hooken håndhæver det).
4. Små ændringer uden faglig konsekvens (fx en dato) noteres kun i `aendringer.md` og `status.md` uden ny kontrol.

## Fagforespørgsel og retur – hold det kort
- Fagforespørgslen angiver `FASE: <n>` og `KONTROLNIVEAU: let|fuld` og, i fase 3, `DESIGNGRUNDLAG:`.
- Fase 1: beslutningsnotat (højst ca. 2 sider). Fase 2: fagnotat uden tilbudsgrundlag. Tilbudstjekliste og montagetrin skrives først i fase 3 som en del af den samlede plan.
- Retur: fagagenten retter **kun de berørte afsnit** med Edit og skriver ikke notatet om. Kontrolrespons står i en kort tabel.
