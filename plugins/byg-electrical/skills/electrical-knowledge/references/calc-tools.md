# El – regneværktøj `el.py`

Læses kun, når en gruppe, et kabel eller en tavle skal dimensioneres. Andre spørgsmål besvares fra normgrundlag og praksis.

## Sådan arbejder du
- Regn med værktøjet, aldrig i hovedet. Bash er låst af en hook til kun at køre `el.py`, én kommando ad gangen. Skriv tavlefilen med Write i sagsmappen.
- Aflevér gruppeskemaet som tabellen fra `el.py panel` med fundene. Skriv kommando og resultat i `trade-notes/electrical-appendix.md`, så kontrollen kan genkøre dem.
- Et tavlediagram (enstregsdiagram) tegnes efter `schematic.md` med tallene fra `el.py panel`.
- Værdier, du ikke kender (Ik fra netselskabet, kabellængde, isolering langs ruten), skrives som antagelser i notatet.

Kør: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/electrical-knowledge/scripts/el.py" <kommando> …` (kun standardbiblioteket; skriver ingen filer). Første linje i svaret er kommandoen – gengiv den i bilaget, så kontrollen kan genkøre den.

| Kommando | Regner | Vigtige flag |
|---|---|---|
| `iz` | Iz = tabelværdi × Ca × Cg × Ci for hver del af ruten; den værste del afgør. Kontrol Ib ≤ In ≤ Iz og I2 ≤ 1,45 Iz | `--size --insulation pvc/xlpe --method B2 --method C` (én pr. del) `--loaded 2/3 --insulated-mm --ambient --grouped/--cg --rating --device mcb/gG --ib` |
| `vdrop` | ΔU i % inkl. foranliggende fald, maks. længde for valgt og næste tværsnit | `--size --length --current --phases 1/3 --cosphi --upstream --limit` |
| `ikmin` | Ik,min L–N i kredsens ende mod Ia; maks. længde; udkoblingstid mod kablets grænse, hvis Ik < Ia | `--size --length --rating --curve B/C/D/gG [--ia] --ik-net` eller `--service-fuse`, `--feeder-size --feeder-length --feeder-insulation pvc/xlpe` (standard xlpe) |
| `ikmax` | Ik,max ved tavlen (16 kA foran stikledningen minus stikledningen) mod brydeevne | `--icn 6000/10000 --ik-net --feeder-size --feeder-length` |
| `panel <fil>` | Hele tavlen: fast gruppeskema + fund (se nedenfor) | `--format md/json` |
| `template` | Eksempel på tavlefil – kopiér og ret | |
| `test` | Selvtest mod håndregnede værdier | |

## Tavlefil (JSON, danske nøgler)
`el.py template` viser formatet. Kort:
- `tavle`: `system` (TT/TN), `forsikring` (A), `ik_min_net`/`ik_max_net` (A, foran stikledningen; tom → Fællesregulativets standard), `stikledning` {`tvaersnit`, `laengde`, `isolering`}, `spaendingsfald_foran`, `spaendingsfald_graense`, `pladser`, `pladser_brugt`, `backup_ka` (fabrikantens back-up-værdi for automat bag forsikring).
- `rcd[]`: `id`, `type` (A, F, B, B-EV, S, AC), `ma`, `in`, `foran` (id på RCD foran eller tom).
- `grupper[]`: `nr`, `navn`, `sikring`, `kurve` (B/C/D/gG), `icn`, `fase` (L1, L2, L3 eller L1L2L3), `kabel`, `tvaersnit`, `isolering`, `metode` (liste – én pr. del af ruten), `isoleret_mm`, `samlet`, `laengde`, `last` (A), `rcd`, `anvendelse` (lys, stik, elbil, varmepumpe, frekvensomformer – de tre sidste udløser RCD-kontrollen), `stikkontakt_a` (10, 13 eller 16 – stikkontakternes mærkestrøm; tom ved `stik` → 13 A antaget), evt. `led_spots` (`led_maks` fra driverens datablad) og `rdc_dd: true` (lader med 6 mA DC-detektering).

