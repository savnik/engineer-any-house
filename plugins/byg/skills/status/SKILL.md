---
name: status
description: Vis status for en byggesag – fase, næste skridt, åbne spørgsmål og kvalitetskontrol pr. leverance. Bruges også til at fortsætte en sag i en ny session.
argument-hint: "[sag-id eller sti til sagsmappe]"
disable-model-invocation: true
---

Giv en kort status for sagen: $ARGUMENTS (er intet angivet: list sagerne i `byg-sager/` – undtagen mappen `ejendomme/` – og spørg, hvilken).

1. Læs `status.md`, de seneste ca. 15 linjer af `kvalitet/kontrollog.md`, de seneste ca. 15 linjer af `beslutningslog.md` og `aendringer.md` samt RCA'er, der ikke er afsluttet. Fra ejendomskortet (`**Ejendom:**` i `status.md`) læses kun "Fælles" og "Åbne spørgsmål". Læs ikke fagnotaterne, dommene (`kvalitet/*.json`) eller andre sager nu; de læses målrettet, når en opgave kræver det. Hele statussen skal kunne laves med højst ca. 8 fillæsninger.
2. Svar kort: fase, seneste beslutninger, næste 3 skridt, åbne spørgsmål til brugeren, og en tabel over leverancer med forsøg og dom (godkendt / afvist runde r/2 forsøg n/2 / stoppet – venter på brugerens valg).
3. Markér leverancer, der mangler kontrol, fund der venter på brugerens beslutning, og om sagen mangler erfaringshøst (`**Erfaringshøst:** ikke udført` på en afsluttet sag).
4. Er det en ny session på en eksisterende sag, så fortsæt derefter med brugerens næste opgave som projektleder (skill `projektleder`) ud fra sagsmappen.
