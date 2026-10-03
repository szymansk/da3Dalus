# Neutralpunkt bei kleinen Reynoldszahlen: wie weit trägt AVL? (03.10.2026)

Anlass: AeroBuildup legt den Neutralpunkt etwa 10 % MAC hinter AVL, weil der Abwind am Leitwerk fehlt
(#1154). Frage des Maintainers: Eignet sich AVL bei kleinen Reynoldszahlen?

## Was AVL kann und was nicht

- **Kann:** Geometrie und Abwind (Wirbelschleppe am Leitwerk), reibungsfrei, für kleine α und β.
- **Kann nicht:** Dicke, Umschlag, Ablösung, laminare Ablöseblasen, Abriss.
- **Reibung kommt nur über CLAF hinein:** die Profilauftriebssteigung als Vielfaches von 2π.
  - Drelas Primer empfiehlt dafür Windkanal- oder viskose Profildaten (avl_doc.txt:882–907).
  - CDCL wirkt nur auf den Widerstand.
  - dCL_a / dCM_a wirken nur auf die Eigenformen, nicht auf den Neutralpunkt.
- **AeroSandbox schreibt CLAF selbst**, nach Drelas Dickenregel 1 + 0,77·t/c.
- **Rümpfe:** AVL rechnet sie nach Schlankkörpertheorie; Drela nennt die Erfahrung damit „relatively
  limited".

## Was Reibung am Neutralpunkt ändert

In $h_n = h_{ac,wb} + \eta V_H (a_t/a)(1 - d\varepsilon/d\alpha)$ stimmen Geometrie und Abwind-Struktur.
Die Auftriebssteigungen $a$ und $a_t$ und der Faktor η sind dagegen reibungsabhängig.
- **Verliert nur das Leitwerk Steigung**, wandert der echte Neutralpunkt nach vorn. 20 % weniger
  ergeben etwa 4 % MAC.
- **Verlieren beide**, sinkt auch der Abwind, und der Neutralpunkt wandert etwas nach hinten.

Die Richtung hängt also am Verhältnis der beiden Steigungen.

## Messung am BRYAN (`bryan_np_claf.py`)

NeuralFoil-Steigung bei Betriebs-Re über α −1…3°:

| Fläche | Re | Steigung |
|---|---|---|
| Bryan-Flügel | 71k | 1,62 × 2π |
| Bryan-Leitwerk (Platte) | 40k | 1,09 × 2π |
| MH32 (e-Hawk) | 61k | 1,41 × 2π |
| Platte (e-Hawk-Leitwerk) | 32k | 1,07 × 2π |

Die gewölbten Flügelprofile steigen steiler an als 2π. Das ist die laminare Ablöseblase nahe dem
Nullauftrieb: Bei α = 0 liegt C_L unter dem reibungsfreien Wert, danach holt die Kurve auf.

| AVL mit CLAF Flügel / Leitwerk | Neutralpunkt |
|---|---|
| 1,0 / 1,0 | 36,0 % MAC |
| 1,08 / 1,02 (AeroSandbox-Dickenregel, bisheriger Stand) | 32,9 % |
| 1,62 / 1,09 (NeuralFoil) | **14,1 %** |
| 1,62 / 1,0 | 13,9 % |
| 1,0 / 1,09 | 36,4 % |

**Der Neutralpunkt reagiert extrem auf die Flügelsteigung.** Mit den NeuralFoil-Steigungen läge er
17 % MAC vor dem Plan-Schwerpunkt (31,4 %), und der BRYAN wäre unfliegbar. Das widerspricht einem
veröffentlichten, geflogenen Bauplan. Die örtliche Steigung an der Ablöseblase ist also **nicht** die
Steigung, die über das Stabilitätsmaß entscheidet. Sie gilt nur in einem schmalen Bereich um den
Nullauftrieb.

## Literatur

- Es gibt keine frei zugängliche Validierung mit Fehlerprozenten für Neutralpunkt, Stabilitätsmaß oder
  Rolldämpfung bei Re < 500k.
- Müller/Liebenberg (2012, Mini-UAV, Re 300k): AVL, Datcom und XFLR5 „compare favourably" mit Windkanal
  und Flug, aber ohne Zahlen. Die Autoren fanden keine Literatur zu einer unteren Re-Grenze für AVL.
- Ananda/Sukumar/Selig (2015, Flachplattenflügel, Re 60k–160k): Die gemessene Steigung folgt dem Trend
  der Theorie und nähert sich ihr mit steigender Re an.

## Folgerung

1. **AVL ist für den Neutralpunkt besser als AeroBuildup**, weil es den Abwind hat. Das ist der größte
   Fehler von AeroBuildup (10 % MAC, #1154).
2. **Bei kleinen Reynoldszahlen ist kein Werkzeug ohne Kalibrierung belastbar.** Schon die Wahl von
   CLAF verschiebt den Neutralpunkt um 3 % MAC (36,0 gegen 32,9). Steigungen aus NeuralFoil verschieben
   ihn um mehr als 20 %.
3. **Kalibrierung braucht geflogene Schwerpunkte** der Referenzflotte: Bei welchem Schwerpunkt fliegt
   das Modell gut, wo wird es kritisch? Der Plan-Schwerpunkt eines geflogenen Bauplans ist eine erste
   Stütze. Mit AVL und der Dickenregel liegt der BRYAN-Plan-Schwerpunkt bei 1,5 % Stabilitätsmaß.
   Das ist knapp, aber für ein geflogenes Modell nicht unmöglich.
