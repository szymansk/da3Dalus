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
| Anflug 1,3·V_S = 6,88 m/s | −0,0489 | +0,0473 | +0,1685 | −0,1243 | −0,00189 |

Statisch ist das Modell roll- und richtungsstabil. Die Spirale ist schwach instabil (E < 0). Das ist ein
Wert, keine Bewertung (A10).

## Massenhüllkurve (korrigiert: Abriss auf dem ersten C_L-Maximum)

| m [g] | V_S [m/s] | V_max [m/s] | ROC_max [m/s] | T−D bei V_TO [N] | vordere Grenze [% MAC] (getrimmtes V_S) |
|---|---|---|---|---|---|
| 100 | 4,46 | 25,31 | 17,70 | +2,41 | 12,2 (4,7 m/s) |
| **151** | **5,29** | 25,38 | 13,80 | +2,25 | **14,3** (5,6 m/s) |
| 200 | 5,99 | 25,42 | 10,44 | +2,11 | 15,9 (6,3 m/s) |
| 300 | 7,22 | 25,46 | 6,73 | +1,85 | 17,5 (7,6 m/s) |
| 500 | 9,22 | 25,29 | 3,56 | +1,39 | 18,9 (9,7 m/s) |
| 800 | 11,61 | 24,35 | 1,48 | +0,77 | 19,7 (12,2 m/s) |
| 1100 | 13,59 | 22,20 | 0,35 | +0,21 | 20,0 (14,3 m/s) |

- **Schwerpunktbereich bei 151 g:** vorn 14,3 % MAC (volles Höhenruder hält den Abriss), hinten der
  Neutralpunkt bei 43,8 % MAC. Der Plan-Schwerpunkt (31,4 %) liegt mittig. Die vordere Grenze wandert mit
  der Masse nach hinten, weil die Abrissgeschwindigkeit und damit der Höhenruderbedarf steigen.
- **Grenzmassen:** m_max,level = **1228 g**, m_max,TO = **1218 g**. Das ist die aerodynamische und
  antriebsseitige Grenze, die Struktur ist nicht berücksichtigt (max-mass-structure braucht n_break des
  Holms).
- **Hintere Grenze:** Das Ruder (voll Tief bei V_max) trimmt erst weit hinter dem Neutralpunkt, bei über
  90 % MAC. Hinten begrenzt also bei jeder Masse zuerst der **Neutralpunkt**.

## Befunde

1. **Das Abrissproblem ist nicht konvex.** Das ganze Flugzeug hat in AeroBuildup ein sauberes
   C_L,max = 1,26 bei α = 12°. Danach folgt ein Plateau mit einem zweiten, kleineren Maximum von 1,07
   bei 23°. IPOPT ist vom allgemeinen Startwert aus dort hängen geblieben: V_S = 5,68 statt 5,29 m/s,
   und zwar **ohne aktive Schranke**, sodass die bisherige Freigabeprüfung es nicht bemerkt hat. (Eine
   frühere Fassung dieses Dokuments hielt den Abriss in AeroBuildup für unsauber erfasst. Das war falsch:
   Das 2D-Profil reißt in NeuralFoil bei Re 52k sauber bei 11° ab, C_L,max 1,26, Konfidenz 0,98.)
   Korrektur: erst eine α-Abtastung zum ersten Maximum, dann der Optimierer nur auf dem Ast vor dem
   Abriss. Nachgetragen in `canon/formulas/stall-speed.md`. **Das betrifft jedes Kanon-Problem nahe am
   Abriss** (Anflug, Start, engste Kurve, vordere Grenze). Ihre Freigabe braucht dieselbe Prüfung auf
   das globale Optimum.
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

## Nachprüfung aller Probleme nahe am Abriss (03.10.2026)

Gerechnet mit `bryan_stall_branch_check.py`. A ist die bisherige Lösung, B die auf den Ast vor dem
Abriss beschränkte.

| Problem | A | B | Befund |
|---|---|---|---|
| Manövergeschwindigkeit V_A | 8,79 m/s / 13,4° | gleich | unauffällig |
| engste Kurve | 8,79 / 13,4° | gleich | unauffällig |
| **schnellste Kurve** | **9,83 / 22,9°** | **8,79 / 13,4°** | **betroffen**: A liegt hinter dem Abriss |
| steilstes Steigen V_x | ≈ 3,5 / −3,4° | ≈ 3,5 / −3,4° | kein Abrissproblem: senkrecht, V_x nicht eindeutig (steht so im Kanon) |
| bestes Steigen V_y | 13,85 / −4,6° | gleich | unauffällig |
| geringstes Sinken V_mp | 6,19 / 4,4° | gleich | unauffällig |
| geringster Widerstand V_md | 7,82 / 0,7° | gleich | unauffällig |
| V_max | 25,38 / −5,1° | gleich | unauffällig |

Butterfly war nicht prüfbar, weil der Bryan keine Klappen hat. Die schnellste Kurve liegt beim Bryan an
der Ecke aus Abriss und n_lim; ihre richtige Lösung fällt mit der Manövergeschwindigkeit zusammen.

## Holm: Bruch-Lastvielfaches (03.10.2026)

Gerechnet mit `bryan_spar_break.py` nach dem Kanon-Eintrag spar-break-load-factor.

- **Holm:** I-Holm mit Birkensperrholz-Gurten 1,0 × 4,0 mm, bündig zur Kontur. Steg aus Balsa, 2 mm,
  Höhe 15,5 mm an der Wurzel. Kein Holmstoß.
- **Festigkeit:**
  - Druckgurt: Birke parallel zur Faser 56,3 MPa (USDA Wood Handbook, GTR-282). Beim dreilagigen
    Sperrholz tragen zwei der drei Lagen, also 37,5 MPa.
  - Zuggurt: 91,1 MPa (NACA Report 84, Elmendorf 1920, Tab. 4).
