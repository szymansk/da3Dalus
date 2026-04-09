---
name: elliptische-fluegel-planform
description: Erzeugt eine elliptische Flügel-Planform als JSON-Stützpunktliste (y, xyz_le, xyz_te, chord) aus Gesamtspannweite S und Root-Chord c_root. Nutze dieses Skill, wenn du elliptische Planform/Chord-Verteilung brauchst oder Stützpunkte für Geometrieaufbau/Visualisierung/Export erzeugen willst. Ausgabe ist Root→Tip sortiert und soll unverändert weiterverwendet werden.
version: 0.0.1
author: "Marc Szymanski"
tags: ["elliptical", "wing", "flügel", "geometry", "planform"]
trigger_patterns:
  - "create elliptical wing planform"
  - "generate elliptical wing geometry"
  - "create elliptical wing"
  - "generate elliptical wing"
---

# Elliptische Flügel-Planform

## Ziel
Dieses Skill erzeugt eine **elliptische Flügel-Planform** als diskrete Stützpunkte:
```json
[
  {"y": 0.0, "xyz_le": 0.15, "xyz_te": -0.15, "chord": 0.3},
  ...
]
```

## Schnittstelle
### Eingaben
- `S` (float): Gesamtspannweite (**> 0**)
- `c_root` (float): Root chord (**> 0**)
- `N` (int, optional): Anzahl Stützpunkte (Default: **21**, **N ≥ 2**)

### Ausgabe
- JSON Array, sortiert **Root → Tip** (y von 0 bis S/2)
- Jeder Punkt enthält genau: `y`, `xyz_le`, `xyz_te`, `chord` (alle float)

## Harte Regeln
1. **Vor der Erzeugung validieren und korrigieren** (siehe unten).
2. **Für nachgelagerte Schritte ausschließlich** die erzeugte JSON-Liste verwenden (keine Rekonstruktion/Neuberechnung “nebenbei”).
3. Wenn Eingaben ungültig waren, **mit korrigierten Werten** erneut ausführen.

## Validierung & Korrektur
- Wenn `S <= 0`: setze `S = abs(S)`; falls `S == 0`, setze `S = 1e-6`.
- Wenn `c_root <= 0`: setze `c_root = abs(c_root)`; falls `c_root == 0`, setze `c_root = 1e-6`.
- Wenn `N` fehlt: setze `N = 11`.
- Wenn `N < 2`: setze `N = 2`.

## Nutzung (Python Script)
Dieses Skill enthält ein ausführbares Script:

- Datei: `scripts/elliptische_fluegel_planform.py`
- Zweck: Erzeugt die Stützpunktliste auf STDOUT als JSON.

### Beispiele
```bash
python3 scripts/elliptische_fluegel_planform.py --S 2.0 --c_root 0.3
python3 scripts/elliptische_fluegel_planform.py --S 2.0 --c_root 0.3 --N 51
```

### Weiterverwendung
- Nimm die JSON-Ausgabe **1:1** und nutze sie als Eingabe für Geometrieaufbau/Visualisierung/Export.
- Wenn du die Datei brauchst: `... > planform.json`

```bash
python3 scripts/elliptische_fluegel_planform.py --S 2.0 --c_root 0.3 > planform.json
```

## Mathematische Definition (für Review, nicht zum “Nebenher-Rechnen”)
Halbspannweite: `b = S/2`  
Chord-Verteilung: `c(y) = c_root * sqrt(1 - (y/b)^2)` für `y ∈ [0,b]`  
Stützpunkte: Cosinus-Verteilung:  
`y_i = b * sin(i * pi/2 / (N-1))` für `i=0..N-1`

- `xyz_le = c(y)/2` (leading edge, x+ vorne)
- `xyz_te = -c(y)/2` (trailing edge, x- hinten)

