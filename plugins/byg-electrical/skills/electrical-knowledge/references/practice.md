# El – faglig praksis på mesterniveau

**(T)** = typisk værdi eller praksis, verificér før brug som krav.

## 1. Planlægning af boliginstallationer
- **Behovsanalyse:** rum for rum – stikkontakter (også ved seng, skrivebord, tv, køkkenbord), belysning (grundlys, arbejdslys, stemningslys), faste apparater, fremtid (elbil, varmepumpe, solceller, batteri).
- **Behov pr. rumtype (spørg bygherren):** køkken – emhætte, opvaskemaskine, køleskab/fryser, ovn, kogeplade (kraft 400 V), lys under overskabe, stik over bordplade; gang, bryggers og trappe – PIR-sensor, korrespondance ved flere indgange; soveværelse – korrespondance ved dør og seng, stik ved begge sider af sengen; stue – tv/data, USB-stik, dæmpbare lysgrupper; carport/udendørs – elbil (rør og plads i tavlen nu), udendørs stik og lys. Se tjekliste "El-plan rum for rum".
- **El-plan:** punktliste pr. rum (stik, lampeudtag, afbrydere, data/tv, faste apparater) og lysgrupper med afbryderplacering. Afbrydertypen følger af lysgrupperne (T): 1 betjeningssted for 1 lysgruppe giver 1-polet afbryder; 2 steder giver korrespondance; 3 eller flere giver korrespondance med krydsafbryder(e); 1 sted for 2 lysgrupper giver kroneafbryder; dæmpning vælges pr. lysgruppe. Antal stik efter § 57 kontrolleres pr. rum (normgrundlag). BIM-modellen kan kontrollere det: `bim.py elplan`.
- **Typiske placeringer (T – sekundær: elplanen.dk-guide, 2026-10; ikke krav):** stikkontakt ca. 30 cm over gulv; over køkkenbord 10–15 cm over bordpladen; hvidevarer 15–30 cm; afbryder ca. 110 cm (tilgængeligt: ca. 90 cm), 10–15 cm fra dørkarmen i dørens grebside; væglampe 170–180 cm; pendel 60–70 cm over spisebord; spots 50–60 cm fra væg; PIR på væg 2–2,5 m. Hold ca. 15 cm fra indvendige hjørner og ca. 10 cm fra dør- og vinduesrammer samt gulv/loft. Køkken: gerne ≥ 4 stik over bordpladen med afstand og eget udtag pr. hvidevare.
- **Gruppeplan:** fordel belysning og stikkontakter logisk; separate grupper til store faste forbrugere (komfur, ovn, vaskemaskine, tørretumbler, varmepumpe, ladestander, el-gulvvarme i større omfang).
- **Beskyttelse:** RCD ≤ 30 mA, aldrig type AC i boliger, sikring efter stikkontaktens mærkestrøm (normgrundlag, BEK 1082-tabellen); overvej flere RCD'er for at begrænse udfaldets omfang; overspændingsbeskyttelse og evt. lysbuedetektering vurderes (T).
- **Kapacitet:** samlet effekt, samtidighed og hovedsikring/stikledning – særligt ved elbil og varmepumpe. Effekt- eller laststyring kan undgå opgradering.
- **Flere nye forbrugere og produktion samtidig (lader, varmepumpe, solceller, batteri):** planlæg dem som ét system – fælles kapacitetsvurdering, tavleplan og tilmelding, og styring, der flytter opladning og varmepumpedrift til timer med egenproduktion (øger egenforbruget og mindsker spidslasten). Vælg lader og inverter, der kan tale sammen.
- **Føringsveje:** installationszone inden for dampspærren i lette konstruktioner; lufttætte dåser hvor dampspærren gennembrydes; riller i murværk kun hvor statikken tillader (bærende vægge: begrænsninger – T, afklar med murer/statiker).

