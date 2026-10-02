# BRYAN — Stabilität und Massenhüllkurve (02.10.2026)

Gerechnet mit `scripts/canon_checks/reference_fleet/bryan_stability_mass.py`. Die Kanon-Einträge sind
neutral-point, static-margin, cg-for-target-margin, lateral-static-stability-md/-app und mass-envelope.

**Annahmen:**
- Geometrie, 151 g und Plan-Schwerpunkt aus der Plan-Rekonstruktion; Rumpf-Halbachsen ×2
- Schub nach Route A leistungsbegrenzt (Pulsar 1510, 45 W × 0,85, APC 6×4E, 2S)
- Höhenruder ±14° wie gebaut
- k_S = 1,2 für den Start und 1,3 für den Anflug (im Kanon offen)

## Längsstabilität (bei V_md = 7,82 m/s)

| Größe | Wert |
|---|---|
| MAC / MAC-Vorderkante | 132,8 mm / x = 95,1 mm |
| Neutralpunkt | x = 153,2 mm = **43,8 % MAC** |
| Schwerpunkt laut Plan | x = 136,8 mm = **31,4 % MAC** |
| Stabilitätsmaß | **12,3 % MAC** |
| Schwerpunkt bei SM 5 / 10 / 15 % | 38,8 / 33,8 / 28,8 % MAC |

## Seitenstabilität

| Punkt | C_lβ | C_nβ | C_lr | C_nr | E_spiral |
|---|---|---|---|---|---|
| V_md 7,82 m/s | −0,0547 | +0,0497 | +0,1510 | −0,1268 | −0,00057 |
| Anflug 7,39 m/s | −0,0528 | +0,0486 | +0,1577 | −0,1258 | −0,00102 |

Statisch ist das Modell roll- und richtungsstabil. Die Spirale ist schwach instabil (E < 0). Das ist ein
Wert, keine Bewertung (A10).

## Massenhüllkurve

| m [g] | V_S [m/s] | V_max [m/s] | ROC_max [m/s] | T−D bei V_TO [N] | vordere Grenze [% MAC] |
|---|---|---|---|---|---|
| 100 | 4,62 | 25,31 | 17,70 | +2,40 | – |
| 151 | 5,68 | 25,38 | 13,80 | +2,22 | – |
| 200 | 5,99 | 25,42 | 10,44 | +2,11 | 15,9 |
| 300 | 7,22 | 25,46 | 6,73 | +1,85 | 17,5 |
| 500 | 9,22 | 25,29 | 3,56 | +1,39 | 18,9 |
| 800 | 11,61 | 24,35 | 1,48 | +0,77 | 19,7 |
| 1100 | 15,26 | 22,20 | 0,35 | +0,21 | – |

- **Grenzmassen:** m_max,level = **1228 g**, m_max,TO = **1218 g**. Das ist die aerodynamische und
  antriebsseitige Grenze, die Struktur ist nicht berücksichtigt (max-mass-structure braucht n_break des
  Holms).
- **Hintere Grenze:** Das Ruder (voll Tief bei V_max) trimmt erst weit hinter dem Neutralpunkt, bei
  über 90 % MAC. Hinten begrenzt also bei jeder Masse zuerst der **Neutralpunkt** (43,8 % MAC).

## Befunde

1. **Der Abriss ist bei der Nennmasse nicht sauber erfasst.** Das Problem der Abrissgeschwindigkeit
   endet bei α ≈ 23°, nahe der Schranke von 25°. AeroBuildup/NeuralFoil liefert bei Re ≈ 50k kein klares
   C_L,max. V_S und die vordere Schwerpunktgrenze sind bei 100, 151 und 1100 g deshalb nicht belastbar;
   für die vordere Grenze findet der Solver dort keine Lösung. Vor der Freigabe ist ein Gegencheck des
   Abrisses nötig, gegen XFOIL oder Messwerte.
2. **Die vordere Grenze hat zwei Wurzeln.** Mit vollem Höhenruder hat Cm = 0 eine zweite Lösung hinter
   dem Neutralpunkt. Die Formulierung muss den Anstellwinkel beim Abriss festhalten und den Schwerpunkt
   auf die Seite vor dem Neutralpunkt beschränken. Die Geschwindigkeit bleibt frei, denn der Abtrieb
   des Höhenleitwerks hebt die getrimmte Abrissgeschwindigkeit. Nachgetragen in
   `canon/formulas/mass-envelope.md`.
3. **Bezugsfläche:** AeroSandbox rechnet 7,0 dm², der Plan nennt 6,3 dm². Die Differenz von 0,67 dm² ist
   der Flügel im Rumpf (45 mm × 149 mm). Das ist eine Konventionsfrage, kein Fehler; Flächenbelastungen
   unterscheiden sich dadurch um etwa 10 %.
4. **Der Antrieb ist stark:** Das Schub-Gewichts-Verhältnis liegt über 1, ROC_max beträgt 13,8 m/s, das
   Modell steigt senkrecht. Nach Antrieb und Aerodynamik trägt der Bryan das Achtfache seiner Masse;
   begrenzen wird die Struktur.
