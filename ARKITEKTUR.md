# Arkitektur – byg-eksperter

## Krav → design
| Krav | Design |
|---|---|
| Projektleder som tovholder, der interviewer til projektet er veldefineret | `byg`: projektleder-skill (model-invocable) + agent; interviewblokke A–F og Definition of Ready; projektgrundlaget kontrolleres af `projekt-kontrol` |
| Fagagenter på mesterniveau efter danske standarder | Ét plugin pr. fag: agent (persona, fagområde, kerneprincipper, screening, fejlfinding) + videnbase med normgrundlag markeret V/T med kilde og dato |
| Selvbærende | Hvert fag-plugin virker alene (med `byg-kontrol`); skill-fallback til claude.ai uden subagenter |
| Opbygge viden over tid, forankret til hurtig genbrug | Fire videnlag: kanon, agenthukommelse, videnbank, sagsmappe; `/byg:erfaring` og forankringskø |
| Modsvarende kvalitetskontrolagent pr. fag | `byg-kontrol`: én kontrolagent pr. fag + `projekt-kontrol` |
| Hårdt og kritisk review, adskilt fra den udførende | Egen agent, egen kontrolviden, kun læse-/søgeværktøjer, ingen hukommelse, ingen adgang til fagagentens ræsonnement; efterprøvning mod primærkilder |
| Projektlederen sikrer kontrol af hver leverance og looper til godkendelse | Skill `kvalitetskontrol` + hooks (PreToolUse, SubagentStop, Stop) |
| Maks. 3 forsøg pr. runde, derefter RCA, forbedring af fagagenten og ny runde (maks. 3 runder) | Hook-tilstand pr. leverance-ID med runde og forsøg; 4. forsøg afvises; Stop blokeres, indtil RCA-filen for runden findes; ny runde kræver 'Forbedring implementeret: ja' i RCA'en; 4. runde afvises og eskaleres; RCA-skabelonen fokuserer på, hvorfor forsøg 1 ikke var korrekt |

## Komponenter
```
byg-team ──(dependencies)──► byg, byg-kontrol, byg-vvs, byg-el, byg-murer, byg-ventilation, byg-maler, byg-toemrer
byg ─────────────────────────► byg-kontrol
byg-<fag> ───────────────────► byg-kontrol
```
- **Hovedtråden** (projektlederen eller Claude ved direkte brug) orkestrerer. Fagagenter har ikke Agent-værktøjet og kalder aldrig kontrollen selv.
- **Fagagenter:** `model: opus`, `effort: high`, `memory: user`, værktøjer Read/Write/Edit/Glob/Grep/WebSearch/WebFetch. Fælles protokol indsættes fra `faelles/protokol.md`.
- **Modelvalg (2026-09-26):** Fagagenterne kører på Opus med `effort: high`, fordi et afvist første forsøg koster en hel ekstra fag- og kontrolrunde (målt i en rigtig sag: Sonnet-fagagent 10 min, afvist med 8 væsentlige fund, rettelse 21 min). Kontrolagenterne har eksplicit `effort: high`, fordi Opus 5.5 ellers kører på `medium` som standard. Uafhængigheden sikres af adskilt kontekst, kontrolviden og værktøjer – ikke af modelforskel.
- **Kontrolagenter:** `model: opus`, `effort: high`, `color: red`, værktøjer Read/Glob/Grep/WebSearch/WebFetch, ingen `memory` (som ellers giver Write/Edit). Fælles kontrolprotokol indsættes fra `faelles/kontrolprotokol.md`.

## Kvalitetskontrol-laget
**Leverance-ID** `<sag-id>/<fag-id>/<nr>` binder fagkald, kontrolkald, domme og RCA sammen. Godkendte leverancer ændres kun under nyt ID (`-r2`). `ekstern/<emne>` bruges til rådgivende review af eksternt materiale uden loop.

**Dom** (sidste JSON-blok i kontrolagentens svar): `leverance_id, fag, forsoeg, dom, rubric_version, sagsmappe, fund[id, klasse, status, sted, paastand, krav, kilde, evidens, handling, eskaler], regressioner, efterproevet_mod_primaerkilde, usikkerheder, kontrolsvigt`. Godkendt ⇔ ingen åbne kritiske/væsentlige fund. Blokerende fund kræver krav, kilde og evidens.

**Stabilitet:** rubric fryses ved første runde; runde 2–3 tager stilling til tidligere fund før nye; nye væsentlige fund kun ved ændringer (ellers registreres kontrolsvigt); bestridte kritiske fund eskaleres til brugeren.

**Hooks** (`plugins/byg-kontrol/hooks/kontrol_gate.py`, python3, fail-safe):
| Hændelse | Regel |
|---|---|
| PreToolUse (Agent/Task) | Kræver `LEVERANCE:`; fagkald → "afventer_kontrol"; ny fagversion før dom, forkert kontrolagent, 4. forsøg og ændring af godkendt leverance afvises |
| SubagentStop (kontrolagenter) | Validerer dommen; ugyldig dom sendes retur én gang; opdaterer status (godkendt / afvist / stoppet); gemmer dommen i `<sagsmappe>/kvalitet/` |
| Stop (hovedtråd) | Blokerer én gang, hvis sessionens leverancer afventer kontrol, er afvist eller mangler RCA |

Agentnavne matches på basisnavnet, så både `byg-vvs:vvs-mester` (marketplace) og `byg:vvs-mester` (samlet pakke) virker; fag→kontrol-mapping ligger i `hooks/fagregister.json`.

