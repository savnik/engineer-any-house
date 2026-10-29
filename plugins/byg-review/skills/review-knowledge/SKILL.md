---
name: review-knowledge
description: >-
  Kontrolviden for byg-kontrolagenterne: dansk kontrolgrundlag (KLS, verifikation,
  funktionsafprøvning, lufttæthed, uafhængighedsprincippet i BR18, MBK, tolerancer),
  kontrolpunkter og fejlkataloger pr. fag samt RCA-skabelon. Læses af kontrolagenterne
  og af orkestratoren ved root cause-analyse – ikke af fagagenterne.
disable-model-invocation: true
---

# Kontrolviden

Holdes adskilt fra fagenes videnbaser, så kontrollen ikke deler fagagentens blinde vinkler.

| Fil | Indhold | Læses af |
|---|---|---|
| `references/review-basis.md` | Tværgående dansk kontrolgrundlag med status og kilder | Alle kontrolagenter |
| `references/trades/<trade-id>.md` | Rubric-version, kontrolpunkter, fejlkatalog og primærkilder for faget | Fagets kontrolagent |
| `references/rca-template.md` | Root cause-analyse efter 3 afviste forsøg | Orkestrator/projektleder |

Fagfiler: `plumbing`, `electrical`, `masonry`, `ventilation`, `painting`, `carpentry`, `bim`, `structural`, `architecture`, `landscape`, `project`.

Rubric-versionen står øverst i hver fagfil og angives i hver dom. Ændringer i en fagfil kræver ny version (fx `kontrol-vvs@1.1`) og review – typisk efter en RCA.
