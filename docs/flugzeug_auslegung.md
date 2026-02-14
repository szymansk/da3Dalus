# Auslegung von RC-Flugprofilen (FlightProfiles) – Richtwerte, Physik, Parametrisierung

Ziel: **Flugprofile** so definieren, dass sie (a) für Anfänger verständlich sind, (b) physikalisch konsistent bleiben und (c) später **automatisch auf ein konkretes Flugzeug** (Gewicht/Fläche/Aerodynamik/Antrieb) gemappt und validiert werden können.

Das Profilmodell (vereinfacht) umfasst:
- **Environment** (Höhe, Wind)
- **Goals** (cruise/max speed, Margins, target_turn_n, loiter)
- **Handling** (Stability feel, Rollrate, Pitch/Yaw-Toleranzen)
- **Constraints** (max_bank, max_alpha, max_beta)

---

## 1) RC-Klassifikation aus der Praxis (Web-Quellen)

Für “typische” Klassenbegriffe (Segler, Motorflug, Einsteiger, Trainer, …) eignen sich u.a.:
- RC-Network Wiki: Übersichtsseiten und Kategorien für Flugmodelle.  [oai_citation:0‡RC-Network Wiki](https://wiki.rc-network.de/wiki/Flugmodelle_%C3%9Cbersicht?utm_source=chatgpt.com)
- rcflug.ch Plandatenbank: filterbare Kategorien/Modelle als grobe Taxonomie-Inspiration.  [oai_citation:1‡RCFlug](https://www.rcflug.ch/plan/modelle.php?utm_source=chatgpt.com)

Für **numerische Ankerwerte** (Flächenbelastung, Stall, Va/Vne usw.) ist air-rc.com sehr hilfreich, weil viele Einträge diese Größen explizit nennen. Beispiele zeigen eine große Spannweite:
- Leichte Modelle mit ca. **31 g/dm²** und **Vs ~15 km/h**.  [oai_citation:2‡air-rc.com](https://www.air-rc.com/aircraft/3D-LabPrint_VL-Pyorremyrsky_VLP?utm_source=chatgpt.com)  
- Größere/schnellere Modelle mit ca. **83 g/dm²** und **Vs ~32 km/h**, inkl. Va/Vne-Werten.  [oai_citation:3‡air-rc.com](https://www.air-rc.com/aircraft/3D-LabPrint_B-25J-Mitchell_b25fm?utm_source=chatgpt.com)  
- Sehr hohe Flächenbelastung um **104 g/dm²** und **Vs ~50 km/h** (Jet/EDF-ähnlich).  [oai_citation:4‡air-rc.com](https://www.air-rc.com/aircraft/3D-LabPrint_F-86A-Sabre_F86A?utm_source=chatgpt.com)

Diese Beispiele sind keine Norm, aber **gute Plausibilitätsanker**.

---

## 2) Physikalische Grundlagen (Formeln)

### 2.1 Auftriebsgleichung und Stallgeschwindigkeit

Grundgleichung (stationär):
- Inline: $L=\tfrac12\rho V^2 S C_L$

Im stationären Horizontalflug gilt näherungsweise $L\approx W$ (Gewichtskraft). Beim Stall erreichst du $C_{L,\max}$; daraus folgt:

$$
V_s=\sqrt{\frac{2W}{\rho S C_{L,\max}}}
$$

**Interpretation (wichtig für Parametrisierung):**
- Mehr Gewicht $W$ ⇒ $V_s$ steigt mit $\sqrt{W}$
- Größere Fläche $S$ ⇒ $V_s$ sinkt mit $1/\sqrt{S}$
- Größeres $C_{L,\max}$ ⇒ $V_s$ sinkt mit $1/\sqrt{C_{L,\max}}$
- Geringere Dichte $\rho$ (z.B. hohe Platzhöhe) ⇒ $V_s$ steigt mit $1/\sqrt{\rho}$

Quelle (Stall-Gleichung aus Vorlesung/Performance-Grundlagen):  [oai_citation:5‡MIT OpenCourseWare](https://ocw.mit.edu/courses/16-333-aircraft-stability-and-control-fall-2004/9befd7ea465e31f9ff763c5587815264_lecture_1.pdf?utm_source=chatgpt.com)

---

### 2.2 Flächenbelastung als “Master-Parameter”

Flächenbelastung:
- Inline: $\tfrac{W}{S}$

Sie ist in RC-Daten häufig in **g/dm²** angegeben (anstatt SI-$N/m^2$). Der Grund: handlich, weil viele Modellflächen in dm² gerechnet werden. air-rc.com nutzt diese Darstellung ebenfalls.  [oai_citation:6‡air-rc.com](https://www.air-rc.com/aircraft/3D-LabPrint_B-25J-Mitchell_b25fm?utm_source=chatgpt.com)

Praktische Konsequenz:
- Wenn du $W/S$ ungefähr kennst, kannst du über $V_s$ sofort abschätzen, ob deine Profil-Geschwindigkeiten (Cruise/Approach) überhaupt plausibel sind.

---

### 2.3 Kurvenflug: Bankwinkel $\varphi$ ↔ Lastvielfaches $n$

Im koordinierten (nicht rutschenden) Kurvenflug gilt:

$$
n=\frac{1}{\cos\varphi}
$$

Damit folgen die beiden Richtungen:

**Erreichbares Maximum bei gegebener Bankbegrenzung:**
$$
n_{\max}=\frac{1}{\cos\varphi_{\max}}
$$

**Benötigter Bankwinkel für gewünschtes $n$:**
$$
\varphi_{\min}=\arccos\left(\frac{1}{n}\right)
$$

Quelle (Grundlagen Turn-Performance/Loads in Performance-Vorlesung):  [oai_citation:7‡MIT OpenCourseWare](https://ocw.mit.edu/courses/16-333-aircraft-stability-and-control-fall-2004/9befd7ea465e31f9ff763c5587815264_lecture_1.pdf?utm_source=chatgpt.com)

---

### 2.4 Deine Profil-Margins als saubere Abstraktion

Du definierst im Profil **keine** Stallgeschwindigkeit, sondern nur Sicherheitsmargen:

- Clean:
  $V_{\min,\text{clean}}=m_{\text{clean}}\cdot V_{s,\text{clean}}$
- Takeoff:
  $V_{\text{TO}}=m_{\text{TO}}\cdot V_{s,\text{TO}}$
- Approach/Landing:
  $V_{\text{APP}}=m_{\text{LDG}}\cdot V_{s,\text{LDG}}$

Damit bleibt das Profil **flugzeugunabhängig**, aber später **rechenbar**, sobald $W,S,C_{L,\max}$ bekannt sind.

---

## 3) Richtwert-Tabelle für FlightProfileType (min / median / max)

**Konventionen:**
- Geschwindigkeiten in **m/s** (TAS-Zielwerte).
- Werte sind **Profil-Targets**, nicht “jede Kiste kann das”.
- Für Segler sind zusätzliche Leistungsgrößen (z.B. $L/D$, Sinkrate) wichtig, aber nicht im Profilmodell enthalten → siehe Abschnitt 5.

### 3.1 Motorgetriebene Profile (trainer, warbird, fpv_cruiser, three_d, motor_glider)

| FlightProfileType | cruise_speed_mps (min/med/max) | max_level_speed_mps (min/med/max) | target_turn_n (min/med/max) | max_bank_deg (min/med/max) | roll_rate_target_dps (min/med/max) | min_speed_margin_vs_clean (min/med/max) | takeoff_speed_margin_vs_to (min/med/max) | approach_speed_margin_vs_ldg (min/med/max) | Hinweise |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| trainer | 12 / 18 / 24 | 20 / 30 / 40 | 1.3 / 1.8 / 2.2 | 35 / 50 / 60 | 60 / 120 / 180 | 1.20 / 1.25 / 1.35 | 1.20 / 1.25 / 1.35 | 1.25 / 1.30 / 1.40 | Für Einsteiger konservativ. In realen Modell-Daten finden sich niedrige Flächenbelastungen und sehr niedrige Vs bei “easy flyers”.  [oai_citation:8‡air-rc.com](https://www.air-rc.com/aircraft/3D-LabPrint_VL-Pyorremyrsky_VLP?utm_source=chatgpt.com) |
| warbird | 15 / 22 / 30 | 28 / 40 / 55 | 1.5 / 2.2 / 3.0 | 45 / 60 / 75 | 90 / 170 / 260 | 1.25 / 1.30 / 1.40 | 1.20 / 1.25 / 1.35 | 1.25 / 1.30 / 1.45 | Tendenziell höhere Flächenbelastung und höhere Va/Vne in Datensätzen.  [oai_citation:9‡air-rc.com](https://www.air-rc.com/aircraft/3D-LabPrint_B-25J-Mitchell_b25fm?utm_source=chatgpt.com) |
| fpv_cruiser | 14 / 20 / 26 | 22 / 30 / 40 | 1.2 / 1.5 / 2.0 | 30 / 45 / 60 | 40 / 90 / 160 | 1.25 / 1.30 / 1.40 | 1.20 / 1.25 / 1.35 | 1.30 / 1.35 / 1.50 | Stabilität/Komfort wichtiger als Agilität; eher “ruhige Plattform”. |
| three_d | 8 / 14 / 20 | 20 / 30 / 40 | 1.2 / 1.8 / 2.5 | 45 / 65 / 85 | 200 / 360 / 600 | 1.30 / 1.35 / 1.50 | 1.20 / 1.25 / 1.35 | 1.30 / 1.35 / 1.50 | 3D kann langsam sein, braucht aber extreme Steuerwirkung (Rollrate/Alpha-Budget). |
| motor_glider | 10 / 16 / 22 | 18 / 26 / 36 | 1.2 / 1.6 / 2.2 | 35 / 50 / 65 | 40 / 90 / 160 | 1.25 / 1.30 / 1.45 | 1.20 / 1.25 / 1.35 | 1.30 / 1.35 / 1.50 | Mischung: Motor für Steigen/Transit, danach seglerähnlicher Betrieb; in Beispieldaten finden sich niedrige Wingloadings bei seglerartigen Auslegungen.  [oai_citation:10‡air-rc.com](https://www.air-rc.com/aircraft/3D-LabPrint_A6M2-ZERO_A6M2?utm_source=chatgpt.com) |

### 3.2 Segler-Profile (glider) – separat, weil Ziele anders gewichtet sind

| FlightProfileType | cruise_speed_mps (min/med/max) | max_level_speed_mps | target_turn_n (min/med/max) | max_bank_deg (min/med/max) | min_speed_margin_vs_clean (min/med/max) | approach_speed_margin_vs_ldg (min/med/max) | Hinweise |
|---|---:|---:|---:|---:|---:|---:|---|
| glider (Thermik/Allround) | 9 / 13 / 18 | optional | 1.1 / 1.4 / 2.0 | 25 / 40 / 60 | 1.25 / 1.30 / 1.50 | 1.30 / 1.35 / 1.60 | Thermik: niedrige Sinkrate und gutes $L/D$ sind entscheidend (nicht im Profilmodell). |
| glider (Speed/Hang) | 12 / 18 / 28 | optional | 1.3 / 1.8 / 2.8 | 35 / 55 / 75 | 1.20 / 1.25 / 1.40 | 1.25 / 1.30 / 1.50 | Höhere Wingloadings (Ballast) sind üblich; Vs steigt entsprechend. Beispiele zeigen sehr hohe Wingloadings und Vs für schnelle Modelle.  [oai_citation:11‡air-rc.com](https://www.air-rc.com/aircraft/3D-LabPrint_F-86A-Sabre_F86A?utm_source=chatgpt.com) |

---

## 4) Parametrisierung: Wie du aus (Profil + Flugzeug) rechenbare Targets machst

### 4.1 Was das Profil vorgibt vs. was das Flugzeug liefern muss

**Profil gibt vor (dein Modell):**
- $V_\text{cruise}$, ggf. $V_\text{max}$
- Sicherheitsmargen $m_\text{clean}$, $m_\text{TO}$, $m_\text{LDG}$
- $n_\text{target}$ und Limits $\varphi_\text{max}$, $\alpha_\text{max}$, $\beta_\text{max}$
- Handling-Ziele (Rollrate etc.)

**Flugzeug muss liefern (separates Aircraft-Modell / Analyse):**
- Gewicht $W$ (min/typ/max)
- Fläche $S$
- $C_{L,\max}$ clean / TO / LDG (oder Ersatzannahmen)
- Dichte $\rho$ (aus Höhe/ISA; dein `altitude_m` ist der Trigger)

Erst dann kannst du **physikalische Checkgrößen** berechnen:
- $V_{s,\text{clean}}$, $V_{s,\text{TO}}$, $V_{s,\text{LDG}}$ über $$V_s=\sqrt{\tfrac{2W}{\rho S C_{L,\max}}}$$  [oai_citation:12‡MIT OpenCourseWare](https://ocw.mit.edu/courses/16-333-aircraft-stability-and-control-fall-2004/9befd7ea465e31f9ff763c5587815264_lecture_1.pdf?utm_source=chatgpt.com)
- daraus die Profil-Targets:
  - $V_{\min,\text{clean}}=m_\text{clean}\cdot V_{s,\text{clean}}$
  - $V_\text{TO}=m_\text{TO}\cdot V_{s,\text{TO}}$
  - $V_\text{APP}=m_\text{LDG}\cdot V_{s,\text{LDG}}$

### 4.2 Turn-Check (dein vorhandener Validator ist korrekt)
Aus $\varphi_\text{max}$ folgt:
$$
n_{\max}=\frac{1}{\cos\varphi_{\max}}
$$
und du musst sicherstellen:
$$
n_\text{target}\le n_{\max}
$$
Quelle: Turn-Loads/Performance-Grundlagen.  [oai_citation:13‡MIT OpenCourseWare](https://ocw.mit.edu/courses/16-333-aircraft-stability-and-control-fall-2004/9befd7ea465e31f9ff763c5587815264_lecture_1.pdf?utm_source=chatgpt.com)

### 4.3 (Motor) Machbarkeit von cruise/max speed: “Leistung/Schub reicht?”
Für Motorprofile ist der entscheidende Machbarkeitstest:
- bei $V_\text{cruise}$ und $V_\text{max}$ muss gelten: **verfügbarer Schub/Leistung ≥ benötigter Widerstand/Leistung**.

Konzeptionell (ohne hier ein komplettes Prop-Modell aufzuspannen):
- Level flight: $T_\text{avail}(V)\ge D(V)$
- Power: $P_\text{avail}(V)\ge P_\text{req}(V)$

Diese Logik ist Standard in Performance-Vorlesungen.  [oai_citation:14‡MIT OpenCourseWare](https://ocw.mit.edu/courses/16-333-aircraft-stability-and-control-fall-2004/9befd7ea465e31f9ff763c5587815264_lecture_1.pdf?utm_source=chatgpt.com)

---

## 5) Segler: wichtige “Derived Targets” (nicht im FlightProfile-Schema, aber sinnvoll)

Bei Seglern reichen Geschwindigkeiten allein nicht, weil die Mission oft durch Gleitleistung/Steigen bestimmt wird:
- bestes Gleiten: $L/D_\text{max}$ (hoher Wert = effizient)
- Minimales Sinken: $w_\text{min}$ (klein = gut)
- Speed-to-Fly (abhängig von Aufwind/Polar)

Dein Profilmodell kann das (noch) nicht ausdrücken; pragmatisch:
- Hinterlege pro Segler-Profil **Derived Targets** in der Analyseebene (nicht im Profile-DB-Schema), damit du Profile trotzdem bewerten kannst.

---

## 6) Mermaid-Abhängigkeitsgraph (parser-sicher)

```mermaid
graph TD
  Alt[Environment altitude_m] --> Rho[Air density rho]
  W[Takeoff weight W] --> WS[Wing loading W over S]
  S[Wing area S] --> WS
  CLmax[CLmax clean TO LDG] --> Vs[Stall speed Vs]
  Rho --> Vs
  WS --> Vs

  Vs --> VminCleanTarget[Vmin clean target = margin_clean * Vs_clean]
  Vs --> VtoTarget[Vto target = margin_TO * Vs_TO]
  Vs --> VappTarget[Vapp target = margin_LDG * Vs_LDG]

  Cruise[Cruise speed target] --> FeasibleCruise{Feasible at cruise}
  Vmax[Max level speed target] --> FeasibleVmax{Feasible at Vmax}
  Drag[Drag required D of V] --> FeasibleCruise
  Thrust[Thrust or power available] --> FeasibleCruise
  Drag --> FeasibleVmax
  Thrust --> FeasibleVmax

  Bank[Max bank deg] --> Nmax[nmax = 1 over cos phi]
  TurnN[Target turn n] --> CheckN{Turn n <= nmax}
  Nmax --> CheckN

  RollRate[Roll rate target dps] --> ControlSizing[Control authority sizing]