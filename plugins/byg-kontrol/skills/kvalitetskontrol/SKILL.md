---
name: kvalitetskontrol
description: >-
  Protokol for uafhængig kvalitetskontrol af byg-leverancer: leverance-ID, kald af
  fagets kontrolagent, håndtering af dommen, retur til fagagenten, højst 2 forsøg pr. runde,
  derefter eskalering til brugeren; ny runde med root cause-analyse kun efter brugerens beslutning. Brug ALTID, når en byg-fagagent (vvs-mester,
  el-installatoer, murermester, ventilationsekspert, malermester, toemrermester) skal
  levere eller har leveret, når projektlederens egne leverancer skal kontrolleres, og
  når eksternt materiale (tilbud, rapport, tegning) skal have et uafhængigt review.
---

# Kvalitetskontrol – orkestratorens protokol

Gælder for hovedtråden: projektlederen – eller Claude, når et fag bruges direkte. Hooks i byg-kontrol håndhæver reglerne i Claude Code og Cowork; følg dem også, hvis hooks ikke kører.

## Agentpar
| Fag | Fagagent | Kontrolagent |
|---|---|---|
| vvs | `vvs-mester` | `vvs-kontrol` |
| el | `el-installatoer` | `el-kontrol` |
| murer | `murermester` | `murer-kontrol` |
| ventilation | `ventilationsekspert` | `ventilation-kontrol` |
| maler | `malermester` | `maler-kontrol` |
| toemrer | `toemrermester` | `toemrer-kontrol` |
| bim | `bim-modelloer` | `bim-kontrol` |
| statik | `statiker` | `statik-kontrol` |
| arkitekt | `arkitekt` | `arkitekt-kontrol` |
| anlaeg | `anlaegsgartner` | `anlaeg-kontrol` |
| projekt | hovedtråden (projektlederen) | `projekt-kontrol` |

Brug det fulde navn fra din agentliste: `byg-vvs:vvs-mester` og `byg-kontrol:vvs-kontrol` ved installation fra marketplacet, `byg:vvs-mester` og `byg:vvs-kontrol` ved den samlede Cowork-pakke.

**BIM:** før kontrolkaldet kører hovedtråden selv den deterministiske kontrol (`bim.py check <ifc> --draw --out <sagsmappe>/kvalitet/bim-<nr>-tjek`) og giver rapporten til `bim-kontrol`. Ved import af tegninger kommer først sammenligningsloopet med hjælpeagenten `bim-sammenligner` (skill `tegningsimport`, højst 3 sammenligninger), derefter kontrollen. Rettelser efter en sammenligning bruger ikke af kontrolforsøgene.

## 1. Leverance-ID
- Format `<sag-id>/<fag-id>/<nr>`: sag-id = sagsmappens navn (fx `2025-03-14-bad-1970`), nr = 01, 02 … pr. opgave til faget.
- Første linje i hver prompt til fag- og kontrolagent: `LEVERANCE: <id>`.
- Ændring af en godkendt leverance: nyt ID med suffiks (`…/vvs/01-r2`).
- Enkeltstående spørgsmål uden sag: opret **ikke** en mappe i `byg-sager/`; brug `~/byg-tmp/<ÅÅÅÅ-MM-DD>-<emne>/` med en kort `projektgrundlag.md` (midlertidigt – det godkendte svar løftes ind i hovedsagen, hvis det skal gemmes).
- Branch-sag (`<hovedsag>--<emne>/`): sag-id = branch-mappens navn; leverancen flettes ind i hovedsagen ved godkendelse.
- Review af eksternt materiale: `LEVERANCE: ekstern/<emne>` (ingen loop – dommen er rådgivende).

