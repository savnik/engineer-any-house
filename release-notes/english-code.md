---
byg: major
byg-review: major
byg-bim: major
byg-team: major
byg-ventilation: major
byg-landscape: major
byg-architecture: major
byg-electrical: major
byg-painting: major
byg-masonry: major
byg-structural: major
byg-carpentry: major
byg-plumbing: major
byg-data: patch
---
Koden er oversat til engelsk: Python-moduler, funktioner, variabler, kommentarer og docstrings har engelske navne (fx `review_gate.py`, `bimlib/decode.py`, `femlib/shells.py`). CLI-kommandoer, flag og valgmuligheder er også engelske – fx `bim.py decode check`, `bim.py check … --draw`, `bim.py merge … --dry-run`, `fem.py calc … --no-files`, `fem.py result`, `statik.py beam --span …` og `bim.py draw … all --out …`. De gamle danske kommandonavne virker ikke længere. Resten af produktet er uændret dansk – hjælpetekster og al tekst til brugere og agenter, YAML/JSON-nøgler, og værdier i gemte data (domme, hændelser) er de samme som før.

Også navne er nu engelske: filnavne, plugins, agenter, skills, fag-id'er og markører. Plugins: byg-kontrol→byg-review, byg-anlaeg→byg-landscape, byg-arkitekt→byg-architecture, byg-el→byg-electrical, byg-maler→byg-painting, byg-murer→byg-masonry, byg-statik→byg-structural, byg-toemrer→byg-carpentry, byg-vvs→byg-plumbing. Agenter fx projektleder→project-manager (`claude --agent byg:project-manager`), statiker→structural-engineer, vvs-mester→plumber og `<fag>-kontrol`→`<trade>-review`; skills fx kvalitetskontrol→quality-review, tegningsimport→drawing-import, koordiner→coordinate og `<fag>-viden`→`<trade>-knowledge`. Fag-id'er: vvs→plumbing, el→electrical, murer→masonry, maler→painting, toemrer→carpentry, statik→structural, arkitekt→architecture, anlaeg→landscape, projekt→project. Sagsmappen hedder nu `byg-cases/` (før `byg-sager/`) med engelske filnavne: projektgrundlag.md→project-basis.md, beslutningslog.md→decision-log.md, fagnotater/→trade-notes/, forslag/→proposals/, kvalitet/kontrollog.md→quality/review-log.md, bilag/→attachments/, ejendomme/→properties/, erfaringer.md→lessons-learned.md, tilstand.json→state.json m.fl.; videnbanken hedder knowledge-bank/ (sager.md→cases.md). Markører i prompts: LEVERANCE:→DELIVERABLE:, FASE:→PHASE:, KONTROLNIVEAU: let|fuld→REVIEW-LEVEL: light|full, DESIGNGRUNDLAG:→DESIGN-BASIS:, GENFORSØG→RETRY, `<!-- GENERERET`→`<!-- GENERATED`, og godkendelsen "Godkend G2 <sag-id>" hedder nu "Approve G2 <case-id>". I repoet: eksamen/→exam/, faelles/→shared/, skabelon/→template/, versionsnoter/→release-notes/, ARKITEKTUR.md→ARCHITECTURE.md, og udgivelsesgrene hedder `release/<version>`.

Det kræver handling: afinstallér de gamle plugins og installér dem igen under de nye navne (fx `byg-plumbing` i stedet for `byg-vvs`). Eksisterende sagsmapper og videnbanker skal omdøbes til de nye mappe- og filnavne – der er ingen danske aliaser, så hooks og agenter genkender ikke de gamle navne. Regnemiljøet til statik flytter til `~/.local/share/byg-structural` og installeres igen automatisk ved første kørsel.
