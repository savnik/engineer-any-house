# El – praktisk erfaring fra udførelse og fejlfinding

Sidst opdateret: 2026-09-26. Alt her er **[ERFARING]**: praksis vist af en serviceelektriker, "Elektrikeren Holleufer" (Hareskov Elektric Service) – 9 YouTube-videoer (beskrivelser og automatiske transskriptioner) 17 faglige Instagram-opslag (opslagstekster; tale i reels er ikke tilgængelig som tekst) og TikTok-videoer, hvor automatiske undertekster fandtes (kun 1 af 10 testede). Det er arbejdsmetoder og typiske fund – ikke krav. Hvor et punkt berører et krav, står kravet i `normgrundlag.md`, eller punktet er markeret **T** (skal verificeres).

## 1. Fejlfinding: gruppe der slår fra, når det regner (udendørslys, skur)
1. Bekræft styringen først (fx ur og kontaktor): virker den, ligger fejlen i installationen efter kontaktoren.
2. Isolationsmål hver leder (L1, L2, L3, N) mod beskyttelseslederen på gruppens afgang. Praksisværdier: sund installation typisk langt over 1 MΩ (ofte hundreder af MΩ); 0,04 MΩ er en klar fejl, men udløser ikke nødvendigvis RCD'en i tørvejr – den slår typisk først fra, når installationen bliver våd og værdien falder yderligere.
3. Sektionér: adskil i dåser og armaturer, og mål hvert kabelstykke for sig. Tænd lamperne for at se, hvilke der er uden spænding – det viser, hvilken streng fejlen sidder på.
4. Følg kablet armatur for armatur. Forvent overraskelser: kabler, der løber videre til ukendte steder, samlinger af flere strenge i én lampe, glemte kabler med spænding på liggende løst i en lampe (farligt – afslut eller fjern).
5. Ligger fejlen i et jordkabel mellem to punkter: afkobl den defekte strækning midlertidigt, og få en kabelsøger til at lokalisere fejlen.
6. Nummerér alle ledere, før en rodet samling skilles ad – især når farver er blandet (fx blå og sort i samme samling).

## 2. Vand, jord og myrer i udendørsarmaturer
- Typisk årsag: ekstra hul boret i armaturet eller dåsen uden forskruning, nippel eller membran – i strid med fabrikantens anvisning. Vand, jord og insekter vandrer ind i installationen.
- Praksis: hvert hul, man laver, får en forskruning/nippel, der passer til kablet; ellers bruges de forberedte indføringer efter fabrikantens anvisning.
- Kabler, der kommer op af jorden, beskyttes mekanisk med rør. Nedgravede kabler dækkes med advarselsbånd/dækbånd (dybde og krav: T).
- Midlertidig afslutning af et kabel, hvor en lampe er fjernet: afslut i dåse, og beskyt mekanisk – fx stålrør, hvor der slås græs. Samlinger med muffer og tape er ikke en afslutning.

## 3. Tavleudskiftning i ældre bolig (rækkehus fra slutningen af 1960'erne)
- Typiske grunde til udskiftning: huller i kapslingen, så man kan røre spændingsførende dele; knækkede dele; komponenter, der har været smeltet og aldrig er skiftet; overophedede ledere; ulovlig "nulling" (forbindelse mellem nul og jord) lavet af gør-det-selv.
- Rækkehuse kan have gennemgående stikledning, der fortsætter til naboens tavle. Afbrydelse sker så før tavlen (kabelskab), og naboerne mister strøm – planlæg og varsl. Afbrydelse i kabelskab og alt arbejde ved måleren sker efter netselskabets regler (T); i praksis skal netselskabet selv flytte eller udskifte måleren.
- Arbejdsgang: sluk og kontrollér spændingsløshed (måleren skal stå stille) → opmærk stikledning og alle ledninger præcis som de sad → demontér → montér ny målerramme og præfabrikeret tavle → genopret forsyningen til naboerne hurtigst muligt → forlæng for korte ledere med krympemuffer eller forlæng rørinstallationen frem til de nye komponenter → skær indføringer præcist omkring kabler og rør, uden åbninger → momentspænd alle klemmer efter fabrikantens anvisning → mål (RCD-test, jord/overgangsmodstand, isolationsmåling af hele installationen) → spændingssæt → mærk alle grupper.
- Nulling (TN-C-S) kun, hvor netselskabet tillader det på adressen. PEN-leder udført som blå leder med grøn/gul mærkning i enderne (ifølge praksis; mærkningsregel T), ført fra jordforbindelsen via overspændingsbeskyttelse (SPD) til gruppetavlen.
- Forbindelser mellem tavler i for lille tværsnit (fx 2,5 mm²) er et typisk fund.