## 2. Loopet
1. **Fagkald (forsøg n):** LEVERANCE, opgaven, sagsmappen og stien til notatet (`<sagsmappe>/fagnotater/<fag-id>.md`). Fagagenten skriver kun sine egne filer; ændringer i grænseflader, risici, kontrolplan og ejendomskort kommer som forslag (`<sagsmappe>/forslag/<fag-id>-<nr>__<mål>.md`) og står under "Forslag" i rapporten.
2. **Kontrolkald:** brug skabelonen i afsnit 3. Giv kun leverancen, projektgrundlaget, ejendomskortet, relevante andre fagnotater og tidligere domme – aldrig fagagentens ræsonnement eller dit eget forsvar for løsningen.
3. **Dom:** hooken gemmer JSON-dommen i `<sagsmappe>/kvalitet/`, og ved **godkendt** fletter den leverancens forslag ind i målfilerne (afsnit 8). Tilføj en linje i `<sagsmappe>/kvalitet/kontrollog.md`: dato · leverance · forsøg · dom · åbne fund (kritisk/væsentlig/mindre) · ikke kontrolleret (dommens `ikke_kontrolleret`, ellers "–"). En godkendelse dækker kun det kontrollerede: bygger du videre på en del, der står under `ikke_kontrolleret`, så sig det til brugeren, eller bestil en kontrol af netop den del.
4. **Godkendt:** leverancen må bruges. **Afvist:** send **kun de blokerende fund** (kritisk og væsentlig) ordret retur til fagagenten (afsnit 4) som forsøg n+1. Mindre fund sendes ikke retur. De står i dommen og tages kun med, hvis notatet alligevel revideres senere. En retur må ikke indeholde nye ønsker eller opgaver; de bliver en ny leverance med nyt ID.
5. **Fund der kræver brugeren** ("afklar med bruger" eller `eskaler: true`): stop loopet og spørg brugeren (AskUserQuestion, hvis tilgængelig). Svaret skrives ind i projektgrundlaget, derefter fortsætter loopet.
   **Spørgsmål i `afklar_med_bruger`** blokerer ikke: loopet fortsætter. Saml dem fra sagens domme, og stil dem samlet til brugeren ved næste naturlige stop (fx ved gaten), de vigtigste først. Svarene skrives ind i projektgrundlaget.
6. **Højst 2 forsøg pr. runde, højst 2 runder.** Afvises 2. forsøg i en runde:
   1. **Stop runden, og eskalér til brugeren.** Vis de åbne blokerende fund kort (én linje hver), og spørg, om leverancen skal (a) bruges med fundene som åbne antagelser eller hold points, (b) have en ny runde – brugeren skriver selv `Ny runde <leverance-id>` – eller (c) omformuleres som en ny, mindre opgave under et nyt leverance-ID. Start ingen ny runde, og skriv ingen RCA, før brugeren har valgt (b). Hooken håndhæver det.
   2. **Root cause-analyse (kun ved (b)):** skriv RCA'en efter `${CLAUDE_PLUGIN_ROOT}/skills/kontrol-viden/references/rca-skabelon.md` til `<sagsmappe>/kvalitet/RCA-<leverance-id med / erstattet af __>.md`. Fra runde 2 får filnavnet `__runde-<n>`. Analysen undersøger, **hvorfor fagagenten ikke kunne levere korrekt i første forsøg**, med **5 Why-metoden**: mindst én kæde med fem hvorfor-niveauer, evidens til hvert svar og en handlingsbar grundårsag (skabelonens afsnit 3).
   3. **Forbedr fagagenten:**
      - Skriv læringen i agentens egen hukommelse (`~/.claude/agent-memory/<plugin>-<agent>/`, med en linje i dens `MEMORY.md`), så den virker i næste runde.
      - Skriv den samtidig generaliseret i Engineer Any House-repoet (agentprompt eller videnbase), med commit og en versionsnote (`versionsnoter/`, se README).
      - Skriv `Forbedring implementeret: ja` i RCA'en.
   4. **Ny runde:** send et nyt fagkald under **samme leverance-ID**. Hooken starter runde n+1 med forsøg 1. Prompten indeholder RCA-stien, den oprindelige opgave og de seneste fund. Fagagenten retter sit notat ud fra læringen i stedet for at starte helt forfra.
   5. **Efter runde 2:** eskalér igen. Fortsæt kun efter brugerens beslutning og under et nyt leverance-ID.

   Fortæl brugeren kort om RCA'en og forbedringen. Læg også læringen i forankringskøen (`/byg:erfaring`).
