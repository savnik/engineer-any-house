---
byg-bim: minor
byg-electrical: minor
byg-review: patch
---
El-plan efter gennemgang af elplanen.dk:

- **Ny kommando `bim.py elplan`.** Den laver en punktliste pr. rum og kontrollerer antallet af stikkontakter mod § 57 i BEK 1082/2016:
  - stk. 1: 1 pr. påbegyndt 4 m², højst 10
  - køkken: mindst 3 på mindst 2 kredse
  - bad/wc: mindst 1
  - garage, carport, loft og depot er undtaget

  Kommandoen udleder også afbrydertypen pr. lysgruppe (1-polet, korrespondance, kryds eller krone) og finder lamper uden gruppe.
- **BIM-spec.** Nye el-arter: `kraftstik`, `data` og `pir`. Nye felter: `lysgruppe`, `kreds` og `dimmer`, som gemmes i `Byg_El`. `geometri` kan nu udelades for el-punkter.
- **El-videnbasen** har fået:
  - behov pr. rumtype
  - logikken for afbrydertype
  - typiske placeringer (markeret T, ikke krav)
  - tjeklisten "El-plan rum for rum"
  - § 57, stk. 5 (verificeret)
- **El-fejlkataloget** (kontrol-el@1.3) har fået typiske misforståelser i el-planlægningsværktøjer, fx forældet zone 3, stik i område 2 og montagehøjder fremstillet som krav.
