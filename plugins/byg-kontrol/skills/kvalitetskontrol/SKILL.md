---
name: kvalitetskontrol
description: >-
  Protokol for uafhængig kvalitetskontrol af byg-leverancer: leverance-ID, kald af
  fagets kontrolagent, håndtering af dommen, retur til fagagenten, højst 3 forsøg og
  root cause-analyse ved stop. Brug ALTID, når en byg-fagagent (vvs-mester,
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
6. **Højst 3 forsøg.** Afvises 3. forsøg: STOP. Skriv root cause-analysen efter `${CLAUDE_PLUGIN_ROOT}/skills/kontrol-viden/references/rca-skabelon.md` til `<sagsmappe>/kvalitet/RCA-<leverance-id med / erstattet af __>.md`, eskalér til brugeren med konkret beslutningsbehov, og læg læringen i forankringskøen (`/byg:erfaring`). Fortsæt kun efter brugerens beslutning og under et nyt leverance-ID.
7. **Parallelle fag:** fagkald må køre parallelt; kontrollér hver leverance, så snart den er klar.
8. **Sidste forsøg (3 af 3):** send kun de blokerende fund (kritisk/væsentlig) og de mindre fund, der står i dommen, retur. Kontrollens usikkerheder og bemærkninger uden fund-ID (fx om den samlede budgetramme) må ikke udvide leverancen i sidste forsøg – flyt dem til projektlederens integration.
9. **Koordineringsbeslutninger undervejs:** en beslutning, der berører flere fag, skrives i beslutningsloggen og gives med i alle berørte fags næste fagkald eller retur – ikke kun til det fag, der udløste den.
10. **Baggrundsagenter:** kører kontrolagenten i baggrunden, kan dens rapport nå frem, før hooken har registreret dommen (hooken sender først en dom uden JSON retur én gang). Vent, til leverancen ikke længere står som `under_kontrol` i `kontrol_gate.py status`, før næste fagkald – ellers afviser hooken kaldet.
11. **Retur og genoptagelse:** Send altid fundene retur til fagagenten med et nyt kald i Agent-værktøjet (skabelonen i afsnit 4). Genoptager du fagagenten med SendMessage, registrerer hooken ikke forsøget. Er en dom fra en baggrundskørsel ikke registreret, må kontrolagenten gerne genoptages, så den gentager JSON-dommen, men kun mens leverancen står som `under_kontrol`. Hooken ignorerer domme, der er gentaget eller forældede (status er ikke `under_kontrol`, eller dommens `forsoeg` passer ikke), så de ikke tæller som et nyt forsøg.

## 3. Skabelon – kontrolkald
```
LEVERANCE: <id>
Forsøg: <n> af 3
Opgave: <den oprindelige opgave til fagagenten, ordret>
Leverance: <sti til fagnotat>
Projektgrundlag: <sti>
Relevante andre fagnotater: <stier eller "ingen">
Tidligere domme: <stier eller "ingen">
Sagsmappe: <sti>
Udfør et hårdt og kritisk review efter din kontrolprotokol, og afslut med JSON-dommen.
```

## 4. Skabelon – retur til fagagent
```
LEVERANCE: <id>
Forsøg: <n+1> af 3 – leverancen blev afvist af kvalitetskontrollen.
Dom: <sti til dommen>
Fund der skal adresseres (ordret): <F1 · klasse · påstand · krav · handling>, …
Instruks: Opdatér <sti til notat>. Adressér hvert fund-ID under "Kontrolrespons" (lukket eller bestridt med kilde). Ændr ikke andet uden at notere det. Returnér kort resumé.
```

## 5. Projektlederens egne leverancer
Projektgrundlaget (efter Definition of Ready), koordineringsplanen med grænseflader, tidsplan og kontrolplan samt den samlede anbefaling til brugeren kontrolleres af `projekt-kontrol` i samme loop med `LEVERANCE: <sag-id>/projekt/<nr>`. Her tælles et forsøg ved hvert kontrolkald.

## 6. Når uafhængig kontrol ikke er mulig
Kan Agent-værktøjet ikke bruges (fx i claude.ai-chat), så sig tydeligt, at uafhængig kvalitetskontrol kræver Claude Code eller Cowork. Lever svaret under overskriften **"IKKE UAFHÆNGIGT KVALITETSKONTROLLERET"** efter en selvkontrol mod `${CLAUDE_PLUGIN_ROOT}/skills/kontrol-viden/references/fag/<fag>.md` – og kald det aldrig uafhængig kontrol.

## 7. Det håndhæver hooks
- Fag- og kontrolkald uden `LEVERANCE:` afvises med besked om, hvad der mangler.
- Ny fagversion før kontrol, forkert kontrolagent, 4. forsøg og ændring af en godkendt leverance afvises.
- Ugyldig dom (fx blokerende fund uden kilde eller "godkendt" med åbne fund) sendes retur til kontrolagenten.
- Hovedtråden kan ikke afslutte, mens sessionens leverancer afventer kontrol, er afvist eller mangler RCA (én påmindelse pr. stop).
- Status for alle leverancer: `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/kontrol_gate.py" status`.
