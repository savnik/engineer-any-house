---
name: nyt-projekt
description: Start et nyt byggeprojekt – interview, sagsmappe, kontrolleret projektgrundlag og fagplan.
argument-hint: "[kort beskrivelse af projektet]"
disable-model-invocation: true
---

Start et nyt projekt som byg-projektleder. Brugerens beskrivelse: $ARGUMENTS

1. Læs `${CLAUDE_PLUGIN_ROOT}/skills/projektleder/SKILL.md` og følg faserne 1–3.
2. Find ejendommen: findes der allerede et ejendomskort i `byg-sager/ejendomme/`, så læs det, og spørg kun om det, der mangler. Ellers oprettes det (`references/sagsmappe.md`).
3. Interview efter `references/interview.md` (blokke A–F), til Definition of Ready er opfyldt. Husets fakta skrives i ejendomskortet med kilde og dato (via forslag + `bim.py merge`, hvis kortet er genereret fra en BIM-hovedmodel).
4. Opret sagsmappen efter `references/sagsmappe.md` med linjen `**Ejendom:** <sti>`, skriv `projektgrundlag.md`, og få det kontrolleret af `projekt-kontrol` efter skill `kvalitetskontrol` (`LEVERANCE: <sag-id>/projekt/01`).
5. Vis brugeren projektgrundlaget og fagplanen kort, og spørg om accept, før fagene sættes i gang (`/byg:koordiner`).