## 4. Ladestander der får forsikringer til at springe
- En kortslutning inde i laderen kan være svær at måle med installationstesteren, når den er uden spænding. Afbryd kablet ved laderen og mål kablet for sig (L1–L2, L1–L3 osv.): fejler kablet intet, er laderen defekt. Tegn på varme på bagpladen kan afsløre fejlen – dokumentér med foto.
- Udskift ikke gruppens komponenter på mistanke uden måling. Ladestander på samme RCD som resten af huset er ikke optimalt.

## 5. Service og montage
- **Korrespondance (to afbrydere til samme lys):** lys, der ikke kan slukkes, skyldes ofte ombyttede skinne- og mellemledninger i den ene afbryder. I 1970'er-byggeri siger farverne ikke meget – mål og følg ledningerne.
- **Overbelastning:** vaskemaskine og tørretumbler på samme gruppe får sikringen til at springe. Løsninger: egen gruppe (anbefalet – dimensionering efter reglerne) eller brugerens accept af ikke at køre dem samtidig; dokumentér rådgivningen.
- **Lange kabler:** et 1,5 mm² kabel på over 70 m til en port blev udskiftet til større tværsnit (spændingsfald; grænser T).
- **Tunge lamper:** skru i bærende træ; brug kun gipsanker der, hvor der ikke er træ, og efter lampens vægt. Afmål med laser. Skift lampekabler, hvis de er for korte, og brug altid aflastningen i lampeudtaget – den glemmes ofte.
- **Boring gennem vægge:** tjek for skjulte kabler og installationer på den anden side, før der bores.
- **Ulovlige samlinger:** grå eller grøn/gul brugt som fase er et klassisk fund – grøn/gul må kun være beskyttelsesleder (T for præcis henvisning).
- **Ventilator, der kører 100 %:** er motor og forsyning i orden, ligger fejlen typisk i CTS-styringen – snitflade til ventilations- eller CTS-tekniker.

## 6. Arbejdsmiljø i praksis
- Høje stiger: altid en hånd på stigen eller en makker, der holder; sikkerhedssko; vælg stige efter rummet (en 20-trins stige er upraktisk indendørs).
- Rækkehuse og fælles forsyninger: aftal afbrydelser med de berørte.

