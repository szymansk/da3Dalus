# SNACK im Geometrieformat - Fitbericht

Stand 02.10.2026. Quelle: `SNACK_Gesamtmodell.step` (84 benannte Koerper in den Gruppen Rumpf 29, Leitwerk 7, Haube 8, Fluegel 40) und
FlugModell-Bauplan SNACK (28 Seiten). Das STEP-Modell liegt bereits in der Formatkonvention: X nach hinten, Y nach rechts, Z nach oben, mm
(geprueft: Seitenruderhorn 15d bei -Y = links, Hoehenruderhorn 16c unten - wie im Plan S. 4). Gemessen wird an den Netzen der Koerper.

**Pruefung:** Schema Draft 2020-12 + F-01..F-07: **0 Fehler, 0 Warnungen** (3 Flaechen / 48 Rippenstationen, 2 Rumpfkoerper / 43 Stationen).

## 1 Kopfdaten

| Feld | Wert | Herkunft |
|---|---|---|
| `total_mass_kg` | 0,250 | Plan S. 1: Abfluggewicht 250 g |
| `xyz_ref` | x 143,5 / y 0 / z 15,7 mm | Plan S. 1/9: Schwerpunkt 0 bis 3 mm vor dem Holm -> Mitte des Bereichs (x 142,0..145,0), gemessen an der Holm-Vorderkante in der Mittelebene; z = Holmmitte (**ANNAHME**) |

Kontrolle gegen den Plan: Spannweite 648,0 mm (Plan 650), Laenge 512,6 (Plan 513), Fluegelinhalt aus dem Format 8,02 dm2 (Plan 7,5).

Zum Fluegelinhalt: 8,02 dm2 ist die volle projizierte Flaeche inkl. Mittelstueck im Rumpf. Ohne den Bereich in der Rumpfbreite (y 0 bis 25 mm, Sehne 117,4 mm, beidseitig 0,59 dm2) bleiben 7,43 dm2, ohne das ganze Mittelstueck bis zur Querruderkante (y 33 mm) 7,24 dm2. Die Planangabe 7,5 dm2 passt damit zur Flaeche ausserhalb des Rumpfs (DEUTUNG, im Plan nicht erlaeutert). Flaechenbelastung mit 250 g: 31,2 g/dm2 (voll) bzw. 33,3 g/dm2 (Plan).

## 2 Tragflaeche (`wings.Tragflaeche`, symmetrisch, rechte Haelfte = Teile *_1)

Aufbau laut Plan S. 5: ebene Unterbeplankung 21 (1,0), CFK-Flachprofil 6 x 1 als Holm, Rippen 22 vorn / 25 hinten (2,0), Oberbeplankung 23/27 (1,0),
Abschlussleiste 24, Querruder 28 (Balsa 3, spitz geschliffen). Das Profil ist ein **6 mm dickes Brettprofil** mit gerundeter Nase - die Dicke ist absolut
konstant (Holmhoehe 6,03), nicht proportional zur Sehne. Deshalb hat **jede Station ihre eigene Profildatei** (`snack_fluegel_NN.dat`, konvexe Huelle des Schnitts).

V-Form: LE-Linie 3,92 Grad (im Format, `dihedral` an der Wurzel), ebene Unterseite 4,24 Grad. z_le liegt auf der Ausgleichsgeraden, Restfehler max 0,59 mm.
Stationswahl: kleinste Menge, bei der der lineare Loft Nasen- und Hinterkante auf 0,30 mm trifft; Zwillingsstationen am Querruderanfang (y 33) und -ende (y 322), weil die Sehne dort springt.

| i | y mm | x_le | Sehne | Schraenkung Grad | Dicke mm | Holm (Lage f, Hoehe) | Querruder rel_chord / Spalt |
|---|---|---|---|---|---|---|---|
| 0 | 0,0 | 91,4 | 117,4 | -0,21 | 6,02 | 0,461 / 6,03 | - |
| 1 | 32,9 | 94,7 | 117,4 | -0,47 | 6,04 | 0,448 / 6,03 | - |
| 2 | 33,2 | 94,9 | 147,9 | 0,37 | 6,04 | 0,354 / 6,03 | 0,794 / 0,73 |
| 3 | 286,0 | 120,7 | 109,4 | -0,11 | 6,01 | 0,366 / 6,03 | 0,837 / 0,68 |
| 4 | 298,0 | 124,0 | 105,5 | -0,04 | 6,01 | 0,354 / 6,03 | 0,836 / 0,68 |
| 5 | 304,0 | 127,0 | 102,3 | -0,34 | 6,02 | 0,340 / 6,03 | 0,834 / 0,68 |
| 6 | 308,0 | 129,9 | 99,2 | -0,37 | 6,01 | 0,323 / 6,03 | 0,831 / 0,68 |
| 7 | 312,0 | 133,8 | 95,1 | -0,23 | 6,01 | 0,299 / 6,03 | 0,826 / 0,68 |
| 8 | 316,0 | 138,9 | 89,8 | -0,46 | 6,01 | 0,262 / 6,03 | 0,818 / 0,68 |
| 9 | 318,0 | 142,1 | 86,4 | -0,49 | 6,02 | 0,236 / 6,03 | 0,812 / 0,68 |
| 10 | 320,0 | 146,2 | 82,3 | -0,54 | 6,02 | 0,200 / 6,03 | 0,803 / 0,68 |
| 11 | 321,8 | 151,1 | 77,3 | -0,61 | 6,02 | 0,150 / 6,03 | 0,792 / 0,68 |
| 12 | 322,0 | 151,9 | 76,5 | -0,35 | 6,02 | 0,142 / 6,03 | - |
| 13 | 322,2 | 152,6 | 59,5 | -2,35 | 6,02 | 0,170 / 6,03 | - |
| 14 | 322,4 | 153,4 | 58,7 | -2,38 | 6,02 | 0,159 / 6,03 | - |
| 15 | 322,8 | 155,0 | 57,1 | -2,47 | 6,02 | 0,135 / 6,03 | - |
| 16 | 323,6 | 159,5 | 52,6 | -1,62 | 5,98 | - | - |
| 17 | 324,0 | 162,8 | 49,2 | 0,53 | 2,09 | - | - |

