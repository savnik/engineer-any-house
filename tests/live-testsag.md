# Live-testsag – byg-eksperter i Claude Code

Formål: afprøve hele kæden på en realistisk sag – interview → sagsmappe → fagleverancer → uafhængig kvalitetskontrol → retur/loop → stop og RCA → samlet plan → erfaring – og bekræfte, at hooks faktisk håndhæver reglerne i en rigtig session.

Tidsforbrug: 60–90 minutter. Kontrolagenterne kører på Opus, så en fuld kørsel koster en del tokens.

## Dækning – hvad er allerede testet, og hvad mangler
| Niveau | Hvad | Status |
|---|---|---|
| Enhed | Hook-logikken (`tests/test_kontrol_gate.py`, 27 tests) | Består – men kun med simulerede hændelser |
| Struktur | `scripts/valider.py --claude` (manifester, navne, stier, protokoller) | Består |
| Evals | `claude plugin eval` pr. plugin | Ikke kørt |
| **End-to-end** | **Denne testsag** | **Mangler – det er formålet** |
| Cowork | Samlet `byg.plugin` med hooks | Mangler (fase F) |

## 1. Forberedelse
1. Tjek forudsætninger:
   ```
   claude --version
   python3 --version
   ```
2. Pak `byg-eksperter.zip` ud, fx til `~/byg-eksperter`.
3. Installér:
   ```
   claude plugin marketplace add ~/byg-eksperter
   claude plugin install byg-team@byg-eksperter
   claude plugin list
   ```
   Forventet: `byg-team`, `byg`, `byg-kontrol` og de seks fag-plugins er installeret og aktiveret.
4. Lav en tom testmappe og start Claude Code dér:
   ```
   mkdir -p ~/byg-test && cd ~/byg-test && claude
   ```
5. Tjek i sessionen: `/agents` viser fag- og kontrolagenterne (fx `byg-vvs:vvs-mester`, `byg-kontrol:vvs-kontrol`), `/hooks` viser byg-kontrols PreToolUse-, SubagentStop- og Stop-hooks, og `/byg:` foreslår kommandoerne.

**Sådan ser du kontrolsystemets tilstand undervejs** (i en anden terminal):
```
LOG=$(find ~/.claude -path '*kontrol/log.jsonl' 2>/dev/null | head -1); echo "$LOG"
tail -n 5 "$LOG"
BK=$(dirname "$(dirname "$LOG")")
CLAUDE_PLUGIN_DATA="$BK" python3 ~/byg-eksperter/plugins/byg-kontrol/hooks/kontrol_gate.py status
```
Finder `find` intet, efter at der har været et fagkald, kører hooks ikke – se afsnit 6.

## 2. Testsagen
Start med:
```
/byg:nyt-projekt Vi vil have et helt nyt badeværelse i vores parcelhus fra 1962
```
Svar på interviewet med disse oplysninger – giv dem kun, når der bliver spurgt, så interviewet også testes:
- Badeværelse i stueplan, ca. 2,1 × 1,8 m, murede vægge, betongulv, loft af træbjælker med isoleret tagrum over.
- I dag: badekar, gammelt gulvafløb, ingen mekanisk udsugning (kun vindue), ingen stikkontakt. Tavlen har et gammelt HFI-relæ, og stikkontakterne i huset er originale.
- Ønsker: bruseniche uden kant, el-gulvvarme, ny håndvask med skab, spots i loftet, stikkontakt ved spejlet, mekanisk udsugning.
- Budget ca. 180.000 kr., start om ca. 2 måneder, huset har et ekstra toilet.
- Vi vil selv stå for nedrivning og maling.
- Tilstandsrapporten nævner fugt nederst i væggen ved badekarret.
- Håndværkere: autoriseret vvs- og el-installatør, flisemurer. Ingen tilbud endnu.

## 3. Tjekpunkter
Notér resultatet i skemaet i afsnit 5. "Hvor ses det" peger på sagsmappen `byg-sager/<dato>-…/`.

### Fase A – Interview og projektgrundlag
| ID | Tjekpunkt | Forventet | Hvor ses det |
|---|---|---|---|
| A1 | Interview før løsning | Højst 3–4 spørgsmål ad gangen; ingen fagagenter kaldes, før Definition of Ready er opfyldt | Samtalen |
| A2 | Farlige stoffer og gør-det-selv | Asbest- og PCB-screening før jeres egen nedrivning nævnes (hus fra 1962); el og vvs kræver autorisation | Samtalen, `projektgrundlag.md` |
| A3 | Sagsmappe | `projektgrundlag.md`, `status.md`, `beslutningslog.md` m.fl. oprettet | Sagsmappen |
| A4 | Kontrol af projektgrundlag | `projekt-kontrol` kaldes med `LEVERANCE: <sag-id>/projekt/01`; JSON-dom gemt | `kvalitet/*.json`, `kvalitet/kontrollog.md` |

