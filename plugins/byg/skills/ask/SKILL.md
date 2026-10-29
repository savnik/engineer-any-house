---
name: ask
description: Stil et hurtigt fagspørgsmål til én fagagent – med uafhængig kvalitetskontrol (stikprøve, el, statik og sikkerhedsfunktioner altid).
argument-hint: "<fag> <spørgsmål>  (fag: plumbing, electrical, masonry, ventilation, painting, carpentry, structural, architecture, landscape)"
disable-model-invocation: true
---

Fagspørgsmål: $ARGUMENTS

1. Find faget (vvs, el, murer, ventilation, maler, toemrer) og den tilhørende fagagent. Er faget uklart, så vælg ud fra spørgsmålet og sig hvilket.
2. Opret **ingen** sagsmappe i `byg-cases/`. Spørgsmål er midlertidige: skal der bruges filer (beregninger, udtræk, bilag), lægges de i `~/byg-tmp/<ÅÅÅÅ-MM-DD>-<emne>/` sammen med en kort `project-basis.md` (spørgsmålet og de oplysninger, brugeren har givet). Gælder spørgsmålet en ejendom med et ejendomskort i `byg-cases/properties/`, så skriv `**Ejendom:** <sti>` i projektgrundlaget, og giv stien med i fag- og kontrolkaldet. Hører spørgsmålet til en eksisterende sag, så brug den sags mappe og leverance-ID i stedet.
3. Kald fagagenten med `DELIVERABLE: <emne-id>/<trade-id>/01` (emne-id = tmp-mappens navn) og `REVIEW-LEVEL: sample` (ingen `PHASE:`-linje). Brug `full`, hvis svaret fastlægger eller ændrer en sikkerhedsfunktion (fx sikkerhedsudstyr eller el-beskyttelse), og `light` for el og statik, som altid kontrolleres. Spørgsmål om bærende konstruktioner kontrolleres med `light`: fagagenten tjekker først sine rammer (`frames.md`) og svarer kort, hvis situationen er en standardsituation. Kald derefter kontrolagenten i forgrunden efter skill `quality-review`. Afviser hooken kontrolkaldet, fordi leverancen ikke er udtaget til stikprøve, er svaret afleveret uden kontrol. Hører spørgsmålet til en eksisterende sag, gælder sagens kontrolniveau (`light` eller `full`), ikke stikprøve.
4. Svar brugeren kort med svaret og de vigtigste forbehold, og skriv, om det er godkendt af kontrollen eller "Ikke kvalitetskontrolleret (stikprøve, ikke udtaget)". Kræver svaret flere fag, så foreslå `/byg:new-project`.
5. Høst svaret (`references/knowledge-and-anchoring.md`): nye fakta om huset går til ejendomskortet, og generaliserbar læring går til videnbanken efter brugerens accept. Skal svaret gemmes permanent, løftes det ind i hovedsagen (leverance eller beslutningslog) eller i en branch-sag; tmp-mappen må slettes bagefter.
