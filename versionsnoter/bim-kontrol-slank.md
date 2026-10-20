---
byg-bim: minor
byg-kontrol: minor
byg: patch
---
BIM: `bim.py tjek` kontrollerer sporbarhed (kilde uden reference, K uden leverance-ID, A uden usikkerhed, `--notat` for modelnotatets andel af kilde A). Nyt kontrolniveau `værktøj` for ren tegningsimport og geometri: hooken godkender leverancen, når bim-sammenligneren melder `resultat: ok` og et rent `tjek`, uden bim-kontrol. bim-kontrol bruges, når modellen indarbejder andre fags indhold eller er beslutningsgrundlag.
