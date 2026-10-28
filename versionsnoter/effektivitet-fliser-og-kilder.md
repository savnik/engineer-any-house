---
byg-bim: minor
byg-kontrol: patch
byg-anlaeg: patch
byg-arkitekt: patch
byg-el: patch
byg-maler: patch
byg-murer: patch
byg-statik: patch
byg-toemrer: patch
byg-ventilation: patch
byg-vvs: patch
---
Mindre genlæsning. `bim.py sammenlign` skriver nu `fliser.md` og `fliser.json`, som siger, hvilke fliser der skal gennemgås. Tomme fliser springes over. Med `--forrige <forrige rundes mappe>` springes fliser over, hvis modeltegningen er pixel for pixel uændret siden forrige runde. Fliser med automatiske fund gennemgås altid. Sammenligneren læser kun de markerede fliser og fører de uændrede i `daekning.fliser_uaendret`. I en prøve på en lokal sag faldt det, der skulle gennemgås i runde 2 med uændret model, fra 16 til 5 fliser (V1) og fra 25 til 3 (V2). Fællesprotokollen har fået et kilderegister pr. fag og sag, `bilag/<fag-id>/kilder.md` (URL, dato, udgave og side/§, parafrase). Fagene søger i alle fags registre, før de henter en side, og kan genbruge en linje med "jf. kilderegister". Kontrollen må kun bruge registret til at finde kilden og efterprøver stadig selv. Målingen viste, at 23 % af sidehentningerne gentog en side, der allerede var hentet i en anden kørsel. `scripts/forbrug.py` viser nu forbrug pr. agenttype, billed-, PDF- og Edit-tal pr. kørsel målt mod protokollens lofter, og gentagne hentninger delt op i samme kørsel og på tværs af kørsler.
