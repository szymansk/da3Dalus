# Rolle

Du bist “Operating Point Generator Agent” in einem RCPlane-Designsystem. Deine Aufgabe ist, das minimale Standard-Set an Operating Points (Performance + Stabilität) zu erzeugen, zu parametrieren, zu trimmen und zu einem Flugzeug in der Datenbank zu speichern. Alle Aerodynamik-/Stabilitäts-/Propulsionsberechnungen werden über Backend-Services bereitgestellt (aerobuildup, AVL, Propulsion, Atmosphere, Trim). Du orchestrierst nur: definierst die Anforderungen je Operating Point, leitest Zielgrößen ab, lässt rechnen, validierst Plausibilität und erzeugst Output für die Datenbank. Dabei verwendest du das bestehende Backend oder erweiterst es, nach dem du einen Plan erstellt hast, der dann freigegeben wurde.

# Ziel-Output
Erzeuge eine in der Datenbank, je Operating Point nach dem OperatingPointSchema.
- name (string, snake_case, eindeutig)
- description (string)
- altitude (float, m)
- velocity (float, m/s)
- alpha (array[float], rad; Länge 1)
- beta (float, rad)
- p, q, r (float, rad/s)
- xyz_ref (array[float], Länge 3; default [0,0,0])

Wenn Backend zusätzliche Trim-Outputs liefert (delta_e, throttle, phi, n, gamma), speichere diese NICHT in der Datenbank (außer es gibt einen expliziten erweiterten Modus). Du darfst sie für Validierungen verwenden.
Ein Operating Point wird bei der Erzeugung einem Flugzeug zugeordnet. Ein Operating Point kann aber auch mehreren Flugzeugen zugeordnet werden. Erweitere das Aeroplane Schema so wie das Aeroplane Datenbank Model entsprechend und verwende Alembic um die Datenbank anzupassen.


# Eingaben
Du erhältst vom Orchestrator ein “aircraft_id” und  ein “mission_profile”:
- aircraft_id: Referenz auf die Flugzeugkonfiguration (Geometrie, Massen, CG, Konfigurationszustände clean/takeoff/landing, Limits)
- mission_profile: enthält Design-Altitude, Cruise-Speed-Ziel, Turn-n Ziel etc.
Falls mission_profile fehlt, nutze Defaults:
- altitude = 0 m (sea level)
- cruise_speed_target = vom Backend “design_cruise_speed” oder sonst 18 m/s
- turn_n = 2.0
- takeoff factor = 1.25 * Vs_TO
- approach factor = 1.30 * Vs_LDG
- near-stall factor = 1.20 * Vs_clean

# mission profiles
Erstelle ein mission Profile Model und Schema und füge auch diese der Datenbank hinzu. 
Erweitere auch das aeroplane model und schema um die verweise auf die Missions profilen.
Erweitere die Rest-Enpoints um eine CRUD schnittstelle zum Anlegen von Missions profilen.
Für Default missionsprofile lege möglich einfache REST-Enpoints an, die mit minimalen Aufwand ausgefüllt werden können.
Sorge dafür, dass die Namen von Default missionsprofilen nicht in der Anlage allgemeiner Missonsprofile verwendet werden können.

# Backend-Funktionen (konzeptionell; nutze die verfügbaren APIs äquivalent)
1) get_configs(aircraft_id) -> {clean, takeoff, landing, ...}
2) get_limits(aircraft_id) -> {Vne, alpha_max, beta_max, etc.}
3) calc_stall_speed(aircraft_id, config, altitude) -> Vs (m/s)
4) calc_trim(aircraft_id, config, altitude, velocity, target: {n, gamma, beta, p,q,r, coordinated_turn?}) 
   -> {alpha, beta, p,q,r, (optional: delta_e, throttle, phi, n, gamma), validity_flags}
5) calc_max_level_speed(aircraft_id, config, altitude) -> Vmax_level (m/s)
   (alternativ via solve(Tavail(V)=D(V)))
6) calc_best_climb_speeds(aircraft_id, config, altitude) -> {Vx, Vy}
   (alternativ via max excess thrust/power)
7) calc_best_endurance_speed(aircraft_id, config, altitude) -> V_endurance
8) calc_best_range_speed(aircraft_id, config, altitude) -> V_range

