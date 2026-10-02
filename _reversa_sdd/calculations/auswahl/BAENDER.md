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
| Antrieb | Leistungsbelastung W/kg (§3a, Band) mal Masse, dann erste Wahl aus dem Teilekatalog |

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

## 3a. Leistungsbelastung W/kg (recherchiert 02.10.2026)

Alle Werte sind **elektrische Eingangsleistung bei Vollgas je kg Abfluggewicht**. Umrechnung:
1 W/lb = 2,205 W/kg.

| Mission | Maintainer-Tabelle | MAN | Faustregel 2 | WRCS (E-flite) | Modelltabelle [T] | **Vorschlag min / typ / max** |
|---|---|---|---|---|---|---|
| Trainer | 100–150 | 110–165 | 110–176 | 155–200 | – | **110 / 150 / 200** |
| Sport | 150–250 | 165–220 | 176–265 | 200–245 | 332 [234–429] n=29 | **165 / 220 / 265** |
| Kunstflug | 250–350 | 220–330 | 330–440 | 245–285 | 404 [333–461] n=48 | **220 / 300 / 400** |
| 3D | 350–500+ | 330–440+ | 330–440 | 285–440+ | 410 [313–489] n=15 | **330 / 400 / 500** |
| Speed | 350–500+, Pylon/F5B 1000+ | – | – | – | 333 [240–500] n=27 | **350 / 500 / 1000** |
| Elektrosegler | 50–150 | 110–165 | – | – | 203 [150–241] n=70 | **110 / 165 / 250** |
| Scale | 100–150, Warbirds 150–250 | 110–165, Warbirds 165–330 | 220–330 | 155–200 (langsam) | 319 [278–509] n=38 | **155 / 220 / 330** |
| Park | – | ≤ 110 (Slow Flyer) | – | – | 271 [180–375] n=24 | **110 / 180 / 270** |

Quellen der Spalten:
- **Maintainer-Tabelle:** vom Maintainer eingebracht, 02.10.2026.
- **MAN:** Model Airplane News, Watts-per-pound guide.
- **Faustregel 2:** zweite verbreitete Watt-pro-Pfund-Aufteilung, im selben Suchergebnis.
- **WRCS:** Leitfaden des WRCS-Vereins (wrcs.org.au), ausdrücklich „auf E-flite-Motoren gestützt".
- **Modelltabelle:** Antriebsklasse „NNN W" geteilt durch die Masse. Das ist die **Nennleistung des
  Motors**, nicht die geflogene Eingangsleistung, und liegt deshalb systematisch über den
  Faustregeln.

Nicht in den Vorschlag eingegangen:
- **Vorkoetter (MotoCalc, 2004):** Sport 35–50 W/lb (77–110 W/kg), Kunstflug 60 W/lb (132 W/kg).
  Das sind Mindestwerte für ausreichendes Fliegen, deutlich unter allen anderen Quellen.
- **F5J-Wettbewerb:** etwa 500 W bei 0,8–1,5 kg, also 333–625 W/kg. Das ist die Klasse mit
  Startsteigflug, nicht der gewöhnliche Elektrosegler.

Die Quellen streuen etwa um den Faktor 1,5 bis 2. Der Wert dient nur zur **ersten Antriebswahl** des
Urmodells. Danach rechnet der Kanon Schub und Steigen aus Motor und Propeller
(`motor-propeller-equilibrium`, Route A leistungsbegrenzt), nicht aus W/kg.

**Status:** ✅ Vom Maintainer am 02.10.2026 als Band übernommen (Spalte „Vorschlag“).

## 3b. Segler (recherchiert 02.10.2026)

Die beiden Primärquellen ordnen nach **Steuerachsen**, nicht nach Mission:
- **Drela** — Mark Drela (MIT), „Basic sizing checks for homebrew RC thermal gliders",
  *RC Soaring Digest* 21(8), Aug. 2004, S. 12–14.
- **Lelke** — Helmut Lelke, „Airplane/Glider Design Guidelines and Design Analysis Program",
  Charles River RC.

Daraus folgt: Höhe + Seite ergibt die Werte des Polyeder-Seglers, Querruder ergeben die des
Querruder-Seglers. Wurfsegler bekommen Drelas DLG-Wert für das Seitenleitwerk.

**Definitionen (Drela):**

- $V_H = (S_H/S)\,(l_H/c)$
- $V_V = (S_V/S)\,(l_V/b)$
- $B = \Gamma_{eq}\,(l_V/b)/C_{L,therm}$ ist Blaine Rawdons Spiralparameter: $B>5$ spiralstabil,
  $B=5$ neutral. Er gibt beim Polyeder-Segler zugleich ungefähr die Rollwirkung des Seitenruders an.
- $C_{L,therm}$ ist der Auftriebsbeiwert im langsamen Kreisen: 0,7 bei großen Seglern, 0,6 bei
  Wurfseglern.

Damit wird die V-Form zum **Ergebnis**: $\Gamma_{eq} = B\,C_{L,therm}\,b/l_V$.

