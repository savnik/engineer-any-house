---
name: spoerg
description: Stil et hurtigt fagspørgsmål til én fagagent – med uafhængig kvalitetskontrol af svaret.
argument-hint: "<fag> <spørgsmål>  (fag: vvs, el, murer, ventilation, maler, toemrer)"
disable-model-invocation: true
---

Fagspørgsmål: $ARGUMENTS

1. Find faget (vvs, el, murer, ventilation, maler, toemrer) og den tilhørende fagagent. Er faget uklart, så vælg ud fra spørgsmålet og sig hvilket.
2. Opret en lille sag `byg-sager/<ÅÅÅÅ-MM-DD>-spoergsmaal-<emne>/` med en kort `projektgrundlag.md` (spørgsmålet og de oplysninger, brugeren har givet).
3. Kald fagagenten med `LEVERANCE: <sag-id>/<fag-id>/01`, og kør kontrol-loopet efter skill `kvalitetskontrol`.
4. Svar brugeren kort med det godkendte svar og de vigtigste forbehold. Kræver svaret flere fag, så foreslå `/byg:nyt-projekt`.
