---
name: kvalitetskontrol
description: >-
  Protokol for uafhængig kvalitetskontrol af byg-leverancer: leverance-ID, kald af
  fagets kontrolagent, håndtering af dommen, retur til fagagenten, højst 3 forsøg pr. runde,
  root cause-analyse og forbedring af fagagenten ved stop og højst 3 runder. Brug ALTID, når en byg-fagagent (vvs-mester,
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
| projekt | hovedtråden (projektlederen) | `projekt-kontrol` |

Brug det fulde navn fra din agentliste: `byg-vvs:vvs-mester` og `byg-kontrol:vvs-kontrol` ved installation fra marketplacet, `byg:vvs-mester` og `byg:vvs-kontrol` ved den samlede Cowork-pakke.

## 1. Leverance-ID
- Format `<sag-id>/<fag-id>/<nr>`: sag-id = sagsmappens navn (fx `2025-03-14-bad-1970`), nr = 01, 02 … pr. opgave til faget.
- Første linje i hver prompt til fag- og kontrolagent: `LEVERANCE: <id>`.
- Ændring af en godkendt leverance: nyt ID med suffiks (`…/vvs/01-r2`).
- Enkeltstående spørgsmål uden sag: opret først `byg-sager/<ÅÅÅÅ-MM-DD>-<emne>/` med en kort `projektgrundlag.md`.
- Review af eksternt materiale: `LEVERANCE: ekstern/<emne>` (ingen loop – dommen er rådgivende).

## 2. Loopet
1. **Fagkald (forsøg n):** LEVERANCE, opgaven, sagsmappen og stien til notatet (`<sagsmappe>/fagnotater/<fag-id>.md`).
2. **Kontrolkald:** brug skabelonen i afsnit 3. Giv kun leverancen, projektgrundlaget, relevante andre fagnotater og tidligere domme – aldrig fagagentens ræsonnement eller dit eget forsvar for løsningen.
3. **Dom:** hooken gemmer JSON-dommen i `<sagsmappe>/kvalitet/`. Tilføj en linje i `<sagsmappe>/kvalitet/kontrollog.md`: dato · leverance · forsøg · dom · åbne fund (kritisk/væsentlig/mindre).
4. **Godkendt:** leverancen må bruges. **Afvist:** send fundene ordret retur til fagagenten (afsnit 4) som forsøg n+1.
5. **Fund der kræver brugeren** ("afklar med bruger" eller `eskaler: true`): stop loopet og spørg brugeren (AskUserQuestion, hvis tilgængelig). Svaret skrives ind i projektgrundlaget, derefter fortsætter loopet.
6. **Højst 3 forsøg pr. runde, højst 3 runder.** Afvises 3. forsøg i en runde:
   1. **Stop runden.**
   2. **Root cause-analyse:** skriv RCA'en efter `${CLAUDE_PLUGIN_ROOT}/skills/kontrol-viden/references/rca-skabelon.md` til `<sagsmappe>/kvalitet/RCA-<leverance-id med / erstattet af __>.md`. Fra runde 2 får filnavnet `__runde-<n>`. Analysen undersøger, **hvorfor fagagenten ikke kunne levere korrekt i første forsøg**, med **5 Why-metoden**: mindst én kæde med fem hvorfor-niveauer, evidens til hvert svar og en handlingsbar grundårsag (skabelonens afsnit 3).
   3. **Forbedr fagagenten:**
      - Skriv læringen i agentens egen hukommelse (`~/.claude/agent-memory/<plugin>-<agent>/`, med en linje i dens `MEMORY.md`), så den virker i næste runde.
      - Skriv den samtidig generaliseret i byg-eksperter-repoet (agentprompt eller videnbase), med commit og versionsløft.
      - Skriv `Forbedring implementeret: ja` i RCA'en.
   4. **Ny runde:** send et nyt fagkald under **samme leverance-ID**. Hooken starter runde n+1 med forsøg 1. Prompten indeholder RCA-stien, den oprindelige opgave og de seneste fund, og fagagenten løser opgaven forfra.
   5. **Efter runde 3:** eskalér til brugeren med et konkret beslutningsbehov. Fortsæt kun efter brugerens beslutning og under et nyt leverance-ID.

   Fortæl brugeren kort om hver RCA og forbedring, men start den nye runde uden at vente på svar. Læg også læringen i forankringskøen (`/byg:erfaring`).
7. **Parallelle fag:** fagkald må køre parallelt; kontrollér hver leverance, så snart den er klar.
8. **Sidste forsøg (3 af 3):** send kun de blokerende fund (kritisk/væsentlig) og de mindre fund, der står i dommen, retur. Kontrollens usikkerheder og bemærkninger uden fund-ID (fx om den samlede budgetramme) må ikke udvide leverancen i sidste forsøg – flyt dem til projektlederens integration.
9. **Koordineringsbeslutninger undervejs:** en beslutning, der berører flere fag, skrives i beslutningsloggen og gives med i alle berørte fags næste fagkald eller retur – ikke kun til det fag, der udløste den.
9b. **Returer til fag, der afhænger af hinanden, i rækkefølge:** Deler to fag en snitflade eller henviser til hinandens hold points, afgør projektlederen konflikten først (grænsefladeregistret). Derefter rettes ejeren af snitfladen før det fag, der henviser. Uafhængige fag rettes parallelt.
10. **Baggrundsagenter:** kører kontrolagenten i baggrunden, kan dens rapport nå frem, før hooken har registreret dommen (hooken sender først en dom uden JSON retur én gang). Vent, til leverancen ikke længere står som `under_kontrol` i `kontrol_gate.py status`, før næste fagkald – ellers afviser hooken kaldet. Agentens rapport når ofte frem 20–60 sekunder før hooken har registreret dommen. Tjek derfor status, før du handler på en dom. Kør helst kontrolkald i forgrunden.
11. **Retur og genoptagelse:** Send altid fundene retur til fagagenten med et nyt kald i Agent-værktøjet (skabelonen i afsnit 4). Genoptager du fagagenten med SendMessage, registrerer hooken ikke forsøget. Er en dom fra en baggrundskørsel ikke registreret, må kontrolagenten gerne genoptages, så den gentager JSON-dommen, men kun mens leverancen står som `under_kontrol`. Hooken ignorerer domme, der er gentaget eller forældede (status er ikke `under_kontrol`, eller dommens `forsoeg` passer ikke), så de ikke tæller som et nyt forsøg.

## 3. Skabelon – kontrolkald
```
LEVERANCE: <id>
Runde: <r> af 3 · Forsøg: <n> af 3
FASE: <0-4> · KONTROLNIVEAU: <let|fuld>
DESIGNGRUNDLAG: <kun for projektleverancer i fase 3+: godkendte fagleverance-ID'er>
Opgave: <den oprindelige opgave til fagagenten, ordret>
Leverance: <sti til fagnotat>
Projektgrundlag: <sti>
Relevante andre fagnotater: <stier eller "ingen">
Tidligere domme: <stier eller "ingen">
Sagsmappe: <sti>
Udfør et review på det angivne kontrolniveau efter din kontrolprotokol (forsøg 1: fuldt review; forsøg 2–3: kun lukning af fund og regressioner i ændrede afsnit), og afslut med JSON-dommen.
```
- **FASE og KONTROLNIVEAU** følger `faser-og-gates.md` i projektlederens skill. `fuld` gælder sikkerhedskritiske fag i fase 2 og den samlede plan i fase 3. Ellers er niveauet `let`.
- **Projektkontrol** kræver `FASE:`. I fase 3+ kræver den også `DESIGNGRUNDLAG:` med godkendte fagleverancer (hooken håndhæver det).

## 4. Skabelon – retur til fagagent
```
LEVERANCE: <id>
Forsøg: <n+1> af 3 – leverancen blev afvist af kvalitetskontrollen.
Dom: <sti til dommen>
Fund der skal adresseres (ordret): <F1 · klasse · påstand · krav · handling>, …
Instruks: Ret **kun de berørte afsnit** i <sti til notat> med Edit. Skriv ikke notatet om. Adressér hvert fund-ID i en kort tabel under "Kontrolrespons" (lukket eller bestridt med kilde). Kør afleveringstjekket på de ændrede afsnit. Ændr ikke andet uden at notere det. Returnér kort resumé.
```

## 4b. Skabelon – ny runde efter RCA
```
LEVERANCE: <samme id>
Runde: <n+1> af 3 · Forsøg: 1 af 3 – ny runde efter root cause-analyse.
RCA: <sti til RCA-filen> (læs afsnit 2 "Hvad forsøg 1 manglede" og afsnit 6 "Forbedring af fagagenten")
Læs din opdaterede hukommelse, før du går i gang.
Opgave: <den oprindelige opgave, ordret>
Seneste dom: <sti>
Instruks: Løs opgaven forfra med den nye læring, og skriv en ny version af <sti til notat>. Vis under "Kontrolrespons (runde <n+1>)", hvordan læringen og hvert åbent fund er håndteret. Returnér kort resumé.
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
- Ny fagversion før kontrol, forkert kontrolagent, 4. forsøg i en runde og ændring af en godkendt leverance afvises.
- Projektkontrol uden `FASE:` afvises. En planleverance i fase 3+ afvises, hvis `DESIGNGRUNDLAG` mangler eller indeholder fagleverancer, der ikke er godkendt (fase-gate).
- Et nyt kritisk eller væsentligt fund i forsøg 2–3 uden `nyt_grundlag` sendes retur til kontrolagenten (fund-fastlåsning).
- En ny runde afvises, indtil RCA-filen for runden findes med en 5 Why-kæde (mindst fem nummererede "Hvorfor"-linjer og en "Grundårsag") og linjen `Forbedring implementeret: ja`. En 4. runde afvises altid.
- Ugyldig dom (fx blokerende fund uden kilde eller "godkendt" med åbne fund) sendes retur til kontrolagenten.
- Hovedtråden kan ikke afslutte, mens sessionens leverancer afventer kontrol, er afvist eller mangler RCA (én påmindelse pr. stop).
- Status for alle leverancer: `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/kontrol_gate.py" status`.