7. **Parallelle fag i forgrunden:** fag- og kontrolkald køres i forgrunden. Uafhængige kald sendes parallelt som flere Agent-kald i samme besked, og hver leverance kontrolleres, så snart den er klar. Brugerens beskeder venter i køen imens.
8. **Kontrollens bemærkninger uden fund-ID** (usikkerheder, fx om den samlede budgetramme) udvider ikke leverancen i en retur. Flyt dem til projektlederens integration.
9. **Koordineringsbeslutninger undervejs:** en beslutning, der berører flere fag, skrives i beslutningsloggen og gives med i alle berørte fags næste fagkald eller retur – ikke kun til det fag, der udløste den.
9b. **Returer til fag, der afhænger af hinanden, i rækkefølge:** Deler to fag en snitflade eller henviser til hinandens hold points, afgør projektlederen konflikten først (grænsefladeregistret). Derefter rettes ejeren af snitfladen før det fag, der henviser. Uafhængige fag rettes parallelt.
10. **Ingen baggrundskontrol:** kør ikke kontrolkald i baggrunden. Agentens rapport når frem 20–60 sekunder før hooken har registreret dommen, og venten på hooken koster et statuskald i hovedtråden hver gang. Er en kontrol alligevel kørt i baggrunden, og afviser hooken næste fagkald med "er ikke kontrolleret endnu", så vent på næste hændelse i stedet for at tjekke status gentagne gange.
11. **Retur og genoptagelse:** Send altid de blokerende fund retur til fagagenten med et nyt kald i Agent-værktøjet (skabelonen i afsnit 4). Genoptager du fagagenten med SendMessage, registrerer hooken ikke forsøget. Er en dom fra en baggrundskørsel ikke registreret, må kontrolagenten gerne genoptages, så den gentager JSON-dommen, men kun mens leverancen står som `under_kontrol`. Hooken ignorerer domme, der er gentaget eller forældede (status er ikke `under_kontrol`, eller dommens `forsoeg` passer ikke), så de ikke tæller som et nyt forsøg.

## 3. Skabelon – kontrolkald
```
LEVERANCE: <id>
Runde: <r> af 2 · Forsøg: <n> af 2
FASE: <0-4> · KONTROLNIVEAU: <let|fuld|stikprøve|værktøj>
DESIGNGRUNDLAG: <kun for projektleverancer i fase 3+: godkendte fagleverance-ID'er>
Opgave: <den oprindelige opgave til fagagenten, ordret>
Leverance: <sti til fagnotat>
Forslag: <stier fra fagagentens rapport, eller "ingen">
Ændringer: <forsøg 2 og senere og rettelser: <sagsmappe>/kvalitet/<leverance-id med / erstattet af __>__aendringer.diff, ellers "ingen">
Projektgrundlag: <sti>
Ejendomskort: <sti eller "ingen">
Relevante andre fagnotater: <stier eller "ingen">
Tidligere domme: <stier eller "ingen">
Sagsmappe: <sti>
Udfør et review på det angivne kontrolniveau efter din kontrolprotokol (forsøg 1: fuldt review; forsøg 2 og senere: kun lukning af fund og regressioner i ændrede afsnit), og afslut med JSON-dommen.
```
- **FASE og KONTROLNIVEAU** følger `faser-og-gates.md` i projektlederens skill. Niveauet sættes efter **opgavens risiko**, ikke kun efter faget. `fuld` gælder design i fase 2, der fastlægger eller ændrer en sikkerhedsfunktion i et sikkerhedskritisk fag, og den samlede plan i fase 3. Ellers er niveauet `let`, også for indkøb, priser, sortiment, materialelister og styklister til et godkendt design. `værktøj` findes kun for bim (fagregistret `vaerktoejskontrol`): ren geometri godkendes af sammenligneren og `bim.py check` uden kontrolagent (skill `tegningsimport`). `stikprøve` bruges kun til enkeltstående fagspørgsmål uden sag (ingen `FASE:`) uden sikkerhedsfunktion og aldrig for el og statik: niveauet skrives i **fagkaldet**, og hooken udtager ca. hver tredje. Afviser hooken kontrolkaldet med "ikke udtaget", er svaret afleveret uden kontrol og skal markeres "Ikke kvalitetskontrolleret (stikprøve, ikke udtaget)".
- **Model:** kontrolagenterne kører på Sonnet. Ved `KONTROLNIVEAU: fuld` kaldes de med `model: "opus"` i Agent-kaldet (hooken afviser ellers kaldet). `bim-sammenligner` kører på Sonnet.
- **Giv kun det nødvendige med:** henvis til de relevante afsnit i andre fagnotater (fil og afsnit) frem for hele filer.
- **Projektkontrol** kræver `FASE:`. I fase 3+ kræver den også `DESIGNGRUNDLAG:` med godkendte fagleverancer (hooken håndhæver det).

