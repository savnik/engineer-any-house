---
byg: patch
byg-anlaeg: patch
byg-arkitekt: patch
byg-bim: patch
byg-el: patch
byg-kontrol: patch
byg-maler: patch
byg-murer: patch
byg-statik: patch
byg-team: patch
byg-toemrer: patch
byg-ventilation: patch
byg-vvs: patch
---
Projektet hedder nu Engineer Any House. Marketplace hedder `engineer-any-house` (før `byg-eksperter`), og GitHub-repoet bliver `savnik/engineer-any-house`. Plugin-, agent- og skillnavne er uændrede (`byg`, `byg-kontrol`, `byg-vvs` …), og sagsmapper i `byg-sager/` virker som før. Installer fra den nye marketplace med `claude plugin marketplace add <sti>/engineer-any-house` og `claude plugin install byg-team@engineer-any-house`. Claude Code navngiver pluginernes datamapper efter marketplace, så videnbanken og kontroltilstanden skal kopieres fra `~/.claude/plugins/data/<plugin>-byg-eksperter` til `<plugin>-engineer-any-house` ved skiftet. `scripts/tjek_data.py` læser private termer og sagsmapper fra `~/.config/engineer-any-house/` og stadig fra den gamle `~/.config/byg-eksperter/`.
