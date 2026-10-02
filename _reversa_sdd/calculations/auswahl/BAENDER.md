# Bänder für das Urmodell

Stand 02.10.2026. Gehört zum Auswahlgraphen (`auswahl.json`), **nicht zum Rechenkanon** (A10).
Bänder erzeugen das Urmodell und bewerten später. Sie rechnen nichts im Kanon.

Quellen:
- **[T]**: Modelltabelle RC-Network, 2 674 Modelle. Statistik in `flottenstatistik.json`, erzeugt mit
  `scripts/selection_fleet_stats.py`.
- **[V: Seite]**: Fachquellen im Vault des Skills `rc-aircraft-designer` (rcplanedesigner,
  RC-Network-Wiki, Lennon).
- **—**: keine Quelle. Was dort steht, ist ein Vorgabewert und keine belegte Zahl (ADR 0023).

## 1. Reichen die sieben Antworten?

**Ja, für die Gestalt.** Das Urmodell braucht in der App (Code-Prüfung 02.10.2026):
- Flügel mit mindestens zwei Schnitten (Vorderkante, Profiltiefe, Schränkung, Profil). Höhen- und
  Seitenleitwerk sind ebenfalls Flügel.
- Ruder je Segment (Scharnierlage, symmetrisch oder gegensinnig).
- Optional einen Rumpf aus mindestens zwei Superellipsen.
- Masse und Bezugspunkt (Schwerpunkt).
- Den Antrieb nicht für die Aerodynamik, nur für die Flugleistungen.

Jede dieser Angaben kommt aus einer Antwort, einem Band oder einem Vorgabewert.

**Keine weitere Frage ist nötig.** Die Lücken liegen in den **Bändern**, nicht in den Fragen (§4).

| Angabe des Urmodells | kommt aus |
|---|---|
| Spannweite `b` | Antwort 7 |
| Masse `m` | Masse-Spannweite-Kurve der Mission [T] |
| Streckung, daraus Flügelfläche und -tiefe | Median der Mission [T]; Trainer, Sport und Kunstflug auch [V] |
| Flächenbelastung | **Ergebnis** `m/S`; Plausibilitätsprüfung gegen [V] |
| Zuspitzung | [V] für Trainer, Sport, Kunstflug, Segler; sonst — |
| Schränkung | Nurflügel [V]; sonst — (Vorgabe 0°) |
| Pfeilung | Nurflügel —, **Lücke** |
| V-Form | aus Flügellage und Steuerachsen [V] |
| Profil | Profilklasse der Mission [V], dann beste Wahl aus der DB bei der Reynoldszahl des Urmodells |
| Rumpflänge | Verhältnis Rumpflänge zu Spannweite je Mission [T] |
| Rumpfquerschnitt | —, **Lücke** (Vorgabe) |
| Hebelarme | Leitwerks- und Nasenhebel in MAC für Trainer, Sport, Kunstflug [V]; sonst aus der Rumpflänge |
| Höhenleitwerk | Leitwerksvolumen [V] für Trainer, Sport, Kunstflug; sonst Flächenanteil [V]/[T] |
| Seitenleitwerk | 35–50 % der Höhenleitwerksfläche [V] |
| Leitwerk von V, Ente, Tandem, Kastenflügel | —, **Lücke** |
| Querruder | Tiefe und Spannweitenanteil je Anordnung [V] |
| Höhen- und Seitenruder | Flächenanteil je Mission [V] für Trainer, Sport, Kunstflug |
| Klappen | —, **Lücke** |
| Ruderausschläge | einzelne Werte [V]; je Mission — |
| Stabilitätsreserve-Ziel | Trainer, Sport, Kunstflug, Nurflügel [V]; Segler — |
| Schwerpunkt | Kanon: `cg-for-target-margin` aus Neutralpunkt und Stabilitätsreserve-Ziel |
| Antrieb | **Leistungsbelastung W/kg: keine Quelle**, größte Lücke |

## 2. Statistik der Modelltabelle [T]

Werte als Median mit Quartilsabstand [Q1–Q3] und der Anzahl Modelle n.

Masse-Spannweite-Kurve `m = C · b^k` (kg, m). Die Spalte ×σ gibt die Streuung als Faktor an.

