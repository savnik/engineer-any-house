---
byg-electrical: patch
---
El-agenten afleverer bilag og revisioner mere fuldstændigt:

- **Bilag og PDF (schematic.md).** Kan agenten ikke selv køre diagramgeneratoren, skriver den en eksportspecifikation (PDF-side = tegningens viewBox, via HTML-side med `@page`) og en tælleliste i notatet. Projektlederen kontrollerer PDF'en mod listen før kontrol. En SVG printet direkte bliver beskåret.
- **Revision (electrician.md, uden for den fælles protokol).** Revisionsnummer og dato opdateres alle steder (notat, scriptets og tegningens titelfelt), og afledte filer rettes med. Kilder efterprøvet af kontrollen skrives som efterprøvet.
- **Tjekliste før aflevering** har fået punkter for titelfeltets revision og PDF-specifikationen.
