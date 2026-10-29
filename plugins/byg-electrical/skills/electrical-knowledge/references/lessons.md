# El – forankrede erfaringsblade

Format: `### EB-EL-<nr>: <titel>` med Situation/Problem/Løsning, Grundlag, Gyldighed, Status og dato. Nye blade kommer via `/byg:lessons`.

### EB-EL-001: Gør-det-selv-forarbejde bliver ikke "blåstemplet"
- Situation: bygherren riller og trækker kabler selv og beder en installatør om at slutte til.
- Problem: installatøren hæfter for arbejdet og vil typisk ikke overtage ansvaret for andres skjulte arbejde.
- Løsning: aftal på forhånd, hvad bygherren må forberede (fx nedrivning, afdækning), og lad installatøren udføre og dokumentere alt i den faste installation.
- Grundlag: [KRAV] autorisationsreglerne; [ERFARING] TEKNIQ/branche.
- Status: verificeret · 2026-09-25

### EB-EL-002: Spots og dåser punkterer dampspærren
- Situation: nye indbygningsspots eller dåser i isoleret loft eller skråvæg.
- Problem: fugtig indeluft trænger ud i konstruktionen → kondens, skimmel, energitab.
- Løsning: installationszone under dampspærren eller lufttætte dåser/kapper tilsluttet dampspærren; koordinér med tømrer.
- Grundlag: [ANVISNING] fugtteknik (BUILD/SBi); [ERFARING].
- Status: erfaring · 2026-09-25

### EB-EL-003: Elbillader i ældre hus
- Situation: ladestander ønskes i hus med ældre installation.
- Problem: kapacitet (stikledning/hovedsikring), manglende eller forkert RCD, lang kabelføring.
- Løsning: kapacitetsberegning, egen gruppe, RCD der håndterer DC-fejlstrøm, laststyring, tilmelding til netselskab.
- Grundlag: [NORM] DS/HD 60364-7-722 (T for detaljer); [ERFARING].
- Status: erfaring · 2026-09-25

### EB-EL-004: Typiske fund ved eleftersyn (praktisk erfaring)
- Situation: gennemgang af eksisterende boliginstallationer, fx til elinstallationsrapport ved hussalg.
- Problem: de samme fejl går igen – sikringer der er for store til materiellet eller tværsnittet (manglende pasring), tavler med for store åbninger, manglende mærkning eller dårlig tilgængelighed, dåser uden aflastning eller med skruer/søm igennem, kabler ikke ført ind, bøjelig ledning eller forlængerledning som fast installation, manglende virksom beskyttelsesleder ved maskiner i bryggers, indendørsmateriel brugt udendørs og spændingsførende samlinger efter nedtaget udstyr (fx ladeboks).
- Løsning: udfør og dokumentér arbejdet, så det kan tåle et eleftersyn: sikring efter materiel og tværsnit, dåser og aflastning efter fabrikantens anvisning, samlinger i dåse, korrekt kapslingsklasse, afslut nedtaget udstyr korrekt, mål beskyttelsesleder og RCD, og fotodokumentér skjulte dele.
- Grundlag: [ERFARING] GingerTech (@GingerTech-FTW) og offentliggjorte elinstallationsrapporter; [ANVISNING] SIK-håndbog til elinstallationsrapporter.
- Gyldighed: boliger; bedømmelse af eksisterende installationer sker efter reglerne på udførelsestidspunktet.
- Status: erfaring · 2026-09-26

