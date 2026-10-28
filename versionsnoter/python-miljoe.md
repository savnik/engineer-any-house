---
byg-bim: patch
byg-statik: patch
---
Værktøjernes Python-miljøer er nu fuldt låst (alle pakker, også transitive, for Python ≥ 3.11 på alle platforme), så alle får samme versioner. `opsaet` bruger uv, hvis det er installeret, ellers pip, og giver en klar fejl ved for gammel Python. pytest ligger ikke længere i brugernes BIM-miljø (`bim.py opsaet --test`). Opsætningen deles via `faelles/miljoe.py`.