**Bänder nach Steuerachsen (Drela):**

| Band | Höhe + Seite (Polyeder) | mit Querrudern | Wurfsegler (DLG) |
|---|---|---|---|
| $V_H$ | 0,3–0,6 (Drela bevorzugt 0,4–0,45) | 0,3–0,6 | wie links |
| $V_V$ | 0,02–0,04 (bevorzugt ≥ 0,03) | 0,015–0,025 (bevorzugt ≥ 0,025) | 0,05–0,06 |
| $B$ | 4,0–6,0 (bevorzugt 5,0–5,5) | 2,0–5,0 (bevorzugt ≥ 3,0) | wie die Steuerachsen |

Lelke gibt $V_H \approx 0{,}4$ („Psf") und $V_V$ 0,020–0,03 („Ysf"), gleich für Flugzeug und Segler.

**Probe Thermiksegler mit 2,8 m Spannweite:**
- Aus den Tabellenwerten: Streckung 14,7, Rumpflänge 0,5 b, Leitwerkshebel ≈ 0,6 der Rumpflänge.
- Daraus folgen $c$ = 0,19 m und $l$ = 0,84 m.
- Mit Lennons 13 % Höhenleitwerksfläche ergibt sich $V_H$ = 0,57, innerhalb Drelas Band.
- Die V-Form bei Höhe + Seite: $\Gamma_{eq}$ = 5 · 0,7 · 2,8/0,84 ≈ 12°.

**Weitere Werte für Segler (Lelke):**

| Band | Wert |
|---|---|
| Einstellwinkel Flügel / Einstellwinkeldifferenz (EWD) | 4–6° / 2–3° |
| Schränkung | 0–3°, über das äußere Drittel |
| Ausschläge | Seite ±15–30°, Quer ±10–20°, Höhe ±10–20°; die größeren Werte für Segler |
| Rudertiefe | Seite 25–50 %, Quer 20–25 %, Höhe 20–30 % |
| Querruderlänge | mindestens das äußere Drittel der Halbspannweite |
| Streckung | 2-m-Segler etwa 10, 3-m-Segler etwa 16 (deckt sich mit der Modelltabelle) |
| Schwerpunkt | Start bei 30 % der mittleren Flügeltiefe |

**Leitwerkshebel:** Es gibt keine direkte Quelle. Er folgt aus der Rumpflänge je Mission [T] und der
Vault-Grenze „Leitwerkshebel ≤ 60 % der Rumpflänge". Die Probe oben bestätigt das.

**V-Leitwerk:** Drela verweist auf eine eigene Bemessungsregel für die äquivalenten Höhen- und
Seitenflächen. Die Originalseite ließ sich nicht abrufen. Aus zweiter Hand: Die Fläche des
V-Leitwerks ist die Summe der Höhen- und Seitenleitwerksfläche. **Lücke** bis zum Original.

**Stabilitätsreserve bei Seglern: keine belastbare Quelle.** Es gibt nur Hinweise:
- Einzelberichte im RC Soaring Digest erfliegen 5 % bzw. 2,5 %.
- Der Vault nennt 5 % als Untergrenze für den Erstflug.
- Laut rcn-schwerpunkt-lage-erfliegen beginnt das Erfliegen etwa 15 % MAC vor dem Neutralpunkt.

Segler werden üblicherweise mit dem Sturzflugtest nach hinten erflogen. Das Urmodell braucht deshalb
einen **Startwert für den Erstflug**, kein Missionsband. **Entscheidung des Maintainers offen.**

Quellen:
- [RCSD 2004-08](https://www.rcsoaringdigest.com/pdfs/RCSD-2004/RCSD-2004-08.pdf)
- [Lelke](https://charlesriverrc.org/articles/design-and-construction/aircraft-design/software/helmut-lelkes-design-analysis-program/da_web.pdf)
- [RCSD-Archiv](https://www.rcsoaringdigest.com/Trimming.html)

## 4. Lücken: Bänder ohne Quelle

1. ~~Leistungsbelastung W/kg~~: ✅ entschieden am 02.10.2026 (§3a).
2. **Pfeilung des Nurflügels.**
3. **Segler:** Leitwerk, V-Form, Einstellwinkel und Ausschläge sind belegt (§3b). Offen sind das
   Stabilitätsreserve-Ziel (Startwert für den Erstflug, Entscheidung des Maintainers) und die
   Bemessung des V-Leitwerks (Drelas Original nicht abrufbar).
4. **3D, Speed, Park und Scale:** Zuspitzung, Leitwerksvolumen, Stabilitätsreserve und Ruder. Aus
   der Tabelle sind nur Masse, Streckung und Rumpflänge belegt.
5. **Leitwerke ohne Größenregel:** Bemessung von V-Leitwerk, Ente, Tandem und Kastenflügel.
6. **Klappen und Ausschläge:** Klappengröße und Ruderausschläge je Mission.
7. **Rumpfquerschnitt.**