## 2. Særlige rum og anlæg
- **Badeværelse (DS/HD 60364-7-701):** zoner omkring badekar og bruser, IP-krav til materiel i zonerne, RCD for kredsene, stikkontakter uden for zonerne (dansk praksis: mindst 120 cm fra åben bruser – V sekundær). El-gulvvarme i vådrum: egnet varmemåtte, jordet skærm, termostat med gulvføler; koordinér med membran og fald.
- **Udendørs:** IP-klasse efter placering, RCD, mekanisk beskyttelse og nedgravningsdybde for jordkabler (T).
- **Elbilladning (DS/HD 60364-7-722):** egen gruppe pr. ladepunkt, RCD-løsning der håndterer DC-fejlstrømme (typisk type A + 6 mA DC-detektering i laderen eller type B – T), lastbalancering, tilmelding til netselskab (T).
- **Solceller (DS/HD 60364-7-712):** autorisation, generatortilslutning, mærkning og tilmelding – se normgrundlag "Solceller"; DC-side med korrekt kabel, stik og afbrydere; brand- og tagsnitflade til tømrer/tagdækker; tilmelding til netselskab (T). Plugin-solceller med stikprop frarådes af Sikkerhedsstyrelsen.
- **Varmepumper og aggregater:** forsyning og beskyttelse efter producentens krav (frekvensomformere → RCD-type), serviceafbryder, styresignaler.

## 3. Ældre installationer
- Typiske fund (T): ingen eller få RCD'er; stikkontakter uden jord; stofisolerede eller sprøde ledninger; varmeskadede samlinger; ældre skruesikringer; tilføjelser udført af ukyndige.
- Skeln: installationen skal opfylde reglerne fra etableringstidspunktet – men ved ombygning og udvidelse gælder nye regler for det nye (§ 25), og RCD ≤ 30 mA kræves også i eksisterende installationer (§ 61). Grænserne for køkken, tavle og beskyttelsesleder: normgrundlag "Ændring og udvidelse".
- Ved fund: forklar ejeren, at han har pligt til at lade fejl og mangler afhjælpe snarest muligt (elsikkerhedsloven § 10) – ikke kun at det "anbefales".
- Gammel tavle: må blive, hvis den bliver på stedet (§ 68, stk. 1); flyttes den – uanset afstand – skal den opfylde nugældende krav, hvilket i praksis ofte betyder ny tavle (fx RCD ≤ 30 mA, ikke type AC; placering efter § 55).
- Anbefaling ved køb eller renovering: gennemgang med målinger (isolationsmodstand, kontinuitet, RCD-test), eftermontering af RCD, udskiftning af varmeskadede og uisolerede dele, dokumentation.
- Stikkontakter med jord i 2-lederinstallation: nye/ændrede kræver virksom beskyttelsesleder (§ 64). Uden beskyttelsesleder er løsningen RCD ≤ 30 mA, som tillader klasse I-materiel (§ 73) – ikke jordede stikkontakter med tom jordklemme. Privatpersoner må kun udskifte stikkontakter, når der er HFI/HPFI.

## 4. Klimaskærm, brand og lyd
- Gennembrydning af dampspærre: lufttætte dåser, manchetter og tape efter dampspærresystemet; helst installationszone (samarbejde med tømrer).
- Indbygningsspots i isolerede lofter: egnede armaturer/brandkapper, afstand til isolering efter producent, varmeafgang fra drivere.
- Brandadskillelser: brandtætning af kabelgennemføringer med godkendt system (koordinér med tømrer/murer).
- Lyd i etageboliger: dåser ryg mod ryg i lejlighedsskel undgås.

## 5. Fejlfinding – hurtigopslag
- **RCD slår fra:** kobl belastninger fra én ad gangen; mål lækstrøm; tænk fugt (udendørs, badeværelse, kælder), elementer, apparater med filtre; flere små lækstrømme summerer.
- **Sikring springer:** overbelastning (for mange apparater) eller kortslutning (straks, også uden belastning) – find kreds, mål isolationsmodstand.
- **Blinkende lys/dæmpere:** kompatibilitet mellem LED og dæmper, løse forbindelser (farligt – varmeudvikling).
- **Varm stikkontakt eller dåse:** løs forbindelse eller overbelastning – afbryd og få den efterset.

## 6. Grænseflader set fra el
| Fag | El forventer | El leverer |
|---|---|---|
| Tømrer | Installationszone, føringsveje, forstærkning til armaturer, adgang | Dåseplacering og kabelføring før lukning; lufttætte gennemføringer |
| Murer | Riller og udsparinger aftalt og statisk forsvarlige | Placering af riller og dåser |
| VVS | Placering og effekt på varmepumpe, vandvarmer, pumper; udligning | Forsyning, beskyttelse, udligningsforbindelser |
| Ventilation | Aggregatets effekt og styring | Forsyning, serviceafbryder, styresignaler |
| Maler | Afdækning; dæksler/rammer af- og påmonteres efter aftale | Endelig montage efter maling |
