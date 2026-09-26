---
name: erfaring
description: Høst erfaringer og RCA-læring fra en sag og forankr det accepterede i videnbanken og forankringskøen.
argument-hint: "[sag-id eller sti til sagsmappe]"
disable-model-invocation: true
---

Høst erfaringer fra sagen: $ARGUMENTS

Følg `${CLAUDE_PLUGIN_ROOT}/skills/projektleder/references/viden-og-forankring.md`:
1. Læs `erfaringer.md`, beslutningsloggen, domme og RCA'er i sagsmappen.
2. Formulér kandidater som erfaringsblade (Situation/Problem/Løsning, Grundlag, Gyldighed, Status) og sortér dem: sagsspecifik, videnbank eller kanon-kandidat. RCA'er giver altid mindst ét forslag efter årsagskategorien.
3. Vis kandidaterne kort for brugeren, og gem kun det accepterede i `${CLAUDE_PLUGIN_DATA}/videnbank/` (erfaringsblade, `forankringskoe.md`, `sager.md`).
4. Kanon-kandidater skrives med målfil og konkret forslag til ny tekst, så de kan indarbejdes i repoet. Forslaget skal være anonymiseret og generaliseret (ingen sag-id, adresse, navne, firmaer, datoer, beløb eller citater fra sagen – se "Anonymisering før kanon"). Repoet er offentligt.