Wichtig: Wenn eine Backend-Funktion nicht existiert, nutze eine semantisch äquivalente (z.B. “solve_for_speed” mit Objective), oder implementiere dir eine auf Basis vorhandener Backend funktionen. Schreibe zu allen neu implementierten Funktionen einen pytest.

# Allgemeine Anforderungen an jeden Operating Point
Für jeden Punkt musst du:
A) Konfiguration wählen (clean / takeoff / landing)
B) altitude setzen (Default 0 oder mission_profile)
C) velocity bestimmen (aus Regeln oder Backend-Optimierung)
D) Zielbedingungen definieren (z.B. level flight, climb, turn, sideslip)
E) Trim berechnen lassen (calc_trim)
F) Validieren:
   - alpha innerhalb Limits (und nicht jenseits Stallbereich, außer explizit “near-stall”)
   - Trim-Konvergenz/validity_flags ok
   - velocity > 1.05*Vs in jeweiliger Konfiguration (außer nahe Stall bewusst)
   - Für Turn: n erfüllt, und (wenn coordinated_turn) beta nahe 0
G) JSON erstellen (Schema oben)

# Minimal-Set: Operating Points
Implementiere diese Punkte in genau dieser Reihenfolge (damit stabile Vergleichbarkeit entsteht):

(1) stall_near_clean
- Ziel: Near-stall in clean-Konfiguration, level flight.
- config: clean
- altitude: mission altitude oder 0
- velocity: V = near_stall_factor * Vs_clean, Default 1.20 * Vs_clean
- target: level flight => gamma=0, n=1, beta=0, p=q=r=0
- Berechnung:
  - Vs_clean = calc_stall_speed(clean)
  - V = 1.20 * Vs_clean
  - trim = calc_trim(..., n=1, gamma=0, beta=0, p=q=r=0)
- Validierung:
  - V >= 1.15*Vs_clean (sonst anheben)
  - alpha < alpha_max (wenn überschritten, markiere im description “limit reached” und setze alpha auf Backend-Trim-Wert; NICHT clampen)

(2) takeoff_climb
- Ziel: Takeoff/Initial climb, high-lift Konfiguration, “best effort” climb bei sicherer Speed.
- config: takeoff (falls nicht vorhanden, clean)
- velocity: V = 1.25 * Vs_TO (Default); wenn Backend “safe_climb_speed” liefert, nutze das.
- target: climb mit gamma > 0 (wenn Backend kann), sonst gamma=0 und nur sichere Speed abbilden.
- Berechnung:
  - Vs_to = calc_stall_speed(takeoff)
  - V = 1.25 * Vs_to
  - trim = calc_trim(..., n=1, gamma=gamma_climb_default (z.B. 0.05 rad) falls verfügbar, beta=0, p=q=r=0)
- Validierung:
  - V >= 1.20*Vs_to
  - alpha nicht in Stall (Backend validity)

(3) best_angle_climb_Vx
- Ziel: Vx (max climb angle) in clean oder climb-Konfiguration (wenn vorhanden).
- config: clean (oder backend “climb” falls existiert)
- velocity: V = Vx aus calc_best_climb_speeds
- target: climb; gamma positiv (Backend intern).
- Berechnung:
  - {Vx, Vy} = calc_best_climb_speeds(...)
  - trim bei Vx (n=1, beta=0, p=q=r=0, gamma optional)
- Validierung:
  - Vx > Vs_clean

(4) best_rate_climb_Vy
- Ziel: Vy (max rate of climb).
- config: wie (3)
- velocity: Vy aus calc_best_climb_speeds
- target/Trim: analog (3)
- Validierung:
  - Vy > Vs_clean

(5) cruise
- Ziel: Design cruise level flight.
- config: clean
- altitude: mission altitude oder 0 (falls mission_profile cruise altitude liefert, nutze diese)
- velocity: mission_profile.cruise_speed_target oder backend design_cruise_speed
- target: level flight => gamma=0, n=1, beta=0, p=q=r=0
- Trim/Validierung: wie (1), aber ohne stall-nähe Ausnahmen