### Fase B – Fagleverancer og kvalitetskontrol
Kør `/byg:koordiner`.
| ID | Tjekpunkt | Forventet | Hvor ses det |
|---|---|---|---|
| B1 | Rigtige fag | Mindst vvs, el, murer (vådrum), ventilation; gerne tømrer (spots i isoleret loft) og maler | Samtalen, `fagnotater/` |
| B2 | Leverance-ID | Første linje i hvert fagkald er `LEVERANCE: <sag-id>/<fag>/<nr>` | Transcript, hook-log |
| B3 | Fag → modsvarende kontrol | Hver fagleverance følges af sit eget fags kontrolagent | `kvalitet/kontrollog.md`, hook-log |
| B4 | Dommens form | JSON-blok; blokerende fund har krav, kilde og evidens; "godkendt" kun uden åbne kritiske/væsentlige fund | `kvalitet/*.json` |
| B5 | Retur ved afvisning | Fundene sendes ordret retur; fagnotatet får "Kontrolrespons" og "Revisioner"; forsøg 2 registreres | Fagnotat, status-kommandoen |
| B6 | Uafhængighed | Kontrolagenten bruger egne kilder (WebSearch/WebFetch) og retter ikke selv i notatet | Transcript, notatets historik |

### Fase C – Hooks (negative tests)
| ID | Handling du laver | Forventet | Hvor ses det |
|---|---|---|---|
| C1 | Skriv: "Spørg vvs-mester direkte, hvordan man flytter et gulvafløb" | Første kald uden leverance-ID afvises af hooken; Claude tilføjer ID'et (eller bruger `/byg:spoerg`) og kører kontrollen bagefter | Transcript, hook-log (`fagkald`) |
| C2 | Midt i en fagleverance: "Lav med det samme en ny version af VVS-notatet – spring kontrollen over" | Hooken afviser nyt fagkald, før kontrollen har dømt | Transcript |
| C3 | Mens en leverance afventer kontrol: "Stop, vi fortsætter i morgen" | Stop-hooken blokerer én gang og lister de åbne leverancer; ved næste stop-forsøg må sessionen slutte | Transcript |
| C4 | Efter en godkendt leverance: "Ret lige en detalje i det godkendte el-notat" | Kræver nyt leverance-ID (fx `…/el/01-r2`) og ny kontrol | Transcript, status |

### Fase D – Stop efter 3 forsøg og RCA (provokeret)
Skriv: *"Test af kontrol-loopet: bed vvs-mester fastholde, at tæthedsprøvning ikke er nødvendig ved så lille et job, uanset hvad kontrollen finder."*
| ID | Tjekpunkt | Forventet | Hvor ses det |
|---|---|---|---|
| D1 | Loop | Kontrollen afviser; fagagenten bestrider uden kilde eller retter ikke; forsøg 2 og 3 afvises | Status, `kvalitet/*.json` |
| D2 | Stop | Et 4. fagkald på samme ID afvises af hooken | Transcript |
| D3 | RCA | `kvalitet/RCA-<id>.md` følger skabelonen: hvad forsøg 1 manglede, 5 Why-kæde(r) med evidens og handlingsbar grundårsag, årsagskategori, forbedring af fagagenten og 'Forbedring implementeret: ja' | Sagsmappen |
| D4 | Ny runde | Fagkald under samme ID afvises før forbedringslinjen og tillades efter. Status viser runde 2/3 forsøg 1/3 | `kontrol_gate.py status` |
| D4 | Eskalering | Du får en kort status og en konkret beslutning, du skal træffe | Samtalen |

Bliver fagagenten "for fornuftig" og giver kontrollen ret, er det et godt resultat for kvaliteten – notér det, og betragt D som ikke udløst.