| Mission | n | W/S g/dm² | Streckung | Rumpflänge/b | m = C·b^k | ×σ |
|---|---|---|---|---|---|---|
| Trainer | 20 | 51,5 [44–59] | 6,0 [5,6–6,6] | 0,8 | 1,10·b^1,51 | 1,17 |
| Querruder-/Kunstflugtrainer | 18 | 50,0 [43–59] | 5,5 [4,6–5,8] | 0,9 | 0,87·b^2,42 | 1,26 |
| Sport | 124 | 47,5 [30–65] | 5,6 [4,2–6,6] | 0,8 | 0,87·b^2,34 | 1,62 |
| Kunstflug | 188 | 66,0 [44–79] | 5,2 [4,6–5,6] | 0,9 | 0,91·b^2,72 | 1,34 |
| 3D | 45 | 44,0 [40–56] | 4,7 [3,5–5,2] | 1,0 | 1,17·b^1,92 | 1,47 |
| Speed | 41 | 50,0 [45–63] | 11,3 [9,6–12,3] | 0,6 | 1,01·b^0,83 | 1,36 |
| Elektrosegler | 111 | 36,8 [30–44] | 12,1 [10,5–14,3] | 0,5 | 0,33·b^1,85 | 1,30 |
| Scale | 270 | 71,4 [56–85] | 6,0 [5,4–6,9] | 0,8 | 0,87·b^2,51 | 1,48 |
| Park | 38 | 26,4 [21–30] | 4,2 [3,1–5,6] | 0,8 | 0,66·b^2,65 | 1,50 |
| Segelflug-Trainer | 9 | 23,5 [17–27] | 10,0 [8,5–11,7] | 0,6 | 0,29·b^1,59 | 1,51 |
| Thermik | 55 | 25,1 [15–31] | 14,7 [11,8–15,7] | 0,5 | 0,10·b^2,50 | 1,37 |
| Hang | 33 | 31,0 [24–40] | 11,4 [10,1–13,7] | 0,6 | 0,31·b^1,88 | 1,25 |
| Wurf | 9 | 17,0 [12–18] | 9,0 [8,6–9,5] | 0,6 | 0,24·b^1,09 | 1,17 |
| Scale-Segler | 176 | 55,0 [44–69] | 19,2 [16–23] | 0,4 | 0,19·b^2,35 | 1,39 |
| Nurflügel (alle) | 25 | 28,5 [19–45] | 7,7 [7,1–10,2] | 0,3 | 0,30·b^2,04 | 1,63 |

**Warum eine Massenkurve statt einer festen Flächenbelastung:**
- Die Masse wächst schneller als die Fläche, also wächst die Flächenbelastung mit der Größe.
- [V] sagt dasselbe: Trainer 40–55 g/dm² bei 500 mm Spannweite, 55–75 g/dm² bei 2000 mm.

Probe für einen Trainer mit 1,4 m Spannweite:
- Die Kurve ergibt 1,82 kg.
- Mit Streckung 6 folgt eine Fläche von 32,7 dm².
- Die Flächenbelastung ist dann 56 g/dm². Der Median der Tabelle liegt bei 51,5 g/dm²; der Wert
  passt.

**Vorbehalte:**
- Die Tabelle ist von Verbrenner-Baukästen geprägt: 593 Verbrenner gegenüber 508 Elektro.
  Kunstflug und Scale fallen deshalb schwer aus.
- Die Massenkurven für Wurfsegler, Segelflug-Trainer und Nurflügel beruhen auf weniger als 25
  Modellen.
- Die Spalte „Leitwerksfläche" der Tabelle ist nicht eindeutig (nur Höhenleitwerk oder Summe).

## 3. Bänder aus den Fachquellen [V]

| Band | Trainer | Sport | Kunstflug | Quelle |
|---|---|---|---|---|
| Streckung (min / typ / max) | 5 / 7 / 9 | 4 / 5,5 / 7 | 3,5 / 4,75 / 6 | wing-aspect-ratio--practical-limits… |
| Zuspitzung λ | 0,75 / 0,9 / 1,0 | 0,5 / 0,65 / 0,8 | 0,4 / 0,5 / 0,6 | wing-taper-ratio--designing… |
| Leitwerksvolumen V_H | 0,55 / 0,65 / 0,75 | 0,45 / 0,55 / 0,65 | 0,40 / 0,50 / 0,60 | tail-horizontal-tail-placement… |
| Leitwerkshebel (× MAC) | 2,7–3,0 | 2,3–2,7 | 2,0–2,3 | fuselage-tail-lever-arm--design-envelope |
| Nasenhebel (× MAC) | 1,2–1,5 | 1,1–1,3 | 1,0–1,2 | fuselage-front-lever-arm--design-envelope |
| Stabilitätsreserve % MAC | 5 / 10 / 15 | 3 / 4 / 5 (Lennon: 10) | 0 / 1,5 / 3 | airplane-balance-…static-margin; lennon-cg-location… |
| Höhenruder, % der HLW-Fläche | 25–30 | 35–40 | 40–70 | tail-elevator--practical-limits… |
| Seitenruder, % der SLW-Fläche | 20–40 | 40–60 | 60–80 | tail-rudder--practical-limits… |
| Profildicke % | 12 / 15 / 18, flache Unterseite | 10 / 11 / 12, halbsymmetrisch | 7 / 8,5 / 10, symmetrisch (Lennon: 10–15) | wing-airfoils--relative-thickness / families |