## Fast gruppeskema
`el.py panel` skriver altid denne tabel – brug den uændret i notatet:

`| Gruppe | Sikring/kurve | Fase | Kabel/tværsnit/metode | RCD (type/mA) | Længde | ΔU % | Ik,min | Status |`

Derefter fundtabellen `| Gruppe | Alvor | Fund | Kilde |` med alvor **advarsel** (krav ikke opfyldt), **vejledende** (anbefaling eller manglende dokumentation) og **info**.

Tavlekontrollen fanger: Iz/I2-overskridelse, Ib > In, ΔU over grænsen, Ik,min < Ia, brydeevne < Ik,max uden back-up, kreds uden RCD ≤ 30 mA, type AC, type B efter A/F, RCD'er i serie uden selektivitet (type S, 3 × IΔn), RCD-In under forsikringen, færre end to 30 mA-RCD'er, elbil uden type B/RDC-DD eller på delt RCD, sikring over 13 A foran 10/13 A-stikkontakter eller over 16 A foran 16 A (BEK 1082 § 45), varmepumpe uden type B/F, LED-spots over ca. 30 pr. B16, faselast over forsikringen og skævlast, under 20 % reservepladser, forsikring < 1,6 × største gruppe.

## Forudsætninger og grænser
- Kobber, 230/400 V, 30 °C luft. Iz-tabeller: DS/HD 60364-5-52 anneks B (B.52.2–B.52.5, B.52.10, B.52.12) – værdierne V sekundær 2026-10-31 (Prysmian 2024, Top Cable); selve DS/HD-teksten er ikke læst.
- `xlpe` = NOIKLX 90 (PEX, 90 °C – V sekundær NKT); `pvc` = PVIKLX, ældre NOIKLX før 2015 og ukendt kabel (T).
- Ci (helt omgivet af isolering) efter BS 7671 tabel 52.2, interpoleret, kun ≤ 10 mm² (V sekundær). Jord i metode D regnes ikke.
- Modstand: R20 efter IEC 60228 med α = 0,00393/K ved ledertemperaturen (70/90 °C); X = 0,08 mΩ/m (T). Det giver ρ70 ≈ 0,0217–0,0222 Ω·mm²/m afhængigt af tværsnittet – 1,5–3,5 % under håndregningskonventionen ρ = 0,0225 (1,25 × ρ20, T). Valgt bevidst (tabelværdier pr. tværsnit); ved håndregning med 0,0225 bliver ΔU og z_kabel tilsvarende større og Ik,min/maks. længde lidt mindre. Stikledningen regnes ved isoleringens maks. temperatur (`--feeder-insulation`, tavlefilens `stikledning.isolering`).
- Ik,min: 5 × stikledningssikringen foran stikledningen (Fællesregulativet 2026 pkt. 14, V); Ia = 5/10/20 × In for B/C/D (V sekundær). Ik,max: 16 kA, cos φ 0,3 (V).
- ΔU-grænse 4 % (pkt. 525) er en anbefaling, ikke et dansk krav (svag V).
- Selektivitet (1,6 ×), LED-indkobling (30 pr. B16), reserve 20 % og skævlast er tommelfingerregler [ERFARING – T].
- Værktøjet er projekteringshjælp. Den autoriserede elinstallatør verificerer og måler (BEK 1082 § 75 og DS/HD 60364-6).

