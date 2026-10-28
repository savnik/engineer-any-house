---
name: nyt-fag
description: Opret et nyt fag – fagagent, videnbase, modsvarende kontrolagent og kontrolviden – efter skabelonen i Engineer Any House-repoet.
argument-hint: "<fag-id> [fagnavn]"
disable-model-invocation: true
---

Opret et nyt fag: $ARGUMENTS

1. Interview brugeren kort: fagområde og afgrænsning, typiske opgaver, kerneprincipper, autorisations- og myndighedskrav, vigtigste normer og anvisninger, typiske fejl (til kontrollens fejlkatalog).
2. Research normgrundlaget, og markér hvert punkt V (verificeret med kilde og dato) eller T (skal verificeres).
3. Arbejder brugeren i Engineer Any House-repoet: kør `python3 scripts/nyt_fag.py <fag-id> "<Fagnavn>" <agentnavn>` og udfyld de genererede filer (fagagent, videnbase, kontrolagent, `kontrol-viden/references/fag/<fag-id>.md`). Scriptet registrerer faget i marketplace, byg-team og hookens fagregister.
4. Uden repo: skriv udkastene til `byg-nyt-fag/<fag-id>/` i arbejdsmappen med samme struktur, og forklar, hvordan de lægges ind i repoet.
5. Kør `python3 scripts/valider.py` og fagets evals, før faget tages i brug. Et nyt fag er ikke færdigt uden sin kontrolagent.
