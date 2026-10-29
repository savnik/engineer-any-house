---
name: lessons
description: Høst erfaringer og RCA-læring fra en sag – husets fakta til ejendomskortet, fagviden til videnbanken og forankringskøen.
argument-hint: "[sag-id eller sti til sagsmappe]"
disable-model-invocation: true
---

Høst erfaringer fra sagen: $ARGUMENTS

Følg `${CLAUDE_PLUGIN_ROOT}/skills/project-manager/references/knowledge-and-anchoring.md`:
1. Læs `lessons.md`, beslutningsloggen, domme og RCA'er i sagsmappen.
2. Før sagens nye fakta om huset ind i ejendomskortet (`**Ejendom:**` i `status.md`) med kilde og dato.
3. Formulér kandidater som erfaringsblade (Situation/Problem/Løsning, Grundlag, Gyldighed, Status) og sortér dem: sagsspecifik, videnbank eller kanon-kandidat. RCA'er giver altid mindst ét forslag efter årsagskategorien.
4. Vis kandidaterne kort for brugeren, og gem kun det accepterede i `${CLAUDE_PLUGIN_DATA}/knowledge-bank/` (`lessons/<trade-id>.md`, `anchoring-queue.md`, `cases.md`).
5. Kanon-kandidater skrives med målfil og konkret forslag til ny tekst, så de kan indarbejdes i repoet. Forslaget skal være anonymiseret og generaliseret (ingen sag-id, adresse, navne, firmaer, datoer, beløb eller citater fra sagen – se "Anonymisering før kanon"). Repoet er offentligt.
6. Skriv datoen i linjen `**Erfaringshøst:**` i sagens `status.md`.