- **Last:** 1 g nach Schrenk (NACA TM 948). Die Gewichtsentlastung durch den Flügel ist vernachlässigt,
  das liegt auf der sicheren Seite.

| y [mm] | Holmhöhe [mm] | M_1g [N·mm] | M_cap, Druck [N·mm] | n |
|---|---|---|---|---|
| 0 | 15,5 | 88,7 | 4006 | **45,2** |
| 55 | 14,5 | 53,2 | 3553 | 66,8 |
| 109 | 13,5 | 27,3 | 3163 | 116 |
| 164 | 12,6 | 10,5 | 2789 | 265 |

- **n_break,+ = n_break,− = 45**, maßgebend an der Wurzel (Druckgurt; der Zuggurt allein trüge 110).
  Bei 25 bzw. 50 MPa Druckfestigkeit wären es 30 bzw. 60.
- **m_max,struct = 6,8 kg.** Das liegt weit über der Grenze von Antrieb und Aerodynamik
  (m_max,level 1,23 kg). Beim Bryan begrenzt der Holm also nie die Masse; bei 151 g liegen gemessene
  RC-Lasten (6–19 g) weit darunter.
- **Nicht gerechnet, nach Entscheidung:** Befestigung, Klebung, Schub im Steg, örtliches Beulen des
  1 mm dünnen Druckgurts zwischen den Rippen. Der Kanon rechnet nur die Festigkeit (BR-W18). Beulen
  wäre bei so dünnen Gurten die erste Frage, falls der Holm je knapp wird.
- **Geprüft, kein App-Befund (03.10.2026):** Die Wirbelgitter-Rechnung lieferte zuerst unbrauchbare
  Werte (Panelkräfte von 10⁹ N). Ursache war mein eigener Aufruf mit 24 Panels **je Segment**: Auf den
  winzigen Segmenten des runden Randbogens entstehen dadurch fast entartete Panels. Die App verteilt die
  Panels seit gh-855 proportional zur Segmentspanne (`vlm_strip_forces.remesh_uniform_density`). Auf dem
  Bryan liefert sie C_L = 0,587 mit plausiblem Verlauf; das Wurzelmoment bei 1 g ist 87,0 N·mm gegen
  88,7 N·mm nach Schrenk (−2 %). Schrenk ist hier also eine gute und leicht konservative Näherung.

## Seitenstabilität: AeroBuildup gegen AVL und VLM (03.10.2026)

Gerechnet mit `bryan_lateral_avl.py` bei V_md und gleichem C_L = 0,565, Bezug Plan-Schwerpunkt.
- **AVL:** Die AFIL-Verweise zeigen auf die Original-Profildateien, weil der ASB-Export x > 1 schreibt.
  Ausgelesen wird der erste Treffer, weil AVL zusätzlich die Spiralzeile „Clb Cnr / Clr Cnb = …" druckt.
- **VLM:** ASB-Wirbelgitter mit einem Panel je Segment.

| Methode | C_lβ | C_nβ | C_lp | C_nr | C_lr | C_np | E_spiral |
|---|---|---|---|---|---|---|---|
| AeroBuildup mit Rumpf | −0,055 | **+0,050** | **−0,819** | −0,127 | +0,151 | −0,060 | −0,0006 |
| AeroBuildup ohne Rumpf | −0,052 | +0,103 | −0,819 | −0,127 | +0,151 | −0,060 | – |
| AVL mit Rumpf | −0,066 | +0,122 | −0,349 | −0,162 | +0,137 | −0,039 | −0,0060 |
| AVL ohne Rumpf | −0,072 | +0,119 | −0,350 | −0,161 | +0,137 | −0,039 | – |
| VLM ohne Rumpf | −0,020 | +0,150 | −0,364 | −0,275 | +0,143 | −0,070 | – |

**Befunde:**
1. **Die Rolldämpfung ist in AeroBuildup 2,3-fach zu groß.** AVL (−0,349) und VLM (−0,364) stimmen
   überein, AeroBuildup liefert −0,819. Plausibel ist ein streifenweises Modell ohne die Entlastung durch
   den induzierten Abwind bei antisymmetrischer Last. **Folge für den Kanon:** `max-roll-rate` und
   `aileron-throw-fraction` rechnen die stationäre Rollrate mit AeroBuildup und **unterschätzen sie etwa
   um diesen Faktor.** Das blockiert ihre Freigabe; Werkzeug oder Korrektur ist zu entscheiden.
   **Folge für die App:** Der Analyse-Endpunkt gibt C_lp aus AeroBuildup als „Roll Damping" aus,
   ohne Hinweis. Rollraten selbst rechnet die App nur mit AVL.
2. **Die Richtungsstabilität ohne Rumpf stimmt grob überein** (AeroBuildup 0,103, AVL 0,119,
   VLM 0,150). **Mit Rumpf halbiert AeroBuildup C_nβ** auf 0,050 (destabilisierendes Rumpfmoment), AVL
   kaum (0,122). AVL modelliert Rümpfe nur grob. Welcher Rumpfbeitrag stimmt, bleibt offen und braucht
   eine dritte Quelle (z. B. DATCOM-Rumpfanteil).
3. **Die Schieberollmomente liegen nah beieinander:** AeroBuildup −0,055, AVL −0,066. Den Einfluss der
   Flügellage (Hochdecker) erfasst AeroBuildup also in der Größenordnung. Die VLM (−0,020) hat keinen
   Rumpf und damit keinen Hochdeckereffekt.
4. **Die Spirale ist in allen Methoden schwach instabil.** Das Vorzeichen stimmt; der Betrag
   unterscheidet sich um den Faktor 10.
