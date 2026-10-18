# Ændringslog

## 0.10.0 – 2026-10-18

- `byg` 0.8.0 → 0.9.0
- `byg-bim` 0.4.2 → 0.5.0
- `byg-el` 0.1.13 → 0.1.14
- `byg-kontrol` 0.10.0 → 0.11.0
- `byg-maler` 0.1.8 → 0.1.9
- `byg-murer` 0.1.8 → 0.1.9
- `byg-statik` 0.3.2 → 0.3.3
- `byg-toemrer` 0.1.8 → 0.1.9
- `byg-ventilation` 0.1.9 → 0.1.10
- `byg-vvs` 0.1.9 → 0.1.10

### token-effektivitet (byg, byg-bim, byg-el, byg-kontrol, byg-maler, byg-murer, byg-statik, byg-toemrer, byg-ventilation, byg-vvs)
Tokenbudget: workflows i byg-sager kun på brugerens udtrykkelige ønske (hook); kontrolagenter og bim-sammenligner på Sonnet, `KONTROLNIVEAU: fuld` kræver `model: opus`; højst 2 forsøg pr. runde og eskalering til brugeren, ny runde med RCA kun efter `Ny runde <id>` (højst 2 runder); `maxTurns` på alle agenter; fælles "Tokenbudget"-regler for fag- og kontrolagenter; projektlederen spørger efter 3 fagleverancer i samme sag; status-skillen læser mindre.

## 0.9.0 – 2026-10-16

- `byg` 0.7.2 → 0.8.0
- `byg-bim` 0.4.1 → 0.4.2
- `byg-el` 0.1.12 → 0.1.13
- `byg-kontrol` 0.9.1 → 0.10.0
- `byg-maler` 0.1.7 → 0.1.8
- `byg-murer` 0.1.7 → 0.1.8
- `byg-statik` 0.3.1 → 0.3.2
- `byg-toemrer` 0.1.7 → 0.1.8
- `byg-ventilation` 0.1.8 → 0.1.9
- `byg-vvs` 0.1.8 → 0.1.9

### parallel-skrivning (byg, byg-bim, byg-el, byg-kontrol, byg-maler, byg-murer, byg-statik, byg-toemrer, byg-ventilation, byg-vvs)
Parallelitet og revisionsstyring: én skriver pr. fil i sagerne (skriveret pr. fag håndhævet af hooken), forslag til grænseflader, risici, kontrolplan og ejendomskort, der flettes på rækkeniveau ved godkendelse (med konfliktstop), lokalt git-repo i byg-sager/ med commits pr. aflevering, dom og fletning og en diff til kontrollens forsøg 2–3. I repoet: versionsnoter og scripts/udgiv.py i stedet for versionshævning i grenene.
