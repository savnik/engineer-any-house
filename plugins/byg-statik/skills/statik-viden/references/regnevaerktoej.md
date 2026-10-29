# Statiker – regneværktøj (`statik.py`)

**Snitkræfter, reaktioner og nedbøjninger regnes altid i FEM-modellen (`fem.py`, se `fem.md`)** – også for en simpel bjælke. `statik.py` bruges til lastopgørelse, tværsnitsværdier, udnyttelse efter Eurocode, anden aritmetik og som uafhængig håndkontrol af FEM-resultatet.

**Al regning sker med værktøjerne** – også summer, opland, enhedsomregning og håndformler. Et tal i en leverance, der hverken er aflæst i en kilde eller kommer fra en kørsel, er en fejl. Værktøjet er rent Python-standardbibliotek og skriver ingen filer.

Kør: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/statik-viden/scripts/statik.py <kommando> …`. Hvert output er JSON og starter med `kommando` (med absolut sti), så bilaget kan genkøres. Udtryk skrives med decimalpunktum (`3.6`); rene tal må have decimalkomma (`3,6`).

## Kommandoer
| Kommando | Formål | Eksempel |
|---|---|---|
| `test` | Selvtest: profiler mod tabelværdier, kendte facitter, `calc` | `statik.py test` |
| `calc` | Al anden aritmetik (+ − × ÷ potens, sqrt, sin/cos/tan, radians, log, exp, min, max, pi) | `statik.py calc "q*L**2/8" --var q=17.49 --var L=3.6` |
| `load` | Lastopgørelse: summér lag (kN/m² eller tykkelse×tyngde), × faktor, × opland → linjelast | `statik.py load --layers "tegl:0.6" --layers "spær:0.045*0.195*5/0.9" --factor "1/cos(radians(45))" --tributary 1.8` |
| `beam` | Simpelt understøttet bjælke i stål, træ eller limtræ: reaktioner, M, V, udnyttelse (6.10a og 6.10b), nedbøjning efter DK NA | se nedenfor |
| `pressure` | Kontakttryk under vederlag eller fundament mod en regningsmæssig styrke, du har kilde til | `statik.py pressure --load 31.5 --area 0.108*0.1 --strength 2.5 --unit MPa` |
| `profiles` | Tværsnitsværdier for IPE/HEA/HEB (regnet fra geometrien) | `statik.py profiles --series HEB` |

### `beam`
- Laster karakteristisk: `--g`/`--q` (kN/m) og/eller `--g-area`/`--q-area` (kN/m²) × `--tributary` (m); `--self-weight`; punktlaster `--point G:Q:a` (kN, kN, m fra venstre vederlag, kan gentages).
- Stål: `--material S235|S355 --profile HEB160`. Træ: `--material C18|C24|GL24h|GL30c|GL32h --width 45 --height 195`.
- Træ: `--load-duration` for den variable last (`permanent`, `long`, nyttelast `medium`, sne `short`, vind `instantaneous`) og `--service-class 1|2`.
- Nedbøjning: egenlast w_fin ≤ L/`--limit` (400), variabel last w_inst ≤ L/`--limit-q` (400; vind 250).
- Koefficienter kan overskrives: `--kfi`, `--gamma-g`, `--gamma-g-a`, `--gamma-q`, `--gamma-m`, `--psi2`.

## Indbyggede værdier
| Værdi | Standard | Kilde og status |
|---|---|---|
| 6.10a: 1,2·KFI·G · 6.10b: KFI·(1,0·G + 1,5·Q) | KFI 1,0 (CC2, boliger) | V – EN 1990 DK NA:2024 tabel A1.2(B+C) |
| ψ2 bolig | 0,2 | V – EN 1990 DK NA:2024 tabel A1.1 |
| γ_M træ / limtræ / γ_M0 stål | 1,35 / 1,30 / 1,10 | V – DK NA EN 1995-1-1:2024 tabel 2.3; EN 1993-1-1:2019 6.1(1) |
| k_mod, k_def, k_cr = 0,67 | se `normgrundlag.md` | T – EN 1995-1-1 (betalingsstandard) |
| C18, C24, GL24h, GL30c, GL32h (f_m,k, f_v,k, E_0,mean) | i scriptet | T – EN 338 / EN 14080 (sekundære kilder) |
| S235/S355 f_y, E = 210 000 MPa | t ≤ 16 mm | T – EN 10025-2 |
| IPE/HEA/HEB | geometri h, b, t_w, t_f, r | Selvtest mod tabel-I_y (afvigelse < 1,5 %) |

## Grænser – det regner værktøjet IKKE
Kipning og sideafstivning (advarsel ved træ med h/b > 4) · udnyttelse af kontinuerlige bjælker, udkragninger og rammer (snitkræfterne kommer fra `fem.py`; udnyttelsen regnes med `calc` og formel med kilde) · søjler og stabilitet · samlinger, beslag og bjælkesko · brand · svingninger · murværkets og jordens styrke (skal komme fra kilde eller statiker) · snesække og formfaktorer (input via `load --factor`). Står opgaven her, så regn det ikke på anden vis: beskriv den, og overlad den til den ansvarlige statiker.

## Bilaget (`fagnotater/statik-bilag.md`)
For hver kørsel: formål (én linje) · kommandoen præcis som udskrevet · de relevante resultatlinjer · kilde til hvert input (måling, tegning, antagelse med HP-STAT-1). Afslut med en tabel over de afgørende resultater og deres udnyttelse.