## 4. Skabelon – retur til fagagent
```
LEVERANCE: <id>
Forsøg: <n+1> af 2 – leverancen blev afvist af kvalitetskontrollen.
Dom: <sti til dommen>
Blokerende fund der skal adresseres (ordret): <F1 · klasse · påstand · krav · handling>, …
Instruks: Ret **kun de berørte afsnit** i <sti til notat> med Edit, og saml rettelserne i få Edit-kald. Skriv ikke notatet om, og læs ikke kildegrundlaget igen, medmindre et fund kræver det. Mindre fund i dommen skal ikke rettes. Adressér hvert fund-ID i en kort tabel under "Kontrolrespons" (lukket eller bestridt med kilde). Kør afleveringstjekket på de ændrede afsnit. Ændr ikke andet uden at notere det. Returnér kort resumé.
```
Kun kritiske og væsentlige fund. Ingen mindre fund, ingen nye ønsker og ingen nye opgaver – de kræver et nyt leverance-ID.

## 4b. Skabelon – ny runde efter RCA
```
LEVERANCE: <samme id>
Runde: <n+1> af 2 · Forsøg: 1 af 2 – ny runde efter root cause-analyse (godkendt af brugeren).
RCA: <sti til RCA-filen> (læs afsnit 2 "Hvad forsøg 1 manglede" og afsnit 6 "Forbedring af fagagenten")
Læs din opdaterede hukommelse, før du går i gang.
Opgave: <den oprindelige opgave, ordret>
Seneste dom: <sti>
Instruks: Ret <sti til notat> med den nye læring. Skriv kun de afsnit om, som fundene og læringen berører. Vis under "Kontrolrespons (runde <n+1>)", hvordan læringen og hvert åbent fund er håndteret. Returnér kort resumé.
```

## 5. Projektlederens egne leverancer
Projektgrundlaget (efter Definition of Ready), koordineringsplanen med grænseflader, tidsplan og kontrolplan samt den samlede anbefaling til brugeren kontrolleres af `projekt-kontrol` i samme loop med `LEVERANCE: <sag-id>/projekt/<nr>`. Her tælles et forsøg ved hvert kontrolkald.

## 6. Når uafhængig kontrol ikke er mulig
Kan Agent-værktøjet ikke bruges (fx i claude.ai-chat), så sig tydeligt, at uafhængig kvalitetskontrol kræver Claude Code eller Cowork. Lever svaret under overskriften **"IKKE UAFHÆNGIGT KVALITETSKONTROLLERET"** efter en selvkontrol mod `${CLAUDE_PLUGIN_ROOT}/skills/kontrol-viden/references/fag/<fag>.md` – og kald det aldrig uafhængig kontrol.

## 7. Det håndhæver hooks
- Fag- og kontrolkald uden `LEVERANCE:` afvises med besked om, hvad der mangler.
- **Manuel gate G2:** projektkontrol med `FASE: 3+` og fagkald med `FASE: 3+` afvises, indtil brugeren selv har skrevet `Godkend G2 <sag-id>`. DESIGNGRUNDLAG skal ligge inden for det design, brugeren godkendte.
- Et fagkald står som `fagkald_igang`, indtil fagagenten afleverer. Imens blokerer stop-hooken ikke (først efter 90 min uden aflevering). Et nyt fagkald på en leverance i `fagkald_igang` (fx efter et afbrudt kald) er et genforsøg og tæller ikke som nyt forsøg.
- En kontrolagents dom findes også i dens hand-back-rapport (transkriptet).
- Godkendte leverancer beskyttes: stien fra kontrolkaldets linje `Leverance: <sti>` huskes. Write/Edit på filen afvises for subagenter og giver en advarsel i hovedtråden. Brug nyt leverance-ID via ændringsstyring.
- Ny fagversion før kontrol, forkert kontrolagent, 3. forsøg i en runde og ændring af en godkendt leverance afvises.
- Kontrolkald med `KONTROLNIVEAU: fuld` uden `model: "opus"` afvises.
- **Workflows:** i byg-sager afvises Workflow-værktøjet, medmindre brugerens seneste besked indeholder ordet "workflow".
- Projektkontrol uden `FASE:` afvises. En planleverance i fase 3+ afvises, hvis `DESIGNGRUNDLAG` mangler eller indeholder fagleverancer, der ikke er godkendt (fase-gate).
- Et nyt kritisk eller væsentligt fund i forsøg 2 og senere uden `nyt_grundlag` sendes retur til kontrolagenten (fund-fastlåsning).
- En ny runde afvises, indtil brugeren selv har skrevet `Ny runde <leverance-id>`, og RCA-filen for runden findes med en 5 Why-kæde (mindst fem nummererede "Hvorfor"-linjer og en "Grundårsag") og linjen `Forbedring implementeret: ja`. En 3. runde afvises altid.
- Ugyldig dom (fx blokerende fund uden kilde eller "godkendt" med åbne fund) sendes retur til kontrolagenten.
- Hovedtråden kan ikke afslutte, mens sessionens leverancer afventer kontrol eller er afvist (én påmindelse pr. stop). En stoppet leverance giver én påmindelse om at eskalere til brugeren. RCA kræves kun, når brugeren har bedt om en ny runde.
- **Én skriver pr. fil:** en fagagents Write/Edit i `byg-sager/` uden for dens egne filer afvises (afsnit 8).
- Hovedtråden kan heller ikke afslutte, mens et godkendt forslag ikke kunne flettes (konflikt), før konflikten er løst.
- Status for alle leverancer: `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/review_gate.py" status`.

