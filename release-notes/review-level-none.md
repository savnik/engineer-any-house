---
byg-review: minor
byg: patch
---
Kontrol udeladt for hurtige spørgsmål: et fagkald med `REVIEW-LEVEL: none` (eller `review_gate.py skip <id> --grund "…"` efter afleveringen) afslutter leverancen som `udeladt` uden kontrolagent. Stop-hooken blokerer ikke længere, men viser leverancen én gang. Status og case-git viser grunden, og den registreres i `quality/<id>__udeladt.json`. Forslag flettes ikke, og notatet beskyttes ikke. Et senere kontrolkald på samme ID er forsøg 1. Afvises for el, statik og BIM, i fase 3+ og for leverancer med forslag til fælles sagsfiler. Projektlederen bruger det til hurtige spørgsmål, når bygherren har bedt om det (quality-review, afsnit 2b).
