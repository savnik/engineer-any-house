---
byg-bim: minor
byg-structural: patch
byg-plumbing: minor
---
Eksempelhuset er nu det samme i BIM og FEM. BIM: nyt afsnit `ovenlys` til tagvinduer i tagfladen, `farve` på systemer, `bim.py eksport --gennemsigtig/--alfa` til gennemsigtige facader og en komplet VVS-installation i eksemplet (centralvarme, radiatorer, varmtvandsbeholder, koldt og varmt brugsvand, spildevand til brønd). Statik: nyt FEM-eksempel `fem-example-house.yaml` med husets vægge og dæk. Nyt felt `spaer` på tage: spær, veksler om ovenlys og skorsten samt hanebånd som IfcMember i taget, og eksemplet viser spærkonstruktionen gennem den gennemsigtige tagflade. FEM-eksemplet: bjælkelaget er nu leddet på murkronen, og dækket over kælderen holder kældervæggenes top. Det fjerner de urealistiske spændingsspring ved væghjørnerne. fem.md beskriver begge modelleringsregler. VVS: ny reference `schematic.md` med indhold, layout, farver (samme som BIM-systemerne), SVG-symbolbibliotek og tjekliste, så plumber kan tegne et principdiagram over varme, brugsvand og afløb, samt et færdigt eksempel for eksempelhuset (`assets/principdiagram-eksempelhus.svg`).
