---
name: status
description: Vis status for en byggesag – fase, næste skridt, åbne spørgsmål og kvalitetskontrol pr. leverance. Bruges også til at fortsætte en sag i en ny session.
argument-hint: "[sag-id eller sti til sagsmappe]"
disable-model-invocation: true
---

Giv en kort status for sagen: $ARGUMENTS (er intet angivet: list sagerne i `byg-sager/` og spørg, hvilken).

1. Læs `status.md` og `kvalitet/kontrollog.md`, de seneste ca. 15 linjer af `beslutningslog.md` og `aendringer.md` samt RCA'er, der ikke er afsluttet. Læs ikke fagnotaterne nu; de læses målrettet, når en opgave kræver det.
2. Svar kort: fase, seneste beslutninger, næste 3 skridt, åbne spørgsmål til brugeren, og en tabel over leverancer med forsøg og dom (godkendt / afvist runde r/3 forsøg n/3 / stoppet med RCA og forbedring).
3. Markér leverancer, der mangler kontrol, og fund der venter på brugerens beslutning.
4. Er det en ny session på en eksisterende sag, så fortsæt derefter med brugerens næste opgave som projektleder (skill `projektleder`) ud fra sagsmappen.
