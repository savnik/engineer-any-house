# Interview – fra idé til veldefineret projekt

## Principper
- Højst 3–4 spørgsmål pr. runde; brug AskUserQuestion med 2–4 svarmuligheder, når værktøjet findes.
- Spørg ikke om noget, der allerede står i sagsmappen, videnbanken eller samtalen.
- Byg videre på svarene – følg op, hvor der er risiko eller uklarhed.
- Sikkerhed først: akut fare afbryder interviewet (grundregel 7 i SKILL.md).
- Skal et fag afklare noget, før du kan spørge rigtigt (fx om en væg er bærende), så notér det som åbent spørgsmål til fagforespørgslen i stedet for at gætte.

## Blokke
**A – Formål og ønsker:** Hvad skal laves, og hvorfor? Hvad er succes? Skal-krav og ønsker. Stil og kvalitetsniveau.
Spørg tidligt om **adressen**. Er skill `ejendomsdata` (plugin `byg-data`) tilgængelig, så hent offentlige data med `rapport "<adresse>" --ud <sagsmappe>/attachments/ejendomsdata --pdf`, før blok B og E: opførelsesår, materialer, varmeinstallation, lokalplan, fredning og bevaring, jordforurening og energimærke. Spørg så kun om det, registrene ikke svarer på, og bekræft BBR-oplysninger med brugeren – BBR er selvanmeldt og ofte forældet.

**B – Bygningen:** Type (parcel-, række-, etage- eller sommerhus), opførelsesår, konstruktion (murværk, træ, beton), tidligere ombygninger, kendte problemer (fugt, revner, skimmel, lugt, træk), bevaringsværdi, tegninger, BBR, tilstandsrapport.
Ved rum-projekter (fx bad, køkken) spørges altid til **rummets placering og geometri**: etage (stue, 1. sal, udnyttet tagetage), skråvæg (laveste og højeste højde), vinduer og ovenlys, vægtyper (murede eller lette skunk-/skillevægge), areal og bredde, loftshøjde, og hvad der er under gulvet (kryberum, terræn, opvarmet rum). I vådrum under 3,25 m² eller med en bredde på højst 1,3 m er alle vægge vådzone. En forkert antagelse her (fx kryberum og vandret loft i stedet for tagetage) kan kræve revision af alle fagnotater.

**C – Omfang og rammer:** Rum og areal, budget med buffer, tidsramme og deadlines, beboet under arbejdet, kvalitets- og energiambition.

**D – Udførelse:** Selv, håndværkere eller totalentreprise? Tilbud modtaget? Egne kompetencer, og hvad brugeren selv vil lave (gør-det-selv-grænser vurderes af fagene). Adgang og logistik.

**E – Myndighed og risici:** Ændres bærende konstruktioner, facade, areal eller anvendelse? Lokalplan, servitutter, bevaring? Installationer (gas, fjernvarme, olie, varmepumpe)? Opførelsesår → asbest, PCB, bly. Forsikring, ejerskifte, naboer.

**Fagfakta (efter blok B–E):** Gå `definition-of-ready.md` igennem for hvert berørt fag, og bed om fotos og dokumenter samlet i én runde. Spørg altid efter eksisterende registreringer, servicerapporter og manualer.

**F – Afslutning:** Opsummér forståelsen, antagelser og prioriteringer; få brugerens accept.

## Definition of Ready
- [ ] Formål og succeskriterier er klare
- [ ] Omfang og afgrænsning er beskrevet (med / ikke med)
- [ ] Bygningen er beskrevet (type, år, konstruktion, kendte problemer) – ved rum-projekter også rummets placering og geometri (etage, skråvæg, vinduer, vægtyper, bredde, loftshøjde, hvad der er under gulvet)
- [ ] Rammer for budget, tid og kvalitet – eller bevidst åbne
- [ ] Udførelsesform og brugerens egen rolle er kendt
- [ ] Fakta pr. berørt fag er indsamlet efter `definition-of-ready.md` (fotos, typeskilte, manualer, registreringer), eller manglerne er markeret som antagelser
- [ ] Myndighedsforhold og farlige stoffer er markeret som afklaret eller åbne
- [ ] Antagelser er skrevet ned og accepteret af brugeren
- [ ] Brugeren har accepteret projektgrundlaget

## Skabelon – project-basis.md
```
# Projektgrundlag – <case-id>
**Status:** udkast | kontrolleret | accepteret (dato)
## Formål og succeskriterier
## Bygningen
## Omfang (med / ikke med)
## Rammer (budget, tid, kvalitet, energi)
## Udførelse og brugerens rolle
## Myndighed, stoffer og risici (afklaret / åbent)
## Projektets rammer (krav- og begrænsningsliste R1–Rn med kilde)
## Antagelser
## Åbne spørgsmål
## Berørte fag (foreløbigt), sikkerhedskritiske fag (fuld kontrol) og DoR-status pr. fag
## Fag uden agent (screening, kloakmester, ansvarlig statiker, servicefirma …) – PL prissætter ved G1
## Hold points: navngivning HP-<FAG>-n pr. fag, HP1–HPn projektfælles (fast for hele sagen)
```
