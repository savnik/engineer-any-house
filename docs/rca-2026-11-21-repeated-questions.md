# RCA – pluginet spørger om det samme igen og igen (2026-11-21)

Blameless. Grundlag: sagsmappen for en rigtig VVS-sag på et parcelhus (beslutningslog, status, domme) og hovedtrådens transskripter 2026-10-11 til 2026-11-21. Sagens adresse og personer er udeladt.

## 1. Hændelse
Brugeren oplevede pluginet som en modvillig kollega. Fire emner blev rejst igen, efter brugeren havde svaret:

| Emne | Brugerens svar | Rejst igen | Brugerens reaktion |
|---|---|---|---|
| Sikkerhedsafløb til spand | Valgt 2026-10-11 (M10), bekræftet 2026-10-16 (B-16-1) | 10 hovedtrådssvar i 7 sessioner til og med 2026-11-21, et mindre fund (anbefal kobber til det parkerede afsnit) og "Jeg ser det som et sikkerhedsproblem" i VVS-overblikket 2026-11-21 | "Se bort fra afløb." |
| Sikkerhedsstyrelsens svar (gør-det-selv) | Gengivet 2026-11-20 | "gem svaret" som fund i 3 domme, som `afklar_med_bruger`, i status 3 gange og i 7 hovedtrådssvar | "Accepter det svar som er givet og spørg ikke igen." |
| CO-alarm | "Drop alt om ventilation og co2 alarm" 2026-11-11 (i en branch-sag) | Rejst i hovedsagen 2026-11-21 som modstrid med HP-VVS-0/68 | "Der er allerede en co2 alarm." |
| Foto af PEX-påtryk, brandtætning, VVS'er | Spurgt flere gange | Står i "Det mangler jeg fra dig" | "Intet foto – spørg mig ikke igen." · "Ingen brændtætning og ingen vvser." |

## 2. Den første analyse – og hvorfor den ikke holdt
Den første forklaring var, at reglerne manglede: intet sagde, at brugerens oplysning (kilde B) er grundlag nok, eller at en logget beslutning er afgjort. Rettelsen var tre promptregler. Gennemgangen af transskripterne viser, at det kun er en del af forklaringen:
- Beslutningen om spanden **stod** i beslutningsloggen, og projektlederen kendte den. Den blev alligevel rejst, fordi kilderne til de "åbne punkter" aldrig fik besked.
- Rettelsen bad kontrollen tjekke "den afbødning, der er besluttet med valget". Det er netop den mekanisme, der holdt spanden i live (kæde C).
- En regel om at "søge i beslutningsloggen" hjælper lidt: loggen er over 230 linjer fritekst, og `/byg:status` og hooken efter compact læser kun de sidste ca. 15 linjer.

## 3. 5 Why
### Kæde A – lukkede emner kommer tilbage
1. Hvorfor blev lukkede emner forelagt igen? → Projektlederen lister åbne punkter fra `status.md`, fagnotater, hold point-tabeller, domme og hjælpeagenters overblik (evidens: hjælpeagentens prompt 2026-11-21 15:29 beder om "ALLE åbne VVS-punkter" fra netop disse kilder og nævner selv "Sikkerhedsstyrelsens svar" som ventende).
2. Hvorfor stod de som åbne i disse kilder? → Brugerens svar skrives kun i beslutningsloggen. Godkendte fagnotater og deres hold points må ikke rettes (fælles protokol: "Ret aldrig et godkendt notat"), og mindre fund står som `aabent` i dommene for altid (kontrolprotokol afsnit 4).
3. Hvorfor filtreres de ikke mod beslutningsloggen? → Loggen er fritekst i kronologisk orden uden kobling til de hold points, fund og risici, en beslutning lukker. `/byg:status` og hooken efter compact læser kun de sidste ca. 15 linjer (status-skill punkt 1, `review_gate.py after_compact`). M10 og B-16-1 stod i linje 32 og 71.
4. Hvorfor slår det igennem så ofte? → Designet kræver én opgave pr. session og genoptagelse med `/byg:status` (ARCHITECTURE, "Effektivitet"). Hver ny session, hvert compact (resuméet bevarer "åbne spørgsmål til brugeren", PreCompact-instruksen) og hvert overblik afleder de åbne punkter på ny fra de samme kilder.
5. Hvorfor har systemet ingen tilstand for "lukket af brugeren"? → Kvalitetslaget har livscyklus for leverancer (afventer kontrol → godkendt) og fund (nyt → lukket), men brugerens spørgsmål har ingen: et spørgsmål kan stilles, men aldrig lukkes ét sted, som alle læser.

**Grundårsag A:** ingen fælles, maskinlæsbar registrering af brugerens svar og lukninger, som alle afledninger af "åbne punkter" filtreres imod. Kategori K7 (platform/tilstand) og F3 (prompt).

### Kæde B – brugerens oplysning blev behandlet som udokumenteret
1. Hvorfor bad kontrollen om Sikkerhedsstyrelsens svar? → Den skulle efterprøve lovkrav mod primærkilde og kunne ikke efterprøve en gengivelse (dom plumbing/32: "Uden det hviler autorisationsvurderingen på bygherrens gengivelse").
2. Hvorfor skulle den vurdere autorisation? → Før version 2.0.0 tog fag og kontrol stilling til gør-det-selv-grænser, og VVS-notaterne fastlagde "autoriseret VVS, indtil Sikkerhedsstyrelsen har svaret" (beslutningslog 2026-11-19 og 2026-11-20).
3. Hvorfor blev svaret ikke godtaget, da det kom? → Kontrolprotokollen kræver primærkilde for lovkrav og siger intet om kilde B. Kilde B er kun defineret i ejendomskortet (`case-dir.md`).
4. Hvorfor blev det ved? → Fundet var mindre og stod som `aabent` i hver ny dom. Projektlederen førte det videre i status (kæde A).
5. Hvorfor ikke stoppet af 2.0.0? → Sessionerne kørte før udgivelsen 2026-11-21 16:04. 2.0.0 fjerner emnet (autorisation), men ikke den generelle regel om, at brugerens gengivelse er grundlag.