## Dimensionering – regelgrundlag
- **Strømværdi Iz:** DS/HD 60364-5-52 anneks B (kobber, 30 °C) tabel B.52.2–B.52.5 (metode A1–C) og B.52.10/B.52.12 (metode E) [NORM – værdierne V sekundær 2026-10-31 mod Prysmian 2024/Top Cable]. Ruten dimensioneres efter den værste del. NOIKLX 90 er PEX/XLPE 90 °C (NKT-data, V sekundær); ældre NOIKLX (før maj 2015), PVIKLX og ukendt kabel regnes med PVC 70 °C-tabellerne (T).
- **Kabel helt omgivet af isolering** (fx efter efterisolering af loft): faktor på metode C – 50 mm 0,88 · 100 mm 0,78 · 200 mm 0,63 · 400 mm 0,51 · ≥ 0,5 m 0,50 [V sekundær: BS 7671 tabel 52.2, gælder til 10 mm²; om tabellen findes i DS/HD: T].
- **Overbelastning:** Ib ≤ In ≤ Iz og I2 ≤ 1,45 × Iz (433.1); automatsikring I2 = 1,45 In, gG 1,6 In (In ≥ 16 A) [V sekundær].
- **Spændingsfald:** DS/HD 60364-5-52 pkt. 525 anbefaler højst 4 % fra installationens begyndelse – en anbefaling, ikke et dansk krav; Fællesregulativet har intet krav (V 2026-10-31). Anneks G (offentligt net): 3 % lys / 5 % andet [V sekundær, svag].
- **Kortslutning:** Ik max 16 kA (3-faset, cos φ 0,3) og Ik min L–N = 5 × stikledningssikringen gælder **umiddelbart foran stikledningen** – læg stikledningens impedans til for værdien ved tavlen [KRAV Fællesregulativet 2026 Del B pkt. 13–14 – V 2026-10-31]. Ik,min i gruppens ende ≥ Ia (B 5 In, C 10 In, D 20 In efter EN 60898-1 – V sekundær; mange D-automater 10–14 In); ellers dokumentér udkoblingstiden mod kablets grænse (k²S²/I²). Automatsikringers brydeevne 6 eller 10 kA (EN 60898-1); mindre end Ik,max kræver back-up efter fabrikantens tabel [NORM 434.5.1 – T].

## Tavle og undertavle – opbygning
- **Undertavle:** før forsyningen med kappekabel fra tilgangssiden, eller beskyt den med en selektiv type S (fx 300 mA) foran. To 30 mA i serie er ikke selektive. Endelige kredse må ikke kun sidde bag type S. En undertavle deler ikke RCD med husets grupper. Forsikringen foran en RCD må ikke overstige fabrikantens maks. back-up [ERFARING – T].
- **Udkoblingstider** ved 230 V, endelige kredse: TN 0,4 s, TT 0,2 s (tabel 41.1). I TT kobler RCD'en ud ved jordfejl, men overstrømsbeskyttelsen skal stadig klare kortslutning L–N (Ik,min) [V sekundær (IET, Schneider EIG); omfanget – T].
- **Tavleskabeloner** (udgangspunkt, regn altid den konkrete tavle) [ERFARING – T]:
  - (a) Lille bolig (1-faset eller 3 × 25 A): 2 × RCD type A 30 mA, lys og stik fordelt på begge, egne grupper til køkken og vask, ≥ 20 % reserve.
  - (b) Parcelhus (3 × 35 A): 2–3 × RCD type A 30 mA, komfur 3-faset, vaske-, tørre- og opvaskemaskine på hver sin gruppe fordelt på faserne, varmepumpe og elbillader på hver sin RCD, SPD type 2 vurderet.
  - (c) Med undertavle (garage, anneks, tilbygning): hovedledning fra tilgangssiden eller bag selektiv type S, undertavlens egne 30 mA-RCD'er, Ik,min regnes gennem hovedledningen.
- **Kontrolpunkter pr. gruppe:** Iz efter værste del af ruten (Ci, hvor kablet ligger i isolering, også efter efterisolering af loft), ΔU, Ik,min i kredsens ende ≥ Ia, Ik,max ved tavlen ≤ brydeevne eller dokumenteret back-up. LED-spots pr. gruppe efter driverens indkoblingsstrøm.
