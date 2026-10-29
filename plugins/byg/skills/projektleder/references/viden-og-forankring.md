# Viden og forankring

## Fem videnlag – fagviden og sagsviden hver for sig
| Lag | Hvor | Indhold | Levetid | Ændres af |
|---|---|---|---|---|
| 1. Kanon | Fag-pluginenes `references/` og byg-kontrols kontrolviden | Fagviden: normgrundlag, faglig praksis, tjeklister, erfaringsblade, kontrolpunkter | Lang | Review og ny pluginversion |
| 2. Agenthukommelse | Hver fagagents `memory: user`, én mappe pr. fag | Fagviden, der ikke er forankret endnu: erfaringer, produkter, mønstre. Aldrig sagsdata | Lang, til den er forankret | Fagagenten selv |
| 3. Videnbank | `${CLAUDE_PLUGIN_DATA}/videnbank/` | `sager.md` (indeks med sti til sagsmappe og ejendomskort), `erfaringsblade/<fag-id>.md` (lokalt forankrede), `forankringskoe.md` | Lang | Projektlederen efter brugerens accept |
| 4. Ejendomskort | `byg-sager/ejendomme/<ejendom-id>.md` | Sagsviden om huset: faste fakta med kilde og dato, delt i afsnit pr. fag (`sagsmappe.md`) | Lang, så længe huset | Projektlederen |
| 5. Sagsmappe | `byg-sager/<sag-id>/` | Sagsviden om projektet: omfang, beslutninger, leverancer, status | Kort, så længe sagen | Projektlederen og fagene |

Kun indekset (agentens `MEMORY.md`, skill-indgangen) ligger altid i konteksten. Resten læses afsnitsvis efter behov. Hvert fag læser kun sin egen hukommelse og videnbase og kun sit eget afsnit af ejendomskortet. Videnbanken overlever opdateringer af pluginet. Fagagenter kan ikke læse projektlederens datamappe – giv dem de relevante lokale erfaringer i fagforespørgslen.

## Erfaringshøst (`/byg:erfaring`)
**Hvornår:** altid, når en sag eller et delprojekt afsluttes (sidste leverance godkendt og besvaret, eller sagen parkeres), og efter hver RCA. Et spørgsmål via `/byg:spoerg` høstes, når svaret er givet. Skriv datoen i linjen `**Erfaringshøst:**` i `status.md`. `/byg:status` viser sager, der ikke er høstet.
1. Læs `erfaringer.md`, beslutningsloggen, domme og RCA'er i sagen.
2. **Husets fakta → ejendomskortet:** nye eller ændrede fakta fra sagen (målinger, fotos, typeskilte, godkendte fagnotater) føres ind med kilde og dato. Gamle værdier flyttes til "Erstattede oplysninger". Er kortet genereret fra en BIM-hovedmodel, sker det via forslag + `bim.py merge` (se `sagsmappe.md`).
3. Formulér erfaringerne som erfaringsblade: Situation/Problem/Løsning, Grundlag, Gyldighed, Status.
4. Sortér: sagsspecifikt (bliver i sagen) · generaliserbart (→ videnbank) · kanon-kandidat (→ forankringskø med målfil og forslag til ny tekst).
5. Vis kandidaterne for brugeren; gem kun det accepterede.
6. Opdatér `sager.md` i videnbanken (sag-id, sti, emne, fag, resultat, læring i én linje, ejendomskort).

## Læring fra kvalitetskontrol
- Hver RCA implementerer forbedringen i fagagenten med det samme (agentens hukommelse og repoet, RCA-skabelonen afsnit 6). Den giver også mindst ét forslag i forankringskøen efter årsagskategorien (F1–F5, K4, K7 i RCA-skabelonen): nyt interviewspørgsmål, rettelse i fagets videnbase, præcisering i fagagentens prompt, ny rubric-version for kontrollen, markering af emner der kræver normadgang, nyt tværfagligt tjekpunkt – og en ny eval-case.
- Gentagne fund af samme type på tværs af sager er kanon-kandidater, selv uden RCA.

## Forankringskø – forankringskoe.md
| Dato | Kilde (sag/RCA) | Type | Målfil | Forslag | Status (ny/accepteret/afvist/indarbejdet) |
|---|---|---|---|---|---|

Indarbejdelse i kanon sker i repoet (se README.da.md): ret filen, læg en versionsnote i `versionsnoter/`, kør tests og evals. Versionen hæves ved udgivelse på main.

**Anonymisering før kanon (repoet er offentligt):** Kolonnen "Forslag" skrives, så den kan stå i repoet ordret. Den må ikke indeholde sag-id, adresse, navne, firmaer, datoer, beløb, mål eller citater fra sagsmappen. Den indeholder kun den generaliserede faglige pointe og kilden (norm, RCA-kategori). Sagshenvisningen står i kolonnen "Kilde", og den bliver i den lokale kø. Eval-cases, der bygger på en sag, skrives som et nyt, opdigtet scenarie med andre detaljer. `scripts/check_data.py` afviser sag-id'er og tekst kopieret fra registrerede sagsmapper.

## Kvalitet i viden
- Skeln mellem [KRAV], [NORM], [ANVISNING] og [ERFARING]; markér status V/T med dato.
- Ingen persondata i videnbanken ud over sag-id, sti og emne.
- Videnbank, sagsmapper og agenthukommelse ligger kun lokalt og må aldrig kopieres ind i plugin-repoet (se ARKITEKTUR.md, Dataseparation).
- Forældet viden rettes – slettes ikke uden spor: skriv "erstattet af" med dato.