**Grundårsag B:** kontrollens krav om primærkilde har ingen undtagelse for brugerens egne oplysninger, og autorisationsreglen (nu fjernet) skabte spørgsmålet. Kategori K4 (kontrolkalibrering).

### Kæde C – projektlederens anbefaling blev en betingelse i brugerens valg
1. Hvorfor blev spanden rejst igen 2026-11-21? → Overblikket sagde, at spanden "strider mod sagens egen afbødning (fast metalrør plus vandalarm)".
2. Hvorfor var afbødningen sagens egen? → Projektlederen skrev i B-16-1: "M10's afbødning efter vvs-16 er en del af valget". Brugeren havde valgt spanden, ikke afbødningen.
3. Hvorfor blev det til en modstrid? → plumbing/32 skrev, at restrisikoen var accepteret "under forudsætning af et fast rør og en vandalarm". Da brugeren 2026-11-20 sagde "spand uden rør", så det ud som et brud på beslutningen.
4. Hvorfor kontrollerede systemet det? → Kontrolprotokollen gør modstrid med godkendte notater til et væsentligt fund, og den første rettelse bad endda kontrollen tjekke "den afbødning, der er besluttet med valget".
5. Hvorfor kunne projektlederen skrive det sådan? → Ingen regel skelner mellem brugerens valg og projektlederens anbefaling, når en beslutning logges.

**Grundårsag C:** beslutninger logges med projektlederens anbefalinger som betingelser. Kategori F3.

### Kæde D – beslutninger i en branch-sag gælder ikke hovedsagen
1. Hvorfor blev CO-alarmen rejst igen? → Hovedsagens godkendte VVS-notater kræver CO-alarm (HP-VVS-0/68).
2. Hvorfor kendte hovedsagen ikke fravalget? → Det stod kun i branch-sagens beslutningslog (B19).
3. Hvorfor? → Branch-sagens beslutninger løftes først ind i hovedsagen, når branchen afsluttes (`case-dir.md`).
4. Hvorfor er det et problem? → Brugerens svar handler om huset, ikke om branchen, men gemmes pr. sag.
5. Hvorfor? → Der er ét sted for husets fakta (ejendomskortet), men intet fælles sted for brugerens svar.

**Grundårsag D:** brugerens svar gemmes pr. branch og ikke ét sted for hele sagen. Kategori K7.

## 4. Konklusion – ændret
Den første konklusion ("reglerne mangler") var rigtig, men utilstrækkelig. Hovedårsagen er **tilstand**, ikke tone: brugerens svar har intet sted at bo, som alle kilder til åbne punkter respekterer. Derfor blev de samme punkter afledt igen fra notater, hold points, domme og status i hver session og efter hvert compact. Det forstærkes af, at projektlederen gjorde sine egne anbefalinger til betingelser (C), af at branch-beslutninger ikke deles (D), og – for Sikkerhedsstyrelsen – af den nu fjernede autorisationsregel (B).

## 5. Forbedringer
| # | Grundårsag | Ændring |
|---|---|---|
| 1 | A, D | Nyt register `closed-by-user.md` i hovedsagen (delt af branches): brugerens ord ordret, hvad rækken lukker, hvad den betyder. Skrives straks, når brugeren svarer (`case-dir.md`, projektlederens grundregel 6) |
| 2 | A | Registret gælder frem for ældre fagnotater, hold points, risici og domme, også godkendte, uden revision (fælles protokol og kontrolprotokol) |
| 3 | A | Hooken genindlæser registret efter compact, før `status.md`, også for branch-sager. PreCompact bevarer lukninger og skelner dem fra åbne spørgsmål (`review_gate.py`, test) |
| 4 | A | `/byg:status` læser registret først. Projektlederen filtrerer alle spørgsmål og åbne punkter mod det. Hjælpeagenter, der samler åbne punkter, får det med (`quality-review`, "Filtrér før du spørger") |
| 5 | A | Stien til registret står i fagforespørgslen og kontrolkaldet, sammen med beslutningsloggen |
| 6 | B | Brugerens oplysning (kilde B) er grundlag, også gengivne svar fra myndigheder. Krav om dokumentation er aldrig et fund og aldrig `afklar_med_bruger` |
| 7 | C | Valget logges, som brugeren traf det. Anbefalinger bliver ikke betingelser. Kontrollen tjekker kun det, brugeren har valgt |
| 8 | – | Genåbning af en lukning er et mindre fund. Kun ny viden, der ændrer risikoen væsentligt, forelægges én gang |

Ikke ændret: sikkerhedsadvarsler gives stadig, når valget træffes, og akut fare går forud for alt.

**Opfølgning:** registret er tomt i eksisterende sager, indtil projektlederen fører de lukninger ind, der allerede står i beslutningsloggen. Effekten kan måles med `scripts/usage.py` eller et eksamensforsøg (gentagne spørgsmål pr. session).
