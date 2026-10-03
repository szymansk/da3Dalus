# e-Hawk: Kanon-Ergebnisse (03.10.2026)

Zweites Flugzeug der Referenzflotte. Segler mit 1,50 m Spannweite und 280 g, V-Leitwerk, Querruder,
Kapselrumpf mit CFK-Rohr. Die Geometrie stammt aus den Projekten eHawk_Tragflaeche und
eHawk_Rumpf_R4 des Maintainers, zusammengesetzt mit `build_ehawk.py` (Annahmen dort). Gerechnet mit
`ehawk_canon.py`.

| Größe | Wert |
|---|---|
| Flächenbelastung | 14,0 g/dm² (Bericht: 14,0) |
| Streckung / MAC | 11,3 / 139,8 mm |
| Abriss | erstes C_L-Maximum 1,106 bei 9,0° → **V_S = 4,51 m/s** |
| V_md / beste Gleitzahl | 6,39 m/s / **14,3** |
| V_mp / geringstes Sinken | 4,90 m/s / **0,38 m/s** |
| Neutralpunkt AeroBuildup / AVL | 58,4 / **48,8 % MAC** |
| Plan-Schwerpunkt | 33,0 % MAC → Stabilitätsmaß 25,4 % (AeroBuildup) bzw. **15,8 % (AVL)** |

**Drela-Kennzahlen (BAENDER §3b, mit Querrudern):**
- V_H = 0,45: im Band 0,3–0,6.
- V_V = 0,025: am oberen Rand des Bands 0,015–0,025.
- Äquivalente V-Form ≈ 2,2°, daraus **B = 1,2**, unter dem Band 2–5. Das heißt nach Rawdon
  spiralinstabil, passend zu E_spiral < 0 in beiden Methoden.

**Seitenstabilität bei V_md (C_L 0,550):**

| | C_lβ | C_nβ | C_lp | C_nr | C_lr | E_spiral |
|---|---|---|---|---|---|---|
| AeroBuildup | −0,085 | +0,117 | −0,98 | −0,103 | +0,121 | −0,0054 |
| AVL | −0,083 | +0,082 | −0,59 | −0,077 | +0,157 | −0,0066 |

- Das Schieberollmoment stimmt fast exakt.
- Die Richtungsstabilität ist in AeroBuildup um 40 % größer.
- Die lokale Rolldämpfung ist in AeroBuildup um den Faktor 1,7 größer (vgl. #1153).

## Befunde

1. **Der Neutralpunkt aus AeroBuildup liegt etwa 10 % MAC zu weit hinten** (58,4 gegen 48,8 %; beim
   BRYAN 43,7 gegen 33,1 %). AeroBuildup kennt nur den Eigenabwind jeder Fläche, nicht den Abwind des
   Flügels am Leitwerk (`aero_buildup.py:746`). Die App übernimmt diesen Neutralpunkt für den
   empfohlenen Schwerpunkt; das ist ein Fehler in der unsicheren Richtung, **Ticket #1154**.
2. **Querruder über mehrere Segmente (geklärt, Ticket #1155):** Die vier Segmente „aileron" sind ein
   Querruder. Die Folgesegmente erben vom ersten (gegenläufig, ±35°); in der Quelle tragen sie die
   Vorgabewerte des Konstruktors. Die App wendet diese Vererbung beim Import nicht an und würde drei
   Viertel des Querruders als Klappe rechnen. `build_ehawk.py` setzt die Vererbung jetzt um. Die
   Ergebnisse oben ändert das nicht, denn keines hängt am Querruderausschlag.
