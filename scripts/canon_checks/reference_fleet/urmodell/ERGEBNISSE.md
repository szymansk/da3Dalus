# Urmodell-Flotte — Ergebnisse (03.10.2026)

## Auftrag und Umfang

Der Maintainer wünschte eine Flotte aus allen Urmodellen. Zunächst nur die typischen Kombinationen,
je eine gängige Spannweite aus einer Webrecherche.

- **74 Urmodelle.** Gezählt sind alle Pfade des Auswahlgraphen, auf denen jede Antwort „typisch“
  bewertet ist (`combos.py`). Das sind 74, nicht 72: die erste Zählung hatte Pfade ohne Lage-Frage
  (Doppeldecker) anders bewertet.
- **Spannweiten:** `SPANNWEITEN.md`, `spannweiten.json`. Speed ist nach Bauart getrennt: Hotliner
  1700 mm, Hotwing 800 mm.
- **Generator:** `generate.py`. Er ist ein Prototyp für die Validierung, nicht der App-Generator (#1152).
  Die Bänder kommen aus `_reversa_sdd/calculations/auswahl/BAENDER.md`. Was dort keine Quelle hat,
  ist im Kopf von `generate.py` als D1–D8 erklärt. Ein Beispiel ist D8: Ein Nurflügel bekommt seine
  Masse aus der Flächenbelastung der Mission, weil der Massen-Fit auf Leitwerksmodellen beruht.
- **Kanonlauf:** `fleet_eval.py`, Ergebnis `fleet_results.csv`. Alle 74 laufen fehlerfrei durch.
  Die Seitenstabilität mit AVL rechnet `lateral_avl.csv` gegen.

## Leistung je Mission (Median)

| Mission | n | V_S [m/s] | (L/D)max | Sinken min [m/s] | SM-Ziel | SM [min … max] % MAC |
|---|---|---|---|---|---|---|
| trainer | 2 | 7,8 | 14,4 | 0,81 | 15 | 15,0 … 17,2 |
| park | 3 | 5,1 | 9,4 | 0,79 | 15 | 15,0 … 23,3 |
| sport | 7 | 8,4 | 18,9 | 0,63 | 10 | 6,3 … 10,0 |
| kunstflug | 3 | 9,1 | 13,4 | 1,03 | 3 | −0,3 … 3,9 |
| 3d | 2 | 8,4 | 12,3 | 1,03 | 3 | −0,2 … 5,2 |
| speed | 15 | 8,9 | 16,7 | 0,72 | 6,5 | 3,1 … 6,5 |
| elektrosegler | 8 | 6,6 | 19,0 | 0,45 | 10 | 10,0 … 12,7 |
| segel_trainer | 4 | 5,3 | 16,3 | 0,41 | 13,5 | 13,5 … 16,0 |
| thermik | 6 | 5,6 | 20,3 | 0,34 | 10 | 10,0 … 14,5 |
| hang | 21 | 6,7 | 18,5 | 0,46 | 8 | 4,9 … 10,7 |
| wurf | 3 | 4,5 | 14,2 | 0,41 | 6,5 | 5,3 … 8,6 |

Die Werte sind plausibel für Modelle, die „grundsätzlich fliegen“ sollen. Die Gleitzahlen der Segler
liegen unter denen echter Wettbewerbsmodelle. Ursache sind Rumpf, Profil-Platzhalter und die kleine
Reynoldszahl.

## Befunde

### B1 — Kleine SM-Ziele sind kleiner als die Neutralpunkt-Streuung

Der Generator legt den Schwerpunkt vor den **vorderen geometrischen** Neutralpunkt (Lehrbuch oder
Pappas), mit Abstand SM-Ziel. AVL liegt bei Mittel- und Tiefdeckern bis zu 7,8 % MAC weiter vorn. Ein
Beispiel ist der Kunstflug-Mitteldecker: Lehrbuch 42,4, Pappas 41,4, AVL 34,6 % MAC. Bei einem Ziel von
3 % wird damit eine Welt instabil (SM_min bis −3,8 %). Betroffen sind 3 Kunstflug- und 1 3D-Modell.

- **Ursache:** Die geometrischen Formeln kennen die Höhenlage des Leitwerks nicht. Beim Mitteldecker
  liegen Leitwerk und Tragflügel in einer Ebene, der Abwind wirkt voll. AVL rechnet das mit.
- **Folge für #1152:** Der Generator muss den Schwerpunkt gegen den vorderen Rand **aller** Welten
  legen. Dazu gehört AVL. Sonst verfehlt er bei kleinen Zielen die Stabilität. A11 fordert genau das.

### B2 — AeroBuildup-Neutralpunkt: Fehler nicht konstant, bis +29 % MAC

#1154 ging von etwa 10 % MAC aus. Die Flotte zeigt für AeroBuildup minus AVL:

- **mit Leitwerk (50):** −5,7 bis +29,3, Median +14,5 % MAC. Beim Trainer liegt AeroBuildup bei 76,5,
  AVL bei 51,5.
- **Nurflügel (24):** −5,8 bis −1,7, Median −4,1 % MAC. AeroBuildup liegt hier **vor** AVL.

Den vorderen Rand bildet bei Leitwerksmodellen 23-mal AVL, 24-mal das Lehrbuch und 3-mal Pappas. Ein
Werkzeug ist also nicht immer vorn. Das bestätigt, dass A11 Intervalle braucht.

### B3 — Seitenstabilität: die scharfe Einordnung hält auf der Flotte nicht

Am 03.10. wurde entschieden: C_nβ und Spiralkriterium bleiben scharf, weil Vorzeichen und Spiralurteil
**an zwei Flugzeugen** in beiden Methoden übereinstimmten. Auf 74 Flugzeugen gilt:

| Bauart | n | C_lβ AB/AVL | C_nβ AB/AVL | Spiralurteil uneinig |
|---|---|---|---|---|
| Normal / T / Kreuz | 39 | 0,52–1,11 | 0,41–1,14 | 1 |
| V-Leitwerk | 11 | 0,86–1,11 | 0,92–2,17 | 8 |
| Nurflügel mit Flosse/Winglet | 16 | 0,02–0,33 | 0,18–0,80 | 0 |
| Nurflügel ohne Flosse | 8 | −0,01–0,06 | −0,72–−0,02 | 7 |

Das Spiralurteil kippt bei 16 von 74 Flugzeugen. Das Vorzeichen von C_nβ kippt bei 8, alle sind
Nurflügel ohne Flosse.

**Ursache, durch Reproduktion belegt (`sweep_clb_repro.py`):** AeroBuildup kennt keinen
Pfeilungsbeitrag zu C_lβ. Getestet wurde ein reiner Flügel mit AR 7,7, NACA 0009 und C_L 0,4:

| Pfeilung, V-Form | C_lβ AeroBuildup | C_lβ AVL |
|---|---|---|
| 0°, 0° | +0,0011 | −0,0321 |
| 17°, 0° | +0,0012 | −0,0566 |
| 30°, 0° | +0,0013 | −0,0756 |
| 0°, 5° | −0,0798 | −0,1053 |

AeroBuildup erzeugt Rollstabilität nur aus geometrischer V-Form. Gepfeilte Flügel, also alle Nurflügel,
bekommen fast keine. Beim V-Leitwerk liegt C_nβ von AeroBuildup beim Doppelten von AVL. Eine Ursache
dafür ist nicht nachgewiesen. Vermutet wird, dass die gegenseitige Beeinflussung der beiden V-Hälften
fehlt (🟡).

- **Folge für den Kanon:** Die Gültigkeitsbedingung vom 03.10. ist verletzt. Sie lautete: „Revisit if
  … a spiral criterion lies near zero“. Nach Regel 5 sind C_lβ, C_nβ und das Spiralkriterium unscharf.
  Der Kanon ist entsprechend angepasst, die **Bestätigung durch den Maintainer steht aus**.
- **Folge für die App:** Sie zeigt C_lβ aus AeroBuildup an, für Nurflügel also nahezu null. Dazu ist
  GH #1156 angelegt.

### B4 — Rollrate: Streuung systematisch, Richtung fest

AeroBuildup durch AVL ergibt bei 63 Flugzeugen mit Querrudern oder Elevons 1,04 bis 1,20, Median 1,10.
AeroBuildup liegt **immer** höher. Die Einordnung „unscharf“ bleibt. Keine Methode ist nachweislich
vorsichtig: AVL fehlen die Klappenverluste bei kleiner Reynoldszahl, und auch die wahre Rollrate kann
tiefer liegen. Die Streuung von 4–20 % ist aber kleiner als beim BRYAN (23 %).

### B5 — Nurflügel ohne Flosse mit 17° Pfeilung: richtungsneutral

C_nβ liegt bei AeroBuildup um −0,002 und bei AVL um +0,004. Beides ist praktisch null. Als Urmodell
fliegt ein solcher Nurflügel nur knapp. Für #1152 offen: entweder Winglets oder eine Mittelflosse
als Vorgabe, oder mehr Pfeilung. BAENDER §3c setzt 17° fest, das reicht für einen flossenlosen
Nurflügel nicht. Belege für eine bessere Vorgabe fehlen noch.

## Dateien

`combos.py` · `generate.py` · `fleet/` (74 Geometrien und Profile) · `fleet_eval.py` · `fleet_results.csv` ·
`lateral_avl.py` · `lateral_avl.csv` · `sweep_clb_repro.py` · `analyse.py` · `SPANNWEITEN.md`

## Quellen der Spannweiten (Auszug, URLs)

- F3A: https://aeroclub.at/uploads/download/mso2008_f3a.pdf
- F3K, F3J (FAI SC4 Vol F3 2025): https://www.modellflug.ch/documents/sc4_vol_f3_soaring_25.pdf ·
  https://www.barcs.co.uk/f3k/about-f3k/
- RES/F3L: https://www.barcs.co.uk/fxres/ · https://www.contest-eurotour.com/category-f3l/
- F5B/F5D-Modelle: https://mh-aerotools.de/airfoils/f5b_models.htm · https://mh-aerotools.de/airfoils/f5d_models.htm
- Produkte: Händler- und Herstellerseiten von Horizon/E-flite, FMS, Multiplex (lindinger.at), Topmodel,
  NAN, Royal, Phoenix, wie in `SPANNWEITEN.md` genannt
