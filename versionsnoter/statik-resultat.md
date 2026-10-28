---
byg-statik: minor
byg-kontrol: patch
byg: patch
---
Opslag i en statisk beregning uden ny beregning: `fem.py resultat <fem.yaml> [--element] [--kombi]` viser det gemte resultat med kombination, spec-sha og overslagsforbehold og afviser det, hvis `fem.yaml` er ændret siden eller resultatet er regnet med `--saet`. Statik-kontrollen må bruge kommandoen. Projektlederen svarer på spørgsmål til en færdig beregning ud fra det godkendte statiknotat; nye tal og ændrede input går til statikeren som leverance.
