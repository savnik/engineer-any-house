---
byg-kontrol: minor
byg: minor
byg-anlaeg: patch
byg-arkitekt: patch
byg-bim: patch
byg-el: patch
byg-maler: patch
byg-murer: patch
byg-statik: patch
byg-toemrer: patch
byg-ventilation: patch
byg-vvs: patch
---
Ærlighed om fravær og dækning. "Ikke fundet" behandles som ukendt, ikke som "findes ikke": det står i fællesprotokollen, og i kontrolprotokollen er en fraværskonklusion uden kilde nu et fund. Et delvist besvaret notat skal skrive "Delvist besvaret – mangler: …". Kontrollens dom har et nyt felt, `ikke_kontrolleret`. Hooken validerer og gemmer det, og ved godkendelse siger den, hvad godkendelsen ikke dækker. Feltet føres også i kontrolloggen. Projektlederen laver en opgørelse ved G1–G3: hvert succeskriterie, krav, ramme og åbent spørgsmål markeres besvaret, delvis eller åben, og gaten passeres ikke med punkter, brugeren ikke har accepteret. Det giver kontrolpunkt 1e i kontrol-projekt@1.4. RCA-skabelonen kræver "utilstrækkeligt grundlag", når evidensen mangler.
