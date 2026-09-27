---
description: VVS-mesteren skal gennemgå en pillekedels sikkerhed som ét system (fejltilstande, uafhængige barrierer, sikkerhedskæde) og ikke kun svare på, om en komponent kan udgå.
tags: [vvs, sikkerhed, varme, rca]
max_turns: 20
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite, WebSearch, WebFetch]
---

Vi har et automatisk pillefyr fra ca. 2010 (12 kW, kedel 43 l, overkogssikring ved 100 °C). Fyrets styring har ét blandeventilmodul med "maks. fremløb 50 °C", og det forsyner både radiatorer og gulvvarme i PEX af ukendt klasse. Ved kedeltemperatur over 90 °C laver fyret en varmedump, hvor alle pumper starter og blandeventilerne åbnes. Vi skal have en ny 160 l varmtvandsbeholder med spiral, ladepumpe med tyngdekraftsbremse og elpatron til sommerdrift. Vores VVS'er foreslår at droppe den ekstra blandeventil og sikkerhedstermostat, der var planlagt på radiatorkredsen, fordi fyret "allerede begrænser til 50 °C". Kan den udgå, og hvad skal der ellers til omkring kedlen?
