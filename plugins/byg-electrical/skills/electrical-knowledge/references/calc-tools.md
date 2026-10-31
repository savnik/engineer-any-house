# El – regneværktøj `el.py`

Kør: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/electrical-knowledge/scripts/el.py" <kommando> …` (kun standardbiblioteket; skriver ingen filer). Første linje i svaret er kommandoen – gengiv den i bilaget, så kontrollen kan genkøre den.

| Kommando | Regner | Vigtige flag |
|---|---|---|
| `iz` | Iz = tabelværdi × Ca × Cg × Ci for hver del af ruten; den værste del afgør. Kontrol Ib ≤ In ≤ Iz og I2 ≤ 1,45 Iz | `--size --insulation pvc/xlpe --method B2 --method C` (én pr. del) `--loaded 2/3 --insulated-mm --ambient --grouped/--cg --rating --device mcb/gG --ib` |
| `vdrop` | ΔU i % inkl. foranliggende fald, maks. længde for valgt og næste tværsnit | `--size --length --current --phases 1/3 --cosphi --upstream --limit` |
| `ikmin` | Ik,min L–N i kredsens ende mod Ia; maks. længde; udkoblingstid mod kablets grænse, hvis Ik < Ia | `--size --length --rating --curve B/C/D/gG [--ia] --ik-net` eller `--service-fuse`, `--feeder-size --feeder-length` |
| `ikmax` | Ik,max ved tavlen (16 kA foran stikledningen minus stikledningen) mod brydeevne | `--icn 6000/10000 --ik-net --feeder-size --feeder-length` |
| `panel <fil>` | Hele tavlen: fast gruppeskema + fund (se nedenfor) | `--format md/json` |
| `template` | Eksempel på tavlefil – kopiér og ret | |
| `test` | Selvtest mod håndregnede værdier | |

## Tavlefil (JSON, danske nøgler)
`el.py template` viser formatet. Kort:
- `tavle`: `system` (TT/TN), `forsikring` (A), `ik_min_net`/`ik_max_net` (A, foran stikledningen; tom → Fællesregulativets standard), `stikledning` {`tvaersnit`, `laengde`, `isolering`}, `spaendingsfald_foran`, `spaendingsfald_graense`, `pladser`, `pladser_brugt`, `backup_ka` (fabrikantens back-up-værdi for automat bag forsikring).
- `rcd[]`: `id`, `type` (A, F, B, B-EV, S, AC), `ma`, `in`, `foran` (id på RCD foran eller tom).
- `grupper[]`: `nr`, `navn`, `sikring`, `kurve` (B/C/D/gG), `icn`, `fase` (L1, L2, L3 eller L1L2L3), `kabel`, `tvaersnit`, `isolering`, `metode` (liste – én pr. del af ruten), `isoleret_mm`, `samlet`, `laengde`, `last` (A), `rcd`, `anvendelse` (lys, stik, elbil, varmepumpe, frekvensomformer – de tre sidste udløser RCD-kontrollen), evt. `led_spots` (`led_maks` fra driverens datablad) og `rdc_dd: true` (lader med 6 mA DC-detektering).

## Fast gruppeskema
`el.py panel` skriver altid denne tabel – brug den uændret i notatet:

`| Gruppe | Sikring/kurve | Fase | Kabel/tværsnit/metode | RCD (type/mA) | Længde | ΔU % | Ik,min | Status |`

Derefter fundtabellen `| Gruppe | Alvor | Fund | Kilde |` med alvor **advarsel** (krav ikke opfyldt), **vejledende** (anbefaling eller manglende dokumentation) og **info**.

Tavlekontrollen fanger: Iz/I2-overskridelse, Ib > In, ΔU over grænsen, Ik,min < Ia, brydeevne < Ik,max uden back-up, kreds uden RCD ≤ 30 mA, type AC, type B efter A/F, RCD'er i serie uden selektivitet (type S, 3 × IΔn), RCD-In under forsikringen, færre end to 30 mA-RCD'er, elbil uden type B/RDC-DD eller på delt RCD, varmepumpe uden type B/F, LED-spots over ca. 30 pr. B16, faselast over forsikringen og skævlast, under 20 % reservepladser, forsikring < 1,6 × største gruppe.

## Forudsætninger og grænser
- Kobber, 230/400 V, 30 °C luft. Iz-tabeller: DS/HD 60364-5-52 anneks B (B.52.2–B.52.5, B.52.10, B.52.12) – værdierne V sekundær 2026-10-31 (Prysmian 2024, Top Cable); selve DS/HD-teksten er ikke læst.
- `xlpe` = NOIKLX 90 (PEX, 90 °C – V sekundær NKT); `pvc` = PVIKLX, ældre NOIKLX før 2015 og ukendt kabel (T).
- Ci (helt omgivet af isolering) efter BS 7671 tabel 52.2, interpoleret, kun ≤ 10 mm² (V sekundær). Jord i metode D regnes ikke.
- Modstand: R20 efter IEC 60228 med α = 0,00393/K ved ledertemperaturen (70/90 °C); X = 0,08 mΩ/m (T).
- Ik,min: 5 × stikledningssikringen foran stikledningen (Fællesregulativet 2026 pkt. 14, V); Ia = 5/10/20 × In for B/C/D (V sekundær). Ik,max: 16 kA, cos φ 0,3 (V).
- ΔU-grænse 4 % (pkt. 525) er en anbefaling, ikke et dansk krav (svag V).
- Selektivitet (1,6 ×), LED-indkobling (30 pr. B16), reserve 20 % og skævlast er tommelfingerregler [ERFARING – T].
- Værktøjet er projekteringshjælp. Den autoriserede elinstallatør verificerer og måler (BEK 1082 § 75 og DS/HD 60364-6).
