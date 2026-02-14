# AeroSandbox: Cruise-Trim (Steady Level Flight)

Diese Datei beschreibt, wie man mit **AeroSandbox** einen **Cruise-Trim** als Optimierungsproblem aufsetzt, und enthält ein lauffähiges Beispiel (mit Platzhaltern für dein `airplane` und ein Propulsionsmodell).

---

## Grundprinzip

Ein Cruise-Trim wird in AeroSandbox typischerweise als **nichtlineares Optimierungsproblem** formuliert (über `asb.Opti`):

**Gegeben**
- Geschwindigkeit `V` (m/s)
- Höhe `h` (m)
- Masse `m` (kg)

**Gesucht (typisch)**
- `alpha` (Anstellwinkel, rad)
- `elevator_deflection` (Ruderausschlag, meist in **deg** in AeroSandbox)
- `throttle` (0..1) oder eine andere Leistungs-/Schub-Parametrisierung

**Constraints (steady level flight)**
- Lift-Gleichgewicht: `L(V,h,alpha,δe) = m*g`
- Pitch-Moment Null: `m_b(V,h,alpha,δe) = 0`
- Optional (für echten Cruise): Schub-Gleichgewicht `T(throttle,V,h) = D(V,h,alpha,δe)`

**Annahmen (Geradeausflug)**
- `beta=0`
- `p=q=r=0`
- keine Quer-/Giermoment-Constraints (kannst du später ergänzen)

---

## AeroSandbox-Bausteine

### 1) OperatingPoint (Zustand)
AeroSandbox nutzt `asb.OperatingPoint`, um Flugzustände wie `velocity`, `altitude`, `alpha`, `beta`, `p`, `q`, `r` zu definieren.

### 2) Control-Deflections (Ruder)
Ruderausschläge werden über das Airplane-Objekt gesetzt:
- `airplane.with_control_deflections({...})`
- Deflections sind in AeroSandbox **Grad** (typisch downwards-positive, je nach ControlSurface-Definition).

**Wichtig:** Der Key (z.B. `"elevator"`) muss exakt dem Namen deiner `ControlSurface` entsprechen.

### 3) Aerodynamik (z.B. AeroBuildup)
`asb.AeroBuildup(...).run()` liefert Kräfte/Momente (z.B. `L`, `D`, `m_b`) für den gegebenen Zustand und die Geometrie inkl. Deflections.

### 4) Optimierung (asb.Opti)
Mit `asb.Opti()` definierst du Variablen, Constraints und ein Ziel (`minimize(...)`), und löst dann mit `solve()`.

---

## Minimal-Beispiel: Cruise-Trim mit AeroBuildup

> **Hinweis:** Du brauchst ein vorhandenes `airplane` (AeroSandbox-Airplane-Objekt) und ein Propulsionsmodell.  
> AeroSandbox modelliert Propeller/Motor nicht automatisch für dich – du musst Schub/Leistung selbst abbilden (hier als Platzhalter).

```python
import aerosandbox as asb
import aerosandbox.numpy as np

# --- Inputs (Cruise-Bedingung) ---
V = 25.0          # m/s
h = 200.0         # m
m = 2.5           # kg
g = 9.80665       # m/s^2
W = m * g         # N

# TODO: dein Airplane-Objekt
# airplane = ...

# Simple Propulsion placeholder (ersetzen durch euer Motor/Prop-Modell)
def thrust_N(throttle, V, h):
    T_max = 25.0  # N, Beispiel
    return throttle * T_max

opti = asb.Opti()

# --- Entscheidungsvariablen ---
alpha = opti.variable(init_guess=5 * np.pi/180)      # rad
elev_deg = opti.variable(init_guess=-2.0)            # deg (downwards-positive in ASB)
throttle = opti.variable(init_guess=0.5)             # 0..1

# --- Bounds (realistisch halten) ---
opti.subject_to(alpha >= -5*np.pi/180)
opti.subject_to(alpha <= 15*np.pi/180)
opti.subject_to(elev_deg >= -20)
opti.subject_to(elev_deg <= 20)
opti.subject_to(throttle >= 0)
opti.subject_to(throttle <= 1)

# --- OperatingPoint definieren (steady flight) ---
op = asb.OperatingPoint(
    velocity=V,
    altitude=h,
    alpha=alpha,
    beta=0,
    p=0, q=0, r=0
)

# --- Control-Deflections am Flugzeug anwenden ---
airplane_deflected = airplane.with_control_deflections({
    "elevator": elev_deg,   # Name muss zu deiner ControlSurface-Benennung passen
    # "aileron": 0,
    # "rudder": 0,
})

# --- Aerodynamik rechnen ---
ab = asb.AeroBuildup(airplane=airplane_deflected, op_point=op)
aero = ab.run()  # liefert u.a. L, D, m_b

L = aero["L"]     # Lift [N]
D = aero["D"]     # Drag [N]
m_b = aero["m_b"] # Pitch moment [Nm]

# --- Trim-Constraints ---
opti.subject_to(L == W)
opti.subject_to(m_b == 0)

# Thrust balance (optional, aber für echten Cruise-Trim üblich)
T = thrust_N(throttle, V, h)
opti.subject_to(T == D)

# --- Ziel (z.B. minimaler throttle oder minimaler Drag) ---
opti.minimize(throttle)  # oder: opti.minimize(D)

sol = opti.solve()

print("alpha [deg]:", float(sol(alpha) * 180/np.pi))
print("elevator [deg]:", float(sol(elev_deg)))
print("throttle [-]:", float(sol(throttle)))
print("L [N]:", float(sol(L)), "D [N]:", float(sol(D)))
```

---

## Typische Stolperstellen / Checks

1) **Control-Surface Keys stimmen**
- `"elevator"` muss exakt dem `ControlSurface.name` entsprechen, sonst wirkt die Deflection nicht.

2) **Deflections wirken in deiner Analyse wirklich**
- Je nach Setup/Analysepfad ist ein Integrationstest sinnvoll:
  - gleicher Zustand, einmal `rudder=0`, einmal `rudder=+5°`
  - Erwartung: Kräfte/Momente ändern sich messbar

3) **Konvergenz**
- Gute `init_guess` und realistische Bounds helfen enorm.
- Wenn `T==D` Probleme macht: erst `L==W` und `m_b==0` lösen, dann Schubgleichgewicht ergänzen.

4) **Units**
- Zustände (V, h, alpha) in SI (m/s, m, rad).
- Deflections in AeroSandbox meist in **deg** (einheitlich bleiben oder konsequent konvertieren).

---

## Praktischer Hinweis für euren OP-Workflow
Wenn ihr Operating Points persistent speichert (DB), sollten mindestens folgende Größen erfasst werden:

- Zustand: `V, h, alpha, beta, p, q, r`
- Controls: `elevator, aileron, rudder, throttle` (oder äquivalente Leistungsgröße)
- Status: `TRIMMED / NOT_TRIMMED / ...` + strukturierte `warnings`

Damit ist ein „trimmed operating point“ später reproduzierbar (inkl. Dutch-Roll Startzustand).
