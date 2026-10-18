---
byg: minor
byg-kontrol: minor
byg-bim: minor
---
Sager som branches: `byg-sager/` holder kun permanente data (hovedsager, aktive branch-sager `<hovedsag>--<emne>/`, `ejendomme/`, `arkiv/`). Spørgsmål opretter ingen sagsmappe – midlertidige filer i `~/byg-tmp/` (gaten finder sager og RCA'er der og håndhæver én skriver pr. fil). BIM-hovedmodellen ligger i hovedsagen; en branch-sag har sine forslag lokalt (`bim.py forslag … --ud <branch>/bim/forslag`, basis relativ med sha256) og flettes ind ved godkendelse.
