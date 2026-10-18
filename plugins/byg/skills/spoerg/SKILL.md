---
name: spoerg
description: Stil et hurtigt fagspørgsmål til én fagagent – med uafhængig kvalitetskontrol af svaret.
argument-hint: "<fag> <spørgsmål>  (fag: vvs, el, murer, ventilation, maler, toemrer)"
disable-model-invocation: true
---

Fagspørgsmål: $ARGUMENTS

1. Find faget (vvs, el, murer, ventilation, maler, toemrer) og den tilhørende fagagent. Er faget uklart, så vælg ud fra spørgsmålet og sig hvilket.
2. Opret **ingen** sagsmappe i `byg-sager/`. Spørgsmål er midlertidige: skal der bruges filer (beregninger, udtræk, bilag), lægges de i `~/byg-tmp/<ÅÅÅÅ-MM-DD>-<emne>/` sammen med en kort `projektgrundlag.md` (spørgsmålet og de oplysninger, brugeren har givet). Gælder spørgsmålet en ejendom med et ejendomskort i `byg-sager/ejendomme/`, så skriv `**Ejendom:** <sti>` i projektgrundlaget, og giv stien med i fag- og kontrolkaldet. Hører spørgsmålet til en eksisterende sag, så brug den sags mappe og leverance-ID i stedet.
3. Kald fagagenten med `LEVERANCE: <emne-id>/<fag-id>/01` (emne-id = tmp-mappens navn) og `KONTROLNIVEAU: let`. Brug `fuld`, hvis svaret fastlægger eller ændrer en sikkerhedsfunktion (fx sikkerhedsudstyr, el-beskyttelse eller bærende konstruktion). Kør kontrol-loopet efter skill `kvalitetskontrol` i forgrunden.
4. Svar brugeren kort med det godkendte svar og de vigtigste forbehold. Kræver svaret flere fag, så foreslå `/byg:nyt-projekt`.
5. Høst svaret (`references/viden-og-forankring.md`): nye fakta om huset går til ejendomskortet, og generaliserbar læring går til videnbanken efter brugerens accept. Skal svaret gemmes permanent, løftes det ind i hovedsagen (leverance eller beslutningslog) eller i en branch-sag; tmp-mappen må slettes bagefter.
