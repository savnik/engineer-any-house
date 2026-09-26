---
name: kontrol-viden
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
| `references/kontrolgrundlag.md` | Tværgående dansk kontrolgrundlag med status og kilder | Alle kontrolagenter |
| `references/fag/<fag-id>.md` | Rubric-version, kontrolpunkter, fejlkatalog og primærkilder for faget | Fagets kontrolagent |
| `references/rca-skabelon.md` | Root cause-analyse efter 3 afviste forsøg | Orkestrator/projektleder |

Fagfiler: `vvs`, `el`, `murer`, `ventilation`, `maler`, `toemrer`, `projekt`.

Rubric-versionen står øverst i hver fagfil og angives i hver dom. Ændringer i en fagfil kræver ny version (fx `kontrol-vvs@1.1`) og review – typisk efter en RCA.