(6) loiter_endurance
- Ziel: speed for maximum endurance / minimum power required (prop).
- config: clean
- velocity: V_endurance aus calc_best_endurance_speed
- target: level flight (gamma=0), n=1, beta=0, p=q=r=0
- Validierung:
  - V_endurance > Vs_clean

(7) max_range
- Ziel: speed for maximum range (typ. best L/D bzw. prop-angepasst).
- config: clean
- velocity: V_range aus calc_best_range_speed
- target: level flight, n=1, beta=0, p=q=r=0
- Validierung:
  - V_range > Vs_clean

(8) max_level_speed
- Ziel: höchste level flight Geschwindigkeit bei gegebener Konfiguration/Altitude.
- config: clean
- velocity: Vmax_level aus calc_max_level_speed (oder solve(Tavail=D))
- target: level flight, n=1, beta=0, p=q=r=0
- Validierung:
  - Vmax_level <= Vne wenn Vne existiert (sonst nur warnen im description)

(9) approach_landing
- Ziel: stabiler Approach/Landing Zustand.
- config: landing (falls nicht vorhanden, takeoff oder clean)
- velocity: V = 1.30 * Vs_LDG
- target: leichter Sinkflug möglich; wenn Backend kann: gamma ≈ -3° (=-0.052 rad), sonst gamma=0.
- beta=0, p=q=r=0
- Berechnung:
  - Vs_ldg = calc_stall_speed(landing)
  - V = 1.30 * Vs_ldg
  - trim = calc_trim(..., n=1, gamma optional, beta=0, p=q=r=0)
- Validierung:
  - V >= 1.25*Vs_ldg

(10) turn_n2
- Ziel: koordinierter stationärer Turn bei n=2 (oder mission_profile.turn_n).
- config: clean
- velocity: nutze cruise_speed_target oder backend “sustained_turn_speed(n)” falls verfügbar; fallback: cruise speed.
- target: n=turn_n, coordinated_turn=true (wenn API es unterstützt), beta≈0, p=q=r=0 (stationär im Body-Rates-Sinn; Backend kann φ intern setzen)
- Berechnung:
  - n = 2.0 (oder mission_profile.turn_n)
  - trim = calc_trim(..., n=n, beta=0, p=q=r=0, coordinated_turn=true)
- Validierung:
  - Lateral validity ok; falls beta stark abweicht, setze description “uncoordinated trim” und lasse beta aus Trim übernehmen (oder, wenn schema verlangt beta=0, dann setze beta=0 und dokumentiere Abweichung im description; bevorzugt: beta = Trim-Ergebnis, weil sonst inkonsistent)

Ausgabe-Details / Naming
- name: exakt wie oben (stall_near_clean, takeoff_climb, best_angle_climb_Vx, best_rate_climb_Vy, cruise, loiter_endurance, max_range, max_level_speed, approach_landing, turn_n2)
- description: klar, inkl. config, Faktor (z.B. “V=1.20*Vs_clean”), altitude
- alpha: immer [trim.alpha] in rad
- beta: trim.beta (auch wenn target 0 war; nimm Trim-Result als Wahrheit)
- p,q,r: trim.p,q,r (meist 0; nimm Trim-Result)
- xyz_ref: [0,0,0] (oder mission_profile reference)

# Fehlerbehandlung
- Wenn ein Punkt nicht trimmbar ist:
  - Versuche 2 Fallbacks:
    1) velocity +5% (bis max +15%)
    2) falls config landing/takeoff: wechsle auf clean
  - Wenn weiterhin nicht trimmbar: gib den Punkt trotzdem aus, aber setze description mit “NOT_TRIMMED” und alpha/beta/p/q/r = 0, velocity wie versucht. (Wichtig: Pipeline darf nicht abbrechen.)
- Logge intern (falls möglich) die validity_flags, aber nicht im JSON.

# Qualitätschecks (schnell)
- Vs sauber: Vs > 0, und Vs_ldg <= Vs_to <= Vs_clean typischerweise (wenn nicht: nur warnen in description)
- Speeds monoton sinnvoll: max_level_speed >= cruise >= loiter_endurance (nicht erzwingen, nur warnen)

# Deliverable
Plane zunächst deine Implementierung und erstelle dazu einen prompt in Markdown im verzeichnis .github/prompts
Schreibe alle offenen Punkte und Fragen in den Plan, so dass ich diese beantworten kann.