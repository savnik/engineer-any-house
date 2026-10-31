---
byg-bim: patch
---
BIM: `bim.py export` skriver nu farverne korrekt til glTF (IFC-farver er sRGB, glTF lineære), så tegl, træ og beton ikke længere ser udvaskede og pastelagtige ud i 3D-visningen. Materialerne får navn efter IFC-stilen, rør og kanaler i systemfarver lyser svagt, så de tynde rør kan ses, og standarddækkevnen for `--transparent` er sænket fra 0,25 til 0,15, så det indvendige står tydeligere. 3D-demoen har tættere kamera, retningsbestemt lys og kraftigere skygger.