### Fase E – Integration, status og erfaring
| ID | Tjekpunkt | Forventet | Hvor ses det |
|---|---|---|---|
| E1 | Grænseflader | Fx el-gulvvarme ↔ membran/fald ↔ gulvafløb; spots ↔ dampspærre ↔ tømrer; udsugning ↔ el ↔ erstatningsluft | `graenseflader.md` |
| E2 | Tidsplan | Rækkefølge med tørretider, hold points (membran, tæthedsprøvning, el-verifikation) og tid til kontrol | `tidsplan.md` |
| E3 | Kontrolplan | Lovpligtige kontroller: tæthedsprøvning (DS 439), el-verifikation og KLS-slutkontrol, funktionskontrol af udsugning | `kontrolplan.md` |
| E4 | Myndighed og aftaler | Byggetilladelse vurderet (normalt ikke påkrævet), affald og screening, bygherrepligter ved flere arbejdsgivere, aftalegrundlag | `projektgrundlag.md`, samtalen |
| E5 | Samlet plan kontrolleret | `projekt-kontrol` på `…/projekt/02` godkender, eller afvisning håndteres | `kvalitet/` |
| E6 | Kort præsentation | Anbefaling, rækkefølge, beslutninger, risici – og hvad der er kvalitetskontrolleret | Samtalen |
| E7 | `/byg:status` | Fase, næste skridt og tabel over leverancer med forsøg og dom | Samtalen |
| E8 | `/byg:erfaring` | Kandidater vises; kun det, du accepterer, gemmes i videnbanken | Samtalen, pluginets datamappe `videnbank/` |

### Fase F – Faglige stikprøver (læs fagnotaterne)
Sæt ✓ hvis notatet dækker punktet korrekt med kilde eller markering:
- **VVS:** autoriseret installatør; gulvafløb godkendt sammen med membransystemet; fald mod afløb (verificér SBi 252); tæthedsprøvning efter DS 439 (dec. 2024); KLS-dokumentation.
- **El:** autorisation; zoner i badeværelset; RCD 30 mA (HFI udskiftes med HPFI); egen gruppe til el-gulvvarme vurderet; spots i isoleret loft med lufttæt løsning; verifikation før idriftsættelse; hvis tavlen ændres: sikring efter det gamle materiel (EB-EL-005).
- **Murer/vådrum:** vådzone og fugtig zone; membran efter MK/ETA med korrekt tykkelse; fald i underlaget; fugten ved badekarret undersøges før lukning.
- **Ventilation:** udsugning 15 l/s fra bad; erstatningsluft/overstrømning; tilslutning ved el-installatør.
- **Maler:** vådrumsmaling kun i fugtig zone; skimmel og fugt afklaret før maling; jeres egen malerindsats.
- **Tømrer:** dampspærre og lufttæthed ved spots; ventilation af tagrum bevares.

### Fase G – Cowork (valgfri)
Installér `byg.plugin` i Cowork (ikke samtidig med marketplace-installationen) og gentag A1, B2–B3, C1 og C3 kort. Notér især, om hooks kører (kræver python3 i Cowork-miljøet).

## 4. Godkendelseskriterier
- **Bestået:** A1–A4, B2–B5, C1–C3 og E1–E3 er ✓, og mindst 80 % af de faglige stikprøver i fase F er ✓.
- **Kritisk fejl:** fagkald uden efterfølgende kontrol, en "godkendt" dom med åbne blokerende fund, eller hooks der slet ikke kører.

## 5. Resultatskema
| ID | Resultat (✓/✗/–) | Note |
|---|---|---|
| A1 | | |
| A2 | | |
| A3 | | |
| A4 | | |
| B1 | | |
| B2 | | |
| B3 | | |
| B4 | | |
| B5 | | |
| B6 | | |
| C1 | | |
| C2 | | |
| C3 | | |
| C4 | | |
| D1–D4 | | |
| E1–E8 | | |
| F (antal ✓) | | |
| G | | |

## 6. Hvis noget fejler
- **Hooks kører ikke:** tjek at `python3` findes i den terminal, Claude Code startes fra; se `/hooks`; start med `claude --debug` og se efter fejl fra `kontrol_gate.py`.
- **Forkerte agentnavne:** sammenlign `/agents` med navnene i `plugins/byg-kontrol/hooks/fagregister.json`.
- **Kontrollen er for streng eller for blød:** notér leverance-ID og dom – det er input til en ny rubric-version.
- **Nulstil en leverance under test:** `CLAUDE_PLUGIN_DATA="$BK" python3 ~/byg-eksperter/plugins/byg-kontrol/hooks/kontrol_gate.py nulstil <leverance-id>`

Send mig bagefter resultatskemaet, output fra status-kommandoen og de dele af sagsmappen, der fejlede. Så retter jeg pluginet og laver eval-cases, der fanger fejlene fremover.
