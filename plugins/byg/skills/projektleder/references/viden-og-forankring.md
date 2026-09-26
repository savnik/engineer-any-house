# Viden og forankring

## Fire videnlag
| Lag | Hvor | Indhold | Ændres af |
|---|---|---|---|
| 1. Kanon | Fag-pluginenes `references/` og byg-kontrols kontrolviden | Normgrundlag, faglig praksis, tjeklister, erfaringsblade, kontrolpunkter | Review og ny pluginversion |
| 2. Agenthukommelse | Hver fagagents `memory: user` | Personlige erfaringer, præferencer, produkter, lokale forhold | Fagagenten selv |
| 3. Videnbank | `${CLAUDE_PLUGIN_DATA}/videnbank/` | `sager.md` (indeks med sti til sagsmappen), `erfaringsblade/<fag-id>.md` (lokalt forankrede), `forankringskoe.md` | Projektlederen efter brugerens accept |
| 4. Sagsmappe | `byg-sager/<sag-id>/` | Alt om den konkrete sag | Projektlederen og fagene |

Videnbanken overlever opdateringer af pluginet. Fagagenter kan ikke læse projektlederens datamappe – giv dem de relevante lokale erfaringer i fagforespørgslen.

## Erfaringshøst (`/byg:erfaring`)
1. Læs `erfaringer.md`, beslutningsloggen, domme og RCA'er i sagen.
2. Formulér kandidater som erfaringsblade: Situation/Problem/Løsning, Grundlag, Gyldighed, Status.
3. Sortér: sagsspecifikt (bliver i sagen) · generaliserbart (→ videnbank) · kanon-kandidat (→ forankringskø med målfil og forslag til ny tekst).
4. Vis kandidaterne for brugeren; gem kun det accepterede.
5. Opdatér `sager.md` i videnbanken (sag-id, sti, emne, fag, resultat, læring i én linje).

## Læring fra kvalitetskontrol
- Hver RCA giver mindst ét forslag i forankringskøen efter årsagskategorien (K1–K7 i RCA-skabelonen): nyt interviewspørgsmål, rettelse i fagets videnbase, præcisering i fagagentens prompt, ny rubric-version for kontrollen, markering af emner der kræver normadgang, nyt tværfagligt tjekpunkt – og en ny eval-case.
- Gentagne fund af samme type på tværs af sager er kanon-kandidater, selv uden RCA.

## Forankringskø – forankringskoe.md
| Dato | Kilde (sag/RCA) | Type | Målfil | Forslag | Status (ny/accepteret/afvist/indarbejdet) |
|---|---|---|---|---|---|

Indarbejdelse i kanon sker i repoet (se README): ret filen, bump versionen, kør tests og evals.

**Anonymisering før kanon (repoet er offentligt):** Kolonnen "Forslag" skrives, så den kan stå i repoet ordret. Den må ikke indeholde sag-id, adresse, navne, firmaer, datoer, beløb, mål eller citater fra sagsmappen. Den indeholder kun den generaliserede faglige pointe og kilden (norm, RCA-kategori). Sagshenvisningen står i kolonnen "Kilde", og den bliver i den lokale kø. Eval-cases, der bygger på en sag, skrives som et nyt, opdigtet scenarie med andre detaljer. `scripts/tjek_data.py` afviser sag-id'er og tekst kopieret fra registrerede sagsmapper.

## Kvalitet i viden
- Skeln mellem [KRAV], [NORM], [ANVISNING] og [ERFARING]; markér status V/T med dato.
- Ingen persondata i videnbanken ud over sag-id, sti og emne.
- Videnbank, sagsmapper og agenthukommelse ligger kun lokalt og må aldrig kopieres ind i plugin-repoet (se ARKITEKTUR.md, Dataseparation).
- Forældet viden rettes – slettes ikke uden spor: skriv "erstattet af" med dato.