### EB-EL-005: Ny eltavle i ældre hus – sikring efter det gamle materiel
- Situation: ny tavle med 13 A-automatsikringer monteres i et hus med ældre udtag og afbrydere.
- Problem: ældre materiel er mærket 10 A (6 A i meget gamle huse). 13 A-sikringer kan overbelaste det – udtag og sløjfeklemmer bliver varme ved vedvarende høj belastning – og det anmærkes som forkert sikringsmateriel.
- Løsning: registrér mærkestrømmen på eksisterende materiel pr. gruppe; vælg sikring efter laveste mærkestrøm og tværsnit (10 A ved gammelt 10 A-materiel) eller udskift materiellet; dimensionér nye kabler efter de generelle regler (temperatur, oplægning, samlet fremføring); mærk tavlen korrekt; tætning af indføringer må ikke forringe tavlens IP-klasse.
- Grundlag: [ERFARING] GingerTech – fundet opretholdt i Sikkerhedsstyrelsens revision; [KRAV] BEK 1082 (13 A-reglen gælder egnet materiel); historiske stærkstrømsregler (T).
- Status: erfaring · 2026-09-26

### EB-EL-006: Udendørslys der slår fra i regnvejr
- Situation: RCD eller gruppe slår fra, når det regner – typisk udendørslys, skur eller garage.
- Problem: isolationsfejl i jordkabel, armatur eller samling, som kun viser sig, når installationen er våd.
- Løsning: isolationsmål hver leder mod beskyttelseslederen; sektionér i dåser og armaturer og mål hvert stykke; tænd lamperne for at finde den døde streng; afkobl den defekte strækning midlertidigt og brug kabelsøger ved fejl i jord. Nummerér ledere før rodede samlinger skilles ad.
- Grundlag: [ERFARING] Elektrikeren Holleufer; [ANVISNING] isolationsmodstand > 1 MΩ ved verifikation (Sikkerhedsstyrelsen).
- Status: erfaring · 2026-09-26

### EB-EL-007: Hul i armatur eller dåse uden forskruning
- Situation: der bores et ekstra hul i en udendørslampe eller dåse for at få kablet ind.
- Problem: uden forskruning, nippel eller membran trænger vand, jord og insekter ind – fejlstrømme og korrosion.
- Løsning: brug de forberedte indføringer eller en passende forskruning i hvert nyt hul, efter fabrikantens anvisning; beskyt kabler mekanisk, hvor de kommer op af jorden.
- Grundlag: [ERFARING] Elektrikeren Holleufer og GingerTech; fabrikantens anvisning.
- Status: erfaring · 2026-09-26

### EB-EL-008: Tavleskift i rækkehus med gennemgående stikledning
- Situation: en gammel tavle skal skiftes i et rækkehus, hvor stikledningen fortsætter til naboen.
- Problem: afbrydelse rammer naboerne; gammel installation kan skjule ulovlig nulling, overophedede ledere og for små tværsnit mellem tavler.
- Løsning: planlæg og varsl afbrydelsen; afbryd og arbejd ved måler og kabelskab efter netselskabets regler; opmærk alt før demontering; genopret naboernes forsyning hurtigst muligt; skær indføringer præcist; momentspænd; mål (RCD, jord, isolation) før spændingssætning; mærk grupperne.
- Grundlag: [ERFARING] Elektrikeren Holleufer; [KRAV] verifikation før idriftsættelse (installationsbekendtgørelsen § 75); netselskabets regler (T).
- Status: erfaring · 2026-09-26

### EB-EL-009: Løse forbindelser – brand uden at noget slår fra
- Situation: brændt lugt eller sværtede samlinger i en dåse, typisk ved en belastning som vaskemaskine eller varmelegeme.
- Problem: en løs muffe eller klemme giver gnister og varme uden kortslutning eller fejlstrøm – sikring og HPFI reagerer ikke.
- Løsning: udskift den skadede samling og dåse, efterspænd og brug korrekte samlemetoder; overvej gruppeafbryder med gnistdetektor (AFDD) hvor relevant (krav T); find andre skjulte samlinger og drivere, og fastgør dem efter fabrikantens anvisning.
- Grundlag: [ERFARING] Elektrikeren Holleufer (Instagram); fabrikantens anvisning.
- Status: erfaring · 2026-09-26
