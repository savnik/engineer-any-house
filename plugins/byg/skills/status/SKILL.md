---
name: status
description: Vis status for en byggesag – fase, næste skridt, åbne spørgsmål og kvalitetskontrol pr. leverance.
argument-hint: "[sag-id eller sti til sagsmappe]"
disable-model-invocation: true
---

Giv en kort status for sagen: $ARGUMENTS (er intet angivet: list sagerne i `byg-sager/` og spørg, hvilken).

1. Læs `status.md`, `beslutningslog.md`, `kvalitet/kontrollog.md` og evt. RCA'er i sagsmappen.
2. Svar kort: fase, seneste beslutninger, næste 3 skridt, åbne spørgsmål til brugeren, og en tabel over leverancer med forsøg og dom (godkendt / afvist runde r/3 forsøg n/3 / stoppet med RCA og forbedring).
3. Markér leverancer, der mangler kontrol, og fund der venter på brugerens beslutning.