## 8. Én skriver pr. fil, forslag og revisionsstyring
Fag- og kontrolkald kører parallelt (afsnit 2, punkt 7). For at de ikke skriver oven i hinanden, har hver fil i sagen én ejer:

| Fil | Ejer | Andre bidrager med |
|---|---|---|
| `fagnotater/<fag-id>.md`, `fagnotater/<fag-id>-*.md`, `bilag/<fag-id>/`, fagets egne mapper (`bim/forslag/`, `bim/kilder/`, `fem/`) | faget | rapporten |
| `graenseflader.md`, `risici.md`, `kontrolplan.md`, ejendomskortet | projektlederen | forslag `forslag/<fag-id>-<nr>__<mål>.md` |
| alt andet (projektgrundlag, beslutningslog, ændringer, status, budget, tidsplan, `kvalitet/kontrollog.md`) | projektlederen | rapporten |
| `bim/model.yaml` (BIM-hovedmodellen) | `bim.py merge` | BIM-forslag (skill `tegningsimport`) |

- **Forslag flettes ved godkendelse.** Hooken gemmer målfilerne som basis, når fagkaldet starter, og fletter det ind, når kontrollen godkender leverancen: rækker med samme ID erstattes, nye ID'er tilføjes sidst i afsnittets tabel, og en ændret værdi i ejendomskortet flyttes til "Erstattede oplysninger". Forslaget flyttes til `forslag/flettet/` og logges i `forslag/flettelog.md`. Et afvist forslag bliver liggende.
- **Konflikt:** har du ændret de samme rækker, siden forslaget blev skrevet, flettes intet, og Stop-hooken viser konflikten. Du ejer målfilen: ret den selv (eller forslaget), og flet med `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/review_gate.py" merge <forslag> [--dry-run] [--force]` eller i hånden. Flyt så forslaget til `forslag/flettet/`, eller slet det.
- **Parallelle returer:** returer til fag, der berører samme rækker, sendes stadig i rækkefølge (afsnit 2, punkt 9b). Forslag gør det kun sikkert at køre fag parallelt, der skriver forskellige rækker.
- **Revisionsstyring:** `byg-sager/` er et lokalt git-repo, som hooken opretter og committer til: hver fagaflevering (kun fagets egne filer), hver dom og fletning og dine egne ændringer, når din tur slutter. Beskeden starter med leverance-ID'et, så `git -C byg-sager log --oneline -- <fil>` viser, hvem der ændrede hvad. Repoet pushes aldrig (sagerne er brugerdata). Slå det fra med miljøvariablen `BYG_GIT=0`.
- **Ændringer til kontrollen:** når fagagenten afleverer en ny version efter en dom, skriver hooken diffen fra den kontrollerede version til `kvalitet/<leverance-id med / erstattet af __>__aendringer.diff`. Giv stien under "Ændringer" i kontrolkaldet, så forsøg 2 og senere kun ser på det, der faktisk er ændret.