## 7. Flere fund fra service i praksis (Instagram @elektrikeren_holleufer)
- **Løse forbindelser giver brand uden at noget slår fra.** En løs muffe i en dåse gnistrede og blev brandvarm, da vaskemaskinen startede – der opstår hverken kortslutning eller fejlstrøm, så sikring og HPFI reagerer ikke. Lugten af brændt elinstallation er ofte det første tegn. Praksis: efterspænd og brug korrekte samlemetoder; gruppeafbrydere med gnistdetektor (AFDD) er på vej i markedet (krav og anvendelse: T).
- **Skjulte drivere og samlinger.** Transformere/drivere til spots findes løst i isoleringen eller mast op over loftet mellem dåser – én var brændt af få centimeter fra avispapir. Drivere skal være fastgjort, tilgængelige og placeret efter fabrikantens anvisning; skjulte samledåser skal findes og lovliggøres.
- **Efter overspænding: tjek alt elektronisk udstyr.** Efter en fejlmonteret ladestander havde der været 400 V i installationen: sprungne drivere og et varmt kiprelæ. Gennemgå drivere, relæer og elektronik på de berørte grupper.
- **Løse enkeltledere i vægge.** Gamle dåser, der sidder dybt (fx 8 cm bag gipsens yderkant), løses ofte med muffer og bløde ledere ud til stikkontakten – "kabel ført forkert ind i dåse". Løsning: træk nye ledere eller monter en forfradåse, så kablet føres dobbeltisoleret ind. Findes der fugt eller vand på dampspærren bag gipsen, så informér kunden – snitflade til tømrer/ventilation.
- **"Bang og røg fra stikkontakten":** løse enkeltledere uden dåse bag en ny mur, et stort hul, hvor dyr og fugt kom ind, og høj belastning fra en murermaskine. Afslut den gamle installation dobbeltisoleret, klip det brændte væk, og monter korrekt.
- **Vand vandrer i kabler.** Fugt fra én utæt udendørslampe kan via kapillarvirkning bevæge sig langs lederne i et ubrudt kabel og dukke op et andet sted. Klip tilbage til tørt kabel eller udskift strækningen; luk armaturer tæt bagfra – myrer flytter ind i lamper tæt ved jorden.
- **Nedgravede spots:** vandfyldte bokse og beton omkring gør udskiftning svær; tjek om kablet overhovedet er aktivt, før der graves; nedlagte enheder afsluttes forsvarligt.
- **Ny tavle fra 2025, der ville dumpe ved en elrapport:** 25 kabler ført ind gennem en fjernet bagpladeblanket, løse enkeltledere i murværket mellem måler og tavle, tegn på varme i ledere, sløjfeledere øverst på grupperne. Praksis: åbninger omkring kabler efter tavlens kapslingsklasse – for tavler monteret efter 2019 højst 2,5 mm (kanalens og GingerTechs udsagn; T mod DETF/fabrikant); ingen løse enkeltledere uden rør eller kanal.
- **Flytning af tavle:** alle kabler forlænges én til én med krympesamlinger til den nye placering; udbedr gør-det-selv-fejl samtidig. Skal samlingerne skjules bag isolering og gips, skal samlemetoden være godkendt til at være utilgængelig (T – undtagelserne i DS/HD 60364-5-52).
- **Små opgaver kan blive store:** et gammelt kraftudtag skulle blive til en stikkontakt (fjernvarme erstattede fyret), men en skjult samling bag tavlen forhindrede kabeludskiftning. Afsæt tid til det uforudsete.
- **Kunden borede i kablet ved ophængning af en hylde** – lyset blinkede, og senere manglede strømmen. Undersøg og udbedr beskadiget kabel; kunderådgivning om kabelsøger før boring.
- **KNX-hus:** separate kabler fra hvert lampeudtag til en KNX-tavle; tryk, binære input (alarm, persienner) og radiatorventiler i samme system. Planlæg tavleplads og kabelføring tidligt.
- **Elrapporter:** kanalen oplever – som GingerTech – at rapporter udført af kursusuddannede konsulenter finder markant færre fejl end rapporter fra elektrikere, og at fabrikantens anvisninger (fx ingen huller i indmuringsdåser) ikke er til forhandling.

## 8. Byggestrøm (TikTok @elektriker.holleufer)
- Byggestrømstavle til nedrivning og nybyg: ny forsyning fra kabelskabet til målertavlen; den gamle forsyning til huset fjernes.
- Afisolering af store kabler: snit rundt om kappen, hvor snittet skal stoppe, og derefter på langs; giv lederne overlængde ved måleren, så de kan tilpasses.
- Grav forsigtigt ved kabelskabet – andre stikledninger ligger tæt; brug ikke spade tæt på kendte kabler.
- Defekt klemme i kabelskabet: ring til netselskabet, som udskifter rækken (arbejde i kabelskab efter netselskabets regler – T).
- Midlertidigt jordspyd til byggestrøm: typisk ca. 1 m ned, så længe måleværdien er godkendt; jordlederen monteres i spydets klemme efter fabrikantens anvisning (fx flere omgange om spydet før og efter klemmen). Mål og dokumentér overgangsmodstanden.
