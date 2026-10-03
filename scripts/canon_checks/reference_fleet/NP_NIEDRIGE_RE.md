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

## Die geometrische RC-Methode (Maintainer-Anstoß, 03.10.2026)

> „Wenn du betrachtest, wie RC-Flugzeuge rein geometrisch ausgelegt werden und selten so elaboriert
> berechnet, wie wir das gerade tun, dann solltest du der Wahrheit und der Nutzbarkeit für den
> Konstrukteur näher kommen." (Maintainer)

**Methode (rcplanedesigner, vault `airplane-balance-finding-the-first-flight-cg--build-the-neutral-point`):**
- Der Neutralpunkt ist der Schwerpunkt der aerodynamischen Mittelpunkte (je 25 % MAC).
- Gewichtet wird der Flügel mit seiner Fläche, das Höhenleitwerk mit der halben Fläche.
- Für den Rumpf wird der Wert um 5 % MAC nach vorn geschoben.
- Beim V-Leitwerk zählt die Projektion A·cos²ν (Drela).

Gerechnet mit `np_geometric.py`:

| Flugzeug | RC-Methode | AVL | AeroBuildup | Plan-Schwerpunkt | Stabilitätsmaß (RC) |
|---|---|---|---|---|---|
| BRYAN | 41,5 % | 32,9 % | 43,7 % | 31,4 % | **10,1 %** |
| e-Hawk | 41,5 % | 48,8 % | 58,4 % | 33,0 % | **8,6 %** |

Mit der RC-Methode liegen beide Plan-Schwerpunkte genau im Zielbereich der Praxis: Sport 10 % (Q-MS-14),
Segler 5–12 % (BAENDER §3b). AVL ergibt kein einheitliches Bild (1,5 % und 15,8 %), AeroBuildup liegt bei
beiden zu weit hinten.

**Vorbehalt:** Die Übereinstimmung ist teilweise zirkulär, denn die Konstrukteure setzen den Schwerpunkt
vermutlich mit genau dieser Regel. Sie belegt nicht die Physik. Sie belegt aber, dass die Regel zu dem
passt, was gebaut und **geflogen** wird. Für den Konstrukteur ist sie die anschlussfähige Zahl.

## Akribische Gegenprüfung aller belegten Methoden (03.10.2026, `np_methods.py`)

Drei unabhängige Recherchen (RC-Vault, Modellflugliteratur im Netz, Lehrbuch) ergaben diese belegten
Formeln. Alle außer Lennon haben die Schwerpunktform
$x_{NP} = (S_w x_{ac,w} + K S_h x_{ac,h})/(S_w + K S_h)$ und unterscheiden sich nur im Leitwerksgewicht
$K$ und im Rumpfterm:

| | Methode | K | Rumpf | Quelle |
|---|---|---|---|---|
| A | rcplanedesigner | 0,5 pauschal | −5 % MAC | vault `…build-the-neutral-point`, rcplanedesigner.com |
| B | Harding | Wirksamkeit, Beispiel 0,5 | in K | Model Aviation 08/2004, „Fundamentals of Stability" |
| C | Pappas | $(1-3{,}24/AR_w)\cdot\frac{1/(1+2/AR_h)}{1/(1+2/AR_w)}$ | – | Model Aviation 10/2009, „If It Flies" (nach von Mises/Prager/Kuerti) |
| D | Lehrbuch | $\eta(1-\frac{4}{AR_w+2})\frac{AR_h/(AR_h+2)}{AR_w/(AR_w+2)}$ | (Raymer, ungeprüft) | Sadraey Eq. 6.67, dε/dα = 2a/(πAR) |
| E | Krauss | 0,75 | – | stunthanger.com „aft cg limit" (dort selbst als den Abwind übergehend bezeichnet) |
| F | Lennon | hinterster Schwerpunkt = [0,17 + 0,30·V_H·HTE]·MAC, HTE 0,4–0,9 | in der Formel | Lennon 1996, Kap. 7 |
| G | Lennon | Neutralpunkt fest 35 % MAC | – | Lennon 1996, Kap. 6 |

Der Lehrbuch-Prüfer hat gezeigt, dass die Schwerpunktform die **exakte** Form der Lehrbuchbeziehung
ist, mit $K = \eta (a_h/a)(1 - d\varepsilon/d\alpha)$. Die lineare Form $h_n - h_{ac} = K V_H$
überschätzt um den Faktor $(1 + K S_h/S)$.

**Ergebnis (Neutralpunkt in % MAC, Stabilitätsmaß am Plan-Schwerpunkt):**

| Methode | BRYAN (AR 4,3) | e-Hawk (AR 11,3) |
|---|---|---|
| C Pappas | 34,0 (SM 2,6) | 52,9 (SM 19,9) |
| D Lehrbuch η 1,0 | 38,2 (6,8) | 52,4 (19,4) |
| D Lehrbuch η 0,9 | 36,9 (5,5) | 49,8 (16,8) |
| **AVL** | **32,9 (1,5)** | **48,8 (15,8)** |
| A rcplanedesigner | 41,5 (10,1) | 41,5 (8,6) |
| B Harding | 46,5 (15,1) | 46,5 (13,6) |
| G Lennon fest | 35,0 (3,6) | 35,0 (2,0) |
| E Krauss | 55,7 (24,3) | 56,5 (23,5) |
| AeroBuildup | 43,7 (12,3) | 58,4 (25,4) |

Lennons hinterster Schwerpunkt (F, HTE 0,4–0,9): BRYAN 22,7–29,8 %, e-Hawk 22,4–29,2 % MAC.

**Befunde:**
1. **Die Methoden mit Abwind und Streckung (Pappas, Lehrbuch) stimmen mit AVL auf 1–4 % MAC überein**,
   an beiden Flugzeugen. Die frühere Lesart „AVL uneinheitlich" war falsch: AVL passt zur Physik.
2. **Die Konstrukteure haben verschieden gewählt:** BRYAN mit 2–7 % (Sport-Band rcplanedesigner 3–5 %),
   der e-Hawk mit 16–20 % (vorsichtiger Erstflug-Schwerpunkt; rcn empfiehlt etwa 15 % zum Einfliegen).
3. **Die pauschale Faustregel (A, B) kennt keine Streckung.** Beim BRYAN legt sie den Neutralpunkt 5–8 %
   MAC zu weit nach hinten; das ist bei kleiner Streckung die unsichere Richtung. Beim e-Hawk legt sie ihn
   8–11 % zu weit nach vorn. Dass sie beide Plan-Schwerpunkte „traf", war Zufall.
4. **Rumpf:** Belegt ist nur rcplanedesigners Pauschalwert von −5 % und Lennons „bis 15 %". Raymers Formel
   (−0,6 bis −1,3 % für schlanke RC-Rümpfe) steht nicht im Vault und ist ungeprüft. AVL-Rümpfe sind grob.
   Der Rumpfanteil bleibt offen.
5. **Nicht gefunden:** Simons' Formel und die „Schenk"/FMT-Formel (nur im Druck). Nichts davon ist
   erfunden.