Holm: `spare_list` Index 0, Tasche 1,0 x 6,03 mm (CFK-Flachprofil hochkant), Modus `standard_backward` (ein gerades Stueck von der Mitte bis y 323,7).
Querruder: `hinge_type` middle (Vlies-Scharniere), Anschlaege +-19,4 Grad (= 10 mm an der groessten Rudertiefe 30,2 mm, **ANNAHME** zur Messstelle). `servo` = null:
der Plan nennt nur die Klasse (bis 6 g), kein Katalogmass; die Querruderservos sitzen an der Fluegelwurzel im Rumpf und lenken direkt mit 0,8-mm-Draht an (S. 7).

## 3 Leitwerke

Hoehenleitwerk (16a Flosse, 16b Ruder einteilig, Balsa 2,0 eben): 9 Stationen, Ruder `symmetric`, Anschlaege +-21,8 Grad (10 mm bei 26,9 mm Rudertiefe).
Seitenleitwerk (15a/15b Flosse, 15c Ruder, Balsa 2,0): 21 Stationen laengs z (`dihedral` 90 an der Wurzel), Anschlaege +-29,2 Grad (20 mm bei 40,9 mm).
Die Flosse laeuft als flacher Keil auf dem Rumpfruecken nach vorn (x 300,6 bis 425); waagerechte Schnitte beschreiben diesen Keil, deshalb viele Stationen zwischen z 63 und 89.
Unter z 63 gibt es nur das Ruder (rel_chord 0). Der Schlitz fuer das Ruderhorn 15d ist keine Station. Ebene Platten: Profildatei je Station (`snack_hlw_NN.dat`, `snack_slw_NN.dat`), weil die Dicke 2,0 mm absolut ist.

## 4 Rumpf und Haube (`fuselages`)

Kastenrumpf (Seiten 1a/1b Balsa 1,5, Boden/Ruecken gewoelbt) -> Superellipsen mit n bis 50 (Rechteck). Haube (17-20) als eigener Koerper. Fit gegen die Aussenhuelle je Station:

| Koerper | Stationen | Fitfehler max mm | groesste Abweichung bei |
|---|---|---|---|
| Rumpf | 28 | 0,63 | x 247 |
| Haube | 15 | 0,38 | x 148 |

Der Rumpf ist im Kabinenbereich (x 136..241) oben offen; die Haube deckt ihn ab. `step_path` / `solid_step_path` bleiben null (keine importierte Aussenflaeche).

## 5 Was nicht im Format steht (-> `snack.zusatz.json`, `teile.json`)

- Antrieb, Steller, Akku, Servos, Empfaenger, Ruderausschlaege in mm, Materialbedarf, Anlenkung, Magnete: woertlich vom Plan S. 1/4 in `snack.zusatz.json`.
- `teile.json`: alle 84 Koerper mit gemessener Dicke (Strahl durch die Platte), Normdicke, Volumen, Huellmass und Material. **Material ist ANNAHME** aus Dicke + Materialbedarf
  (4 mm = Pappelsperrholz: nur Motorspant 7a; 3 mm = Balsa hart; Ruderhoerner 15d/16c/30 = Birke 1,5; sonst Balsa mittelhart). Das STEP enthaelt keine Materialien.
- Servos, Motor, Akku sind im STEP nicht enthalten (nur Holz, Haube, CFK-Holme).

## 6 Annahmen

1. z des Schwerpunkts (Plan nennt nur x). 2. Ruderausschlaege in Grad aus Plan-mm an der groessten Rudertiefe. 3. Materialzuordnung der Teile.
4. `hinge_type` middle fuer Vlies-Scharniere. 5. Servo-Katalogmasse fehlen (`servo` = null).
