---
name: spoerg
description: Stil et hurtigt fagspørgsmål til én fagagent – med uafhængig kvalitetskontrol (stikprøve, el, statik og sikkerhedsfunktioner altid).
argument-hint: "<fag> <spørgsmål>  (fag: vvs, el, murer, ventilation, maler, toemrer)"
disable-model-invocation: true
---

Fagspørgsmål: $ARGUMENTS

1. Find faget (vvs, el, murer, ventilation, maler, toemrer) og den tilhørende fagagent. Er faget uklart, så vælg ud fra spørgsmålet og sig hvilket.
2. Opret en lille sag `byg-sager/<ÅÅÅÅ-MM-DD>-spoergsmaal-<emne>/` med en kort `projektgrundlag.md` (spørgsmålet og de oplysninger, brugeren har givet). Gælder spørgsmålet en ejendom med et ejendomskort i `byg-sager/ejendomme/`, så skriv `**Ejendom:** <sti>` i projektgrundlaget, og giv stien med i fag- og kontrolkaldet.
3. Kald fagagenten med `LEVERANCE: <sag-id>/<fag-id>/01` og `KONTROLNIVEAU: stikprøve` (ingen `FASE:`-linje). Brug `fuld`, hvis svaret fastlægger eller ændrer en sikkerhedsfunktion (fx sikkerhedsudstyr, el-beskyttelse eller bærende konstruktion), og `let` for el og statik, som altid kontrolleres. Kald derefter kontrolagenten i forgrunden efter skill `kvalitetskontrol`. Afviser hooken kontrolkaldet, fordi leverancen ikke er udtaget til stikprøve, er svaret afleveret uden kontrol. Hører spørgsmålet til en eksisterende sag, gælder sagens kontrolniveau (`let` eller `fuld`), ikke stikprøve.
4. Svar brugeren kort med svaret og de vigtigste forbehold, og skriv, om det er godkendt af kontrollen eller "Ikke kvalitetskontrolleret (stikprøve, ikke udtaget)". Kræver svaret flere fag, så foreslå `/byg:nyt-projekt`.
5. Høst sagen (`references/viden-og-forankring.md`): nye fakta om huset går til ejendomskortet, og generaliserbar læring går til videnbanken efter brugerens accept.
