---
byg-electrical: patch
---
`el.py` rettet: `ikmin` har `--feeder-insulation pvc/xlpe` (stikledningen blev altid regnet som XLPE 90 °C), og næste tværsnit regnes nu med samme stikledningstemperatur og isolering. `el.py panel` giver advarsel ved sikring over 13 A foran 10/13 A-stikkontakter og over 16 A foran 16 A (BEK 1082 § 45, nyt felt `stikkontakt_a`, 13 A antages ved `stik`). `calc-tools.md` dokumenterer, at modstanden regnes efter IEC 60228 pr. tværsnit (ρ70 ≈ 0,0217–0,0222), lidt under håndregningskonventionen 0,0225.