**Bänder, die nicht von der Mission abhängen:**

| Band | Wert | Quelle |
|---|---|---|
| V-Form, mit Querrudern | Hochdecker 2°, Mitteldecker 3°, Tiefdecker 4° | lennon-wing-position-dihedral |
| V-Form, nur Höhe + Seite | Hochdecker 5°, Mitteldecker 6°, Tiefdecker 7° | lennon-wing-position-dihedral |
| Pfeilung als Ersatz für V-Form | 2–3° Pfeilung wirken wie etwa 1° V-Form | lennon-dihedral-directional-balance |
| Grenzen der Hebelarme | Leitwerkshebel ≥ 2 MAC und ≤ 60 % der Rumpflänge; Nasenhebel ≥ 1 MAC und ≤ 50 % des Leitwerkshebels | fuselage-…-design-envelope |
| Seitenleitwerksfläche | 35–50 % der Höhenleitwerksfläche, selten über 60 % | tail-vertical-tail-placement… |
| Leitwerksflächen beim Segler | Höhenleitwerk 13 %, Seitenleitwerk 6 % der Flügelfläche | lennon-typical-proportions-by-mission |
| Querruder | 25 % Tiefe × 35–40 % Halbspannweite; über die ganze Spannweite 10 % Tiefe / 80 % Spannweite; mindestens 5 % der Flügelfläche | lennon-aileron-sizing-geometry; wing-ailerons-… |
| Querruder-Differenzierung | 1,3:1 bis 2:1 | rcn-differenzierung |
| Seglerprofil | hohes c_a, kleines c_m, Re 100k–300k | lennon-mission-profile |
| Speedprofil | dünn, wenig gewölbt (E226, E374) | lennon-mission-profile |
| Nurflügel: Schränkung | 2–5° bei symmetrischem Profil, 5–9° bei S-Schlag | lennon-tailless-sweep-washout |
| Nurflügel: Zuspitzung | etwa 2:1; bei 4:1 reißt die Spitze ab | lennon-tailless-sweep-washout |
| Nurflügel: Stabilitätsreserve | 5–10 % MAC | lennon-tailless-cg-static-margin |
| Nurflügel: V-Form | etwa 5° bei ungepfeiltem Flügel | flying-wing-lateral-stability |
| Nurflügel: Seitenflächen | Winglets 2–3° Vorspur; Seitenruder 30 % der Flossenfläche | lennon-tailless-vertical-surfaces |

**Widersprüche:**
- **Profildicke im Kunstflug:** rcplanedesigner nennt 7–10 %, Lennon 10–15 %.
- **Stabilitätsreserve beim Sport-Modell:** rcplanedesigner nennt 3–5 %, Lennon 10 %.
- **Streckung beim Kunstflug:** [V] nennt 4,75 als typisch, die Tabelle hat einen Median von 5,2.
  Das ist verträglich.

## 4. Lücken: Bänder ohne Quelle

1. **Leistungsbelastung W/kg** für alle Missionen mit Motor. Der Vault nennt nur Hubraumverhältnisse
   für Verbrenner. Ohne diesen Wert kann das Urmodell keinen Antrieb wählen.
2. **Pfeilung des Nurflügels.**
3. **Segler:** Stabilitätsreserve-Ziel und Leitwerkshebel für alle Segler-Missionen.
4. **3D, Speed, Park und Scale:** Zuspitzung, Leitwerksvolumen, Stabilitätsreserve und Ruder. Aus
   der Tabelle sind nur Masse, Streckung und Rumpflänge belegt.
5. **Leitwerke ohne Größenregel:** Bemessung von V-Leitwerk, Ente, Tandem und Kastenflügel.
6. **Klappen und Ausschläge:** Klappengröße und Ruderausschläge je Mission.
7. **Rumpfquerschnitt.**