**Læring:** RCA → forbedring af fagagenten straks (agentens hukommelse) og varigt (repoet: prompt/videnbase, commit og versionsløft) → ny runde. Desuden forankringskø → ny tekst i fagets videnbase, ny `rubric_version` i kontrolviden, præciseret prompt, nyt interviewspørgsmål eller ny eval-case.

## Videnmodel
| Lag | Placering | Livscyklus |
|---|---|---|
| Kanon | `plugins/*/skills/*/references/` | Versioneret i repoet; review før ændring |
| Agenthukommelse | `~/.claude/agent-memory/<agent>/` (memory: user) | Fagagenten kuraterer selv |
| Videnbank | `${CLAUDE_PLUGIN_DATA}/videnbank/` (byg) | Overlever plugin-opdateringer; brugeren accepterer |
| Sagsmappe | `byg-sager/<sag-id>/` i arbejdsmappen | Pr. projekt |

## Dataseparation
Repoet er offentligt. Konkrete sager, brugerens data og hemmeligheder må aldrig komme i det.

| Zone | Hvor | Må indeholde | Må aldrig |
|---|---|---|---|
| **Repo (offentligt)** | Dette repo | Generisk faglig viden, skabeloner, kode og testdata (evals, testadresser, fixtures) | Sager, sag-id'er, tekst fra sagsmapper, ejeroplysninger, hemmeligheder |
| **Brugerdata (lokalt)** | Sagsmapper: `byg-sager/` i brugerens arbejdsmappe · Videnbank: `${CLAUDE_PLUGIN_DATA}/videnbank/` · Agenthukommelse: `~/.claude/agent-memory/` · Kontroltilstand: `${CLAUDE_PLUGIN_DATA}/kontrol/` | Alt om de konkrete sager | Ligge i repoet eller i `${CLAUDE_PLUGIN_ROOT}` |
| **Hemmeligheder (lokalt)** | `~/.config/<plugin>/` (chmod 600) eller miljøvariabler | API-nøgler | Stå i kode, logs, output, sagsmapper, commits eller PR'er |

**Overgangen sag → kanon** er det eneste sted, hvor viden flytter fra brugerdata til repoet. Den sker via forankringskøen (`/byg:erfaring`), og forslaget skal være generaliseret. Det må ikke indeholde sag-id, adresse, navne, firmaer, datoer, beløb eller mål fra sagen, kun den faglige pointe og kilden (norm, RCA-kategori). Sag-id'et står i forankringskøen, som er lokal, ikke i repoet.

**Håndhævelse:** `scripts/tjek_data.py` kører i `valider.py` og som git pre-commit-hook (`git config core.hooksPath scripts/hooks`). Den afviser:
- sagsmapper, sagsfiler, rapporter og PDF'er i repoet
- API-nøgler (den lokale nøgle og generiske mønstre)
- sag-id'er fra den lokale videnbank og termer fra `~/.config/byg-eksperter/private-termer.txt`
- tekstlinjer kopieret fra de sagsmapper, der er registreret i videnbankens `sager.md` (kolonnen Sti) eller i `~/.config/byg-eksperter/sagsmapper.txt`

De lokale kilder findes ikke i CI. Der kører kun strukturtjek og nøglemønstre. Tjek derfor altid lokalt før push.

## Platformnoter (verificeret september 2026, Claude Code 2.1.282)
- Plugin-agenter ignorerer `hooks`, `mcpServers`, `permissionMode` og `initialPrompt` i frontmatter → håndhævelse sker via pluginets `hooks/hooks.json`.
- `memory` på en agent tilføjer automatisk Write/Edit → kontrolagenter har ingen memory.
- Subagenter kan nestes (standard 3 lag); plugin-agenter hedder `<plugin>:<agent>`.
- PreToolUse kan afvise via `permissionDecision: deny`; SubagentStop/Stop kan blokere med `decision: block`; `stop_hook_active` forhindrer uendelige løkker; exit 1 blokerer ikke.
- claude.ai-chat kører hverken subagenter eller hooks; Cowork kører begge (hooks bør testes manuelt).
- Cowork installerer `.plugin`-filer (zip af plugin-mappen) uden afhængighedsopløsning → samlet pakke `byg`.
- Plugins med `bin/` kan ikke bruges i Cowork → ingen `bin/`.

## Begrænsninger og risici
- Normer bag betalingsmur (DS m.fl.) kan ikke efterprøves direkte; kontrollen skal da skrive det under `usikkerheder`.
- Punkter markeret T er ikke verificeret; se "Roadmap".
- Hooks kræver python3; uden python3 er loopet kun instruktionsbaseret.
- Stop-hooken blokerer én gang pr. stop (for at undgå uendelige løkker) – en model kan i princippet afslutte ved andet forsøg.
- Kontrolagentens strenghed skal kalibreres på rigtige sager (afvisningsrate, fund pr. runde, kontrolsvigt).
- Agentkontrol er ikke lovpligtig kontrol og ændrer ikke ansvarsforhold.

## Roadmap
1. Verificér T-punkter (murer: KC-recepter, DS/EN-udgaver, riller, kvartsstøv; tømrer: C18/C24, NTR, vinduesmontage, brand i småhuse; netselskab; skorstensfejer) og markér V med dato.
2. Kør evals for alle plugins og loop-evalen med `byg-team` installeret; tilføj eval-cases fra første RCA'er.
3. Test hooks i Cowork med den samlede pakke.
4. Kalibrér kontrollen: mål afvisningsrate, antal runder og kontrolsvigt pr. fag; justér rubric-versioner.
5. Nye fag via `scripts/nyt_fag.py` (fx kloak, tag, gulv, statik-rådgivning) – altid med kontrolagent.
