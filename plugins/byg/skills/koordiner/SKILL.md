---
name: koordiner
description: Sæt fagene i gang på en sag med uafhængig kvalitetskontrol af hver leverance og saml en kontrolleret plan.
argument-hint: "[sag-id eller sti til sagsmappe]"
disable-model-invocation: true
---

Koordinér sagen: $ARGUMENTS (er intet angivet: den senest ændrede mappe i `byg-sager/`, og bekræft med brugeren).

1. Læs `${CLAUDE_PLUGIN_ROOT}/skills/projektleder/SKILL.md` (fase 4–6), `references/koordinering.md` og sagens `projektgrundlag.md` og `status.md`.
2. Er projektgrundlaget ikke accepteret, så stop og kør interviewet færdigt først.
3. Send fagforespørgsler med leverance-ID'er; kør kontrol-loopet for hver leverance efter skill `kvalitetskontrol` (højst 2 forsøg pr. runde; derefter eskalering til brugeren; ny runde med RCA kun efter brugerens 'Ny runde <id>').
4. Integrér: grænseflader, konflikter, tidsplan, risici, kontrolplan, myndighed og aftaler; få den samlede plan kontrolleret af `projekt-kontrol`.
5. Præsentér kort for brugeren, og opdatér `status.md`.
