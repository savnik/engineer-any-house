---
type: llm
---

PASS hvis svaret opfylder ALLE disse punkter:
1. Beskriver en fast fremgangsmåde i trin: tegningerne afkodes grundigt (alle mål, rum, åbninger, koter, tekster) FØR modellen bygges, og afkodningen kontrolleres (fx mål mod tegningens geometri, målkæder der summerer, kalibrering/målestok).
2. Beskriver en uafhængig sammenligning af originaltegningen med samme visning tegnet fra modellen (overlay/side om side) udført af en anden end den, der byggede modellen, og at fundne afvigelser sendes retur og rettes i et begrænset antal runder.
3. Siger at påskrevne mål går forud for at måle/skalere i scanningen, og at mål/elementer får kilde- eller usikkerhedsmærkning (fx skøn markeret), samt at tegningen ikke nødvendigvis svarer til det udførte hus (opmålingsliste/kontrolmål på stedet).
4. Nævner IFC-formatet konkret (fx IFC4) og en form for validering af filen (fx buildingSMART-regler/validering, IDS eller kontrol af struktur, materialer og rum), og spørger om/nævner formål eller detaljeringsniveau (LOIN) og hvad arkitekten skal bruge.

FAIL hvis svaret foreslår at bygge modellen direkte ved at "aflæse" tegningerne uden afkodning og uafhængig sammenligning, eller lover millimeterpræcision fra scannede tegninger uden forbehold.
