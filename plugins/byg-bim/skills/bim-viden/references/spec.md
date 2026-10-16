# Modelspec (model.yaml) – format

Én YAML-fil beskriver hele modellen. `bim.py byg` validerer alt først og viser **alle** fejl med sti til feltet (fx `aabninger.S-V3.vaeg 'S-YV.5' findes ikke – mente du S-YV.1 … S-YV.4?`). Skabelon: `assets/eksempel/model.yaml` (murermesterhus med kælder, stue og tagetage).

## Konventioner
- **Længder i mm, vinkler i grader.** Lokale akser: x langs (gade)facaden, y vinkelret. Origo i et ydervægshjørne.
- **z er relativ til etagens gulv.** Etagernes `kote` er relativ til ±0 = færdigt gulv i stueetagen.
- **Id'er** er unikke på tværs af alle sektioner. Brug korte, sigende id'er med etagepræfiks: `K-YV`, `S-IV2`, `S-V3`, `K.01`.
- **Kilde på alt:** `kilde` D (dokument/tegning) · M (målt) · F (foto) · B (bygherre) · K (godkendt fagnotat) · A (antagelse). Tekst må følge efter bogstavet (`"D 1937-plan"`). `ref` er dokument/side/mål-id, og `usikkerhed` er i mm. `standard: {kilde: A, status: eksisterende}` gælder, hvor intet er angivet. Undgå derfor at lade standarden dække over reelle kilder.
- **Blandet kildegrundlag** (fx placering fra tegningen, højde antaget): `kilde` er den svageste kilde for de mål, der har betydning for formålet. `ref` angiver hvert måls kilde, fx `kilde: D, ref: "K1 M3 (plan); højde A – projektgrundlag"`. Er højden afgørende (snit, mængder), så brug `kilde: A`.
- **Fælles felter på alle elementer:** `id`, `navn`, `etage` (ikke på åbninger og systemer), `status` (eksisterende|ny|nedrives|midlertidig), `kilde`, `ref`, `usikkerhed`, `fakta` (ejendomskort-id'er, fx `[E-F-07]`), `note`, `beskrivelse`, `egenskaber` (`{Pset_X: {...}}` eller egne `Byg_X: {...}` – aldrig egne sæt, der starter med "Pset"), `klassifikation` (`{system: BIM7AA, kode: "...", navn: "..."}`).

## model, standard, materialer
```yaml
model:
  navn: Eksempelvej 1           # påkrævet; indgår i stabile GlobalId'er – omdøb ikke senere
  schema: IFC4                   # IFC4 (standard) | IFC4X3
  adresse: {vej: …, postnr: "2800", by: …}
  bygning: {navn: Hus, opfoerelsesaar: 1938, anvendelse: Fritliggende enfamiliehus, fredet: false}
  geo: {oest: 721234.5, nord: 6187654.3, kote: 35.73, x_retning: 100}   # EPSG:25832 for origo, DVR90-kote for ±0,
                                 # x_retning = kompasretning af lokal +x (grader fra nord med uret)
                                 # hoejdesystem (valgfri, standard "DVR90"): angiv fx "DNN" eller "lokalt, datum ukendt",
                                 # når kote ikke er DVR90 → VerticalDatum $ og systemet står i IfcProjectedCRS.Description
  kontrol: {areal: {K: 110, S: 110}, tolerance: 0.05}   # BBR-arealer (brutto m² pr. etage-id) til tjek
standard: {kilde: A, status: eksisterende}
materialer: {tegl: {kategori: brick, farve: [0.70, 0.36, 0.26]}}   # valgfrit – kendte ord får farve og kategori selv
```

## typer
```yaml
typer:
  YV-hulmur: {klasse: vaeg, navn: Ydervæg hulmur 300, lag: [[tegl, 108], [mineraluld, 84], [tegl, 108]],
              ude: true, baerende: true, u: 0.55}
  BJL:       {klasse: daek, navn: Træbjælkelag, lag: [[træ gulv, 25], [træbjælker, 200], [puds på rør, 25]]}
  TAG:       {klasse: tag, lag: [[tagsten, 50], [lægter, 50], [spær, 150]]}
  V1:        {klasse: vindue, bredde: 1180, hoejde: 1300, felter: 2, ramme: 100}
  D1:        {klasse: doer, bredde: 825, hoejde: 2040, betjening: enkelt}   # enkelt | dobbelt | skyde
```
- **Lagrækkefølge:** ydervægge udefra og ind (gælder i lukkede løkker og ved `yderside`/`inderside`). Åbne vægge med venstre/højre-justering: fra højre mod venstre set i tegneretningen, og `vend_lag: true` vender. Dæk listes ovenfra og ned, tage udefra (tagbelægning) og ind.
- Tykkelsen er summen af lagene. Øvrige felter: `ude` (IsExternal), `baerende` (LoadBearing), `u` (ThermalTransmittance), `brand` (FireRating), `predefined`, `egenskaber`, `klassifikation`.

## etager
```yaml
etager:
  - {id: K, navn: Kælder, kote: -2400, fri_hoejde: 2100}
  - {id: S, navn: Stueetage, kote: 0, fri_hoejde: 2600}
  - {id: "1", navn: Tagetage, kote: 2900}            # tal-id'er i anførselstegn
```
`hoejde` er som standard afstanden til næste etage (sidste etage: 2500). Rum bruger `fri_hoejde`.

## vaegge
```yaml
  - {id: S-YV, etage: S, type: YV-hulmur, punkter: [[0,0],[10000,0],[10000,8500],[0,8500]], lukket: true,
     justering: yderside, kilde: D, ref: "K1 M1, M9"}
  - {id: S-IV1, etage: S, type: IV-mur, punkter: [[5000, 300], [5000, 8200]]}     # midt (standard)
  - {id: T-YV, etage: "1", type: GAVL, punkter: […], lukket: true, justering: yderside, hoejde: 6000, til_tag: TAG1}
```
- **Segmenter:** en polylinje med n segmenter giver vægge `<id>.1 … <id>.n`. Segment i går fra punkt i til punkt i+1, og i en lukket løkke går det sidste tilbage til punkt 1. Ét segment beholder sit id.
- **justering:** `yderside`/`inderside` betyder, at punkterne ligger på væggens yderside/inderside. Brug dem til ydervægge, også åbne (bygningens midte er "inde"). Ellers `midt`, `venstre` eller `hoejre` set i tegneretningen. Venstre/højre forveksles let, så foretræk yderside/inderside.
- **Samlinger** dannes automatisk: hjørner og T-samlinger trimmes (ydervæg > tykkere > først i spec). Indervægge må gerne tegnes til ydervæggens akse eller inderside.
- **hoejde:** standard for ydervægge er etagehøjden. Andre vægge går op til undersiden af næste etages gulvdæk. `bund` løfter foden. `til_tag: <tag-id>` klipper toppen efter tagets underside (gavle, murkrone, skunkvægge).

## aabninger
```yaml
  - {id: S-V1, vaeg: S-YV.1, type: V1, afstand: 1200, brystning: 850, kilde: D, ref: "K1 M2"}
  - {id: S-D0, vaeg: S-YV.1, type: D2, afstand: 4000, slaar_mod: inde, haengsel: slut}
  - {id: K-HUL1, vaeg: K-IV1, type: hul, afstand: 500, bredde: 900, hoejde: 2000, brystning: 0}
```
- `afstand` måles fra vægsegmentets **startpunkt** til åbningens nærmeste kant, langs segmentet. Ved yderside-løkker er det ydersidens hjørne.
- `brystning` er underkanten over etagegulvet (døre: 0). `bredde`/`hoejde` overstyrer typen og er påkrævet for `hul`.
- Døre: `slaar_mod` er den side, bladet slår mod: `inde`/`ude` (ydervægsløkker) eller `venstre`/`hoejre` (set i væggens tegneretning). `haengsel: start|slut` angiver, hvilken ende af åbningen hængslet sidder i.
- Vinduer: `placering: ude|midt|inde` i vægtykkelsen (standard ude i ydervægge).

## daek
```yaml
  - {id: S-GULV, etage: S, type: BJL, omrids: {fra_vaegge: K-YV, kant: inderside},
     huller: [[[5100,5600],[6000,5600],[6000,8200],[5100,8200]]]}       # trappehul, skorstenshul
  - {id: K-GULV, etage: K, type: KG, omrids: [[300,300],[9700,300],[9700,8200],[300,8200]], art: bund}
```
`top` er oversiden relativt til etagegulvet (standard 0), og dækket går nedad. `art` er gulv|loft|bund|tag. Uden type skal `tykkelse` angives. `fra_vaegge` henviser til en lukket vægløkkes id. Etagedæk ligger typisk inden for kældervæggenes inderside.

## tage
```yaml
  - {id: TAG1, etage: "1", form: sadeltag, omrids: [0, 0, 10000, 8500], rygning: x, haeldning: 45,
     tagfod: 400, udhaeng: 400, udhaeng_gavl: 150, type: TAG}
```
`form` er sadeltag|valmtag|pulttag (`hoej_side: x+|x-|y+|y-`)|fladt. `omrids` er rektanglet ved facadernes yderside. `tagfod` er højden af tagfladens underside ved facadelinjen, relativt til etagegulvet. Tagfladerne bliver IfcSlab (ROOF) samlet i en IfcRoof og er skåret lodret ved kip, grat, tagfod og gavl. Kviste og sammensatte tage laves med `generisk` (se mønstre).

## trapper (lige løb)
```yaml
  - {id: TR-K, etage: K, start: [5550, 5300], retning: 90, bredde: 800, stigninger: 13, grund: 220}
```
`start` er midten af nederste trins forkant, og `retning` er løbsretningen (0 = +x, 90 = +y). `stigning` er som standard etagehøjde / stigninger. Kvartsvingstrapper modelleres som to lige løb plus repos (`generisk`, IfcSlab LANDING), eller som én trappe med note.

## soejler og bjaelker
```yaml
  - {id: K-S1, etage: K, punkt: [2500, 4250], profil: {form: rhs, b: 100, h: 60, t: 5}, materiale: stål}
  - {id: K-B1, etage: K, fra: [300, 4250, 2150], til: [5000, 4250, 2150], profil: {form: i, h: 160, b: 74, tw: 6.3, tf: 9.5},
     kant: top, materiale: stål}
```
Profiler: `rekt` b h · `rhs` b h t · `i` h b tw tf · `rund` d · `roer` d t · `l` h b t. Søjlens højde er som standard op til undersiden af næste dæk. For bjælker er z i `fra`/`til` overkanten (`kant: top`), så den skal ligge under dækket.

## rum
```yaml
  - {id: S.01, etage: S, navn: Stue, punkt: [2500, 2000]}            # omrids findes fra væggene
  - {id: S.04, etage: S, navn: Køkken-alrum, punkt: [7000, 6000], afgraensning: [[[5000, 4200], [5000, 8200]]]}
  - {id: T.01, etage: "1", navn: Værelse, punkt: [5000, 4250], til_tag: TAG1}
```
Punktet skal ligge inde i et lukket rum (døråbninger lukkes ved væglinjen). `afgraensning` er virtuelle skillelinjer i åbne planløsninger. Alternativt kan `omrids` angives. IfcSpace får Name = id og LongName = navn, og nettoarealet beregnes.

## systemer, installationer, roer
```yaml
systemer:
  - {id: CV-F, navn: Centralvarme fremløb, art: varme}   # varme|brugsvand_koldt|brugsvand_varmt|afloeb|regnvand|ventilation|el|gas|andet
installationer:
  - {id: KEDEL, etage: K, art: pillefyr, punkt: [1500, 1200, 0], geometri: {kasse: [600, 700, 1300]}, system: CV-F,
     producent: …, model: …, kilde: F, ref: "typeskilt"}
  - {id: VVB, etage: K, art: beholder, punkt: [8500, 1000, 0], geometri: {cylinder: [520, 900]}}
roer:
  - {id: R-CV1, etage: K, system: CV-F, punkter: [[1500,850,1400],[1500,400,1400],[1500,400,2300]], diameter: 22, materiale: kobber}
```
`punkt` er bundens midtpunkt (z relativt til etagegulvet), og `rotation` drejer om lodret akse. Rør bliver IfcPipeSegment pr. segment med forbundne porte (`art: kanal` giver IfcDuctSegment). Modellér kun installationer fra godkendte fagnotater eller fotos/typeskilte.

**art → IFC:** kedel/pillefyr IfcBoiler · fjernvarmeunit/varmeveksler IfcHeatExchanger · varmepumpe IfcUnitaryEquipment · beholder/buffertank IfcTank STORAGE · ekspansionsbeholder IfcTank EXPANSION · radiator/konvektor IfcSpaceHeater · fordeler IfcPipeFitting · pumpe/draenpumpe IfcPump · ventil/blandeventil/sikkerhedsventil/kontraventil IfcValve · vandmaaler/energimaaler IfcFlowMeter · wc/haandvask/koekkenvask/bruser/badekar IfcSanitaryTerminal · gulvafloeb IfcWasteTerminal · broend IfcDistributionChamberElement · tavle IfcElectricDistributionBoard · stikkontakt IfcOutlet · lampe IfcLightFixture · afbryder IfcSwitchingDevice · ventilationsaggregat IfcUnitaryEquipment · ventilator IfcFan · luftventil/emhaette IfcAirTerminal · solcellepanel IfcSolarDevice · skorsten IfcChimney. Ellers: `klasse: IfcXxx` og `predefined`.

## generisk (nødudgang med rigtig klasse)
```yaml
  - {id: SKORSTEN, etage: K, klasse: IfcChimney, profil: [[4300,3400],[4800,3400],[4800,3900],[4300,3900]], bund: 0, hoejde: 10500,
     materiale: tegl}
  - {id: KVIST-TAG, etage: "1", klasse: IfcSlab, predefined: ROOF, profil: [[0,0],[2000,0],[2000,1500],[0,1500]],
     origo: [4000, 7600, 2600], x_akse: [1, 0, 0], z_akse: [0, -0.26, 0.97], dybde: 150}
```
Et profil i et lokalt plan (`origo`, `x_akse`, `z_akse` = ekstruderingsretning) ekstruderes `dybde`. Standard er lodret ekstrudering fra z = `bund`. Alternativt `mesh: {punkter: [[x,y,z]…], flader: [[0,1,2,3]…]}`. Brug altid den rigtige IFC-klasse. Proxy kun, når ingen klasse passer, og så med `navn`/ObjectType.

## Hovedmodel og forslag (én source of truth)
`bim/model.yaml` er **hovedmodellen** – det eneste sted, husets data står. Den rettes aldrig direkte. Hver ændring (en leverance, en ny radiator, en renoveringsvariant) laves i en **forslagsfil** oven på den og flettes først ind, når den er godkendt:
```
bim.py forslag bim/model.yaml bim-14          → bim/forslag/bim-14.yaml (basis + basis_sha256)
bim.py byg bim/forslag/bim-14.yaml            → byg, tjek, tegn og sammenlign forslaget
bim.py flet bim/forslag/bim-14.yaml --proev   → hvad ændres i hovedmodellen
bim.py flet bim/forslag/bim-14.yaml --note "bim/14 godkendt"
```
Forslaget indeholder kun det, der ændres – samme regler som projektversionen nedenfor, plus `slet: [id, …]` (fjern et element helt, fx en modelfejl) og `felt: null` (fjern et felt). `flet` skriver kun de berørte elementer om (kommentarer og alle andre linjer står urørt), kontrollerer, at resultatet giver præcis den model, forslaget gav, og at den validerer, gemmer versionen før og efter i `bim/historik/`, flytter forslaget til `bim/historik/forslag/` og logger i `bim/historik/flettelog.md`. Er hovedmodellen ændret, siden forslaget blev oprettet, stopper `flet`, hvis de samme elementer er ændret begge steder (konflikt) – opdatér forslaget, og lad kontrollen se det igen. Lav aldrig kopier eller snapshots af hovedmodellen ved siden af den.

## Renovering (projektversion oven på mastermodellen)
```yaml
basis: ../../2026-10-11-bim-eksempelvej-1/bim/model.yaml
model: {navn: Eksempelvej 1}             # samme navn → samme GlobalId'er for uændrede elementer
nedrives: [K-IV3, K-V2]                   # sættes til status nedrives
vaegge:
  - {id: K-YV-IS, etage: K, type: IS-100, punkter: […], status: ny, kilde: K, ref: "sag/murer/02"}
aabninger:
  - {id: K-V2, bredde: 1000}               # samme id: felterne overskrives
```
Elementer med samme id flettes felt for felt. Nye id'er tilføjes. Tegningerne viser NY i rødt og NEDRIVES gult stiplet. `nedrives` gælder hele elementer, ikke enkelte segmenter af en vægløkke (opdel løkken i basismodellen). Rum findes ud fra alle vægge, også dem der nedrives. Det fremtidige rum angives derfor med `omrids` eller `afgraensning` i projektspec'en.

## Mønstre
- **L-formet hus:** én lukket løkke med 6 punkter.
- **Kælder under terræn:** kældervægge som egen løkke på etage K, og kote fra tegning/BBR. Terræn er ikke nødvendigt for LOIN 2.
- **Kviste:** murede/lette kvistvægge på tagetagen (`til_tag` virker ikke for kvistens eget tag), kvisttaget som `generisk` IfcSlab ROOF og et hul i hovedtaget, der ikke modelleres (notér det i modelnotatet).
- **Udvendig kældertrappe:** `trapper` på etage K uden for ydervæggen og en `hul`-åbning/dør i ydervæggen.
- **Skorsten:** `generisk` IfcChimney fra kældergulv til over kip, med `huller` i etagedækkene.
