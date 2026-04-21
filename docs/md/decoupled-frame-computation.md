# Entkoppelte Frame-Berechnung: Incidence aus der Positionspropagation entfernen

## Aktuell (gekoppelt, nach Fix 1 mit rc=0)

Jedes Segment-H enthält sowohl Dihedral ($\mathbf{R}_x$) als auch Incidence ($\mathbf{R}_y$):

$$
\mathbf{H}_{\text{root}} = \mathbf{T}(\text{nose\_pnt}) \cdot \mathbf{R}_x(\gamma_{\text{root}}) \cdot \mathbf{R}_y(\theta_{\text{root}})
$$

$$
\mathbf{H}_{\text{seg},k} = \mathbf{T}(s_k,\; l_k,\; 0) \cdot \mathbf{R}_x(\gamma^{\text{tip}}_k) \cdot \mathbf{R}_y(\theta^{\text{tip}}_k)
$$

$$
\mathbf{H}_i = \mathbf{H}_{\text{root}} \cdot \prod_{k=0}^{i-1} \mathbf{H}_{\text{seg},k}
$$

**Problem:** $\mathbf{R}_y(\theta)$ steckt in jedem $\mathbf{H}_{\text{seg}}$ → Incidence rotiert die Translationsvektoren
aller nachfolgenden Segmente mit → Interleaving-Fehler bei Multi-Segment-Flügeln.

---

## Entkoppelt (vorgeschlagen)

**Kernidee:** $\mathbf{R}_y(\theta)$ aus der Kette herausnehmen und nur einmal am Ende anwenden.

### Schritt 1: Geometrische Kette (nur Dihedral + Translation)

$$
\mathbf{H}^{\text{geom}}_{\text{root}} = \mathbf{T}(\text{nose\_pnt}) \cdot \mathbf{R}_x(\gamma_{\text{root}})
$$

$$
\mathbf{H}^{\text{geom}}_{\text{seg},k} = \mathbf{T}(s_k,\; l_k,\; 0) \cdot \mathbf{R}_x(\gamma^{\text{tip}}_k)
$$

Kein $\mathbf{R}_y$ mehr in den Segment-Matrizen!

Akkumuliert:

$$
\mathbf{H}^{\text{geom}}_i = \mathbf{H}^{\text{geom}}_{\text{root}} \cdot \prod_{k=0}^{i-1} \mathbf{H}^{\text{geom}}_{\text{seg},k}
$$

### Schritt 2: Twist am Ende draufmultiplizieren

$$
\mathbf{H}_i = \mathbf{H}^{\text{geom}}_i \cdot \mathbf{R}_y(\Theta_i)
$$

wobei $\Theta_i$ der kumulierte Twist ist:

$$
\Theta_i = \theta_{\text{root}} + \sum_{k=0}^{i-1} \theta^{\text{tip}}_k
$$

---

## Warum das funktioniert

$\mathbf{H}^{\text{geom}}$ enthält nur $\mathbf{T}$ (Translationen) und $\mathbf{R}_x$ (Dihedral-Rotationen).

Alle $\mathbf{R}_x$ drehen um dieselbe Achse (X) und **kommutieren** daher:

$$
\mathbf{R}_x(\gamma_{\text{root}}) \cdot \mathbf{R}_x(\gamma^{\text{tip}}_0) \cdot \mathbf{R}_x(\gamma^{\text{tip}}_1) = \mathbf{R}_x\!\left(\gamma_{\text{root}} + \gamma^{\text{tip}}_0 + \gamma^{\text{tip}}_1\right) = \mathbf{R}_x(\Gamma_i)
$$

Damit vereinfacht sich $\mathbf{H}^{\text{geom}}_i$ zu:

$$
\mathbf{H}^{\text{geom}}_i = \begin{bmatrix} \mathbf{R}_x(\Gamma_i) & \text{xyz\_le}_i \\ \mathbf{0}^T & 1 \end{bmatrix}
$$

Und der vollständige Frame:

$$
\mathbf{H}_i = \begin{bmatrix} \mathbf{R}_x(\Gamma_i) \cdot \mathbf{R}_y(\Theta_i) & \text{xyz\_le}_i \\ \mathbf{0}^T & 1 \end{bmatrix}
$$

Das ist **exakt** das ASB-Frame: $\mathbf{R}_x(\alpha) \cdot \mathbf{R}_y(\text{twist})$ mit $\alpha = \Gamma_i$.

---

## Positions-Berechnung (explizit)

$$
\text{xyz\_le}_0 = \text{nose\_pnt}
$$

$$
\text{xyz\_le}_{i+1} = \text{xyz\_le}_i + \mathbf{R}_x(\Gamma_i) \cdot \begin{bmatrix} s_i \\ l_i \\ 0 \end{bmatrix}
$$

Ausgeschrieben:

$$
\text{xyz\_le}_{i+1} = \text{xyz\_le}_i + \begin{bmatrix} s_i \\ l_i \cos\Gamma_i \\ l_i \sin\Gamma_i \end{bmatrix}
$$

**Incidence ($\theta$) taucht hier nicht auf.** Nur Dihedral beeinflusst die Position.

---

## Vergleich auf einen Blick

| Aspekt | Gekoppelt | Entkoppelt |
|---|---|---|
| $\mathbf{H}_{\text{seg}}$ | $\mathbf{T}(s,l,0) \cdot \mathbf{R}_x(\gamma) \cdot \mathbf{R}_y(\theta)$ | $\mathbf{T}(s,l,0) \cdot \mathbf{R}_x(\gamma)$ |
| $\mathbf{H}_i$ | Produkt aller $\mathbf{H}_{\text{seg}}$ (interleaved) | $\mathbf{H}^{\text{geom}}_i \cdot \mathbf{R}_y(\Sigma\theta)$ |
| $\mathbf{R}_y(\theta)$ in der Kette? | Ja, propagiert in alle Folgesegmente | Nein, nur lokal am Ende |
| Position von xsec $i$ | Hängt von allen $\gamma$ UND $\theta$ ab | Hängt nur von $\gamma$, $s$, $l$ ab |
| $= $ ASB Frame? | Nein (Interleaving-Fehler) | **Ja, exakt** |

---

## Code-Änderung (Pseudocode)

### Vorher (gekoppelt)

```python
# In _get_relative_segment_coordinate_system():
for seg in reversed(range(segment)):
    H_i = T(s, l, 0) @ R_x(γ_tip) @ R_y(θ_tip) @ H_i

H = T(nose) @ R_x(γ_root) @ R_y(θ_root) @ H_i
```

### Nachher (entkoppelt)

```python
# In _get_relative_segment_coordinate_system():
Gamma = gamma_root
Theta = theta_root

for seg in range(segment):
    # Position: nur Dihedral propagiert
    xyz_le += R_x(Gamma) @ [s, l, 0]
    # Akkumuliere Winkel
    Gamma += gamma_tip[seg]
    Theta += theta_tip[seg]

# Frame: Dihedral-Kette + Twist am Ende
R = R_x(Gamma) @ R_y(Theta)
H = assemble(R, xyz_le)
```

---

## Zusammenfassung

Die Änderung ist konzeptionell einfach:

1. **Entferne $\mathbf{R}_y(\theta)$** aus jedem Segment-Transform
2. **Sammle $\sum\theta$ auf** (einfache Addition)
3. **Multipliziere $\mathbf{R}_y(\sum\theta)$ einmal am Ende** auf den Frame

Das Ergebnis ist ein Frame, der **exakt** dem ASB-Frame entspricht — für jede Geometrie,
jeden Sweep, jedes Dihedral, jede Incidence.

---

## Bidirektionale Konvertierung: WC ↔ ASB

Die Entkopplung macht die Transformation in **beide Richtungen** exakt und verlustfrei.

### WC → ASB (`asb_wing`)

Direkt aus dem Frame ablesbar:

$$
\text{xyz\_le}_i = \text{Translation von } \mathbf{H}_i
$$

$$
\text{twist}_i = \Theta_i = \theta_{\text{root}} + \sum_{k=0}^{i-1} \theta^{\text{tip}}_k
$$

$$
\text{chord}_i = c_i
$$

Der Frame ist identisch zu ASB — nichts zu berechnen.

### ASB → WC (`from_asb`)

Gegeben: $\text{xyz\_le}[i]$, $\text{twist}[i]$, $\text{chord}[i]$ für alle xsecs.

#### Differenzvektor

$$
\boldsymbol{\Delta}_i = \text{xyz\_le}[i+1] - \text{xyz\_le}[i]
$$

#### Sweep (direkt, kein M nötig)

Da $\mathbf{R}_x$ die X-Komponente nicht verändert:

$$
s_i = \Delta_{i,x}
$$

#### Length

$$
l_i = \sqrt{\Delta_{i,y}^2 + \Delta_{i,z}^2}
$$

#### Kumulierter Dihedral (IMMER extrahierbar)

$$
\Gamma_i = \arctan\!\left(\frac{\Delta_{i,z}}{\Delta_{i,y}}\right)
$$

#### Per-Segment Dihedral

$$
\gamma_i = \Gamma_i - \Gamma_{i-1}
$$

#### Per-Segment Incidence

$$
\theta_i = \text{twist}[i] - \text{twist}[i-1]
$$

### Warum das IMMER funktioniert

Im **aktuellen** (gekoppelten) Schema kontaminiert $\mathbf{R}_y(\theta)$ die Z-Komponente:

$$
\Delta_z^{\text{aktuell}} = l \sin\Gamma - s \sin\theta \cos\Gamma + \ldots
$$

Der $s \sin\theta$-Term macht die Dihedral-Extraktion unmöglich wenn $\theta \neq 0$.

Im **entkoppelten** Schema gibt es keinen $\theta$-Term in der Position:

$$
\Delta_z^{\text{entkoppelt}} = l \sin\Gamma
$$

Der `atan2` gibt **immer** den reinen Dihedral-Winkel zurück — unabhängig vom Twist.

### Vergleich: aktuelle vs. entkoppelte `from_asb()`

| Aspekt | Aktuell | Entkoppelt |
|---|---|---|
| **Sweep** | $s = (\mathbf{M}^{-1} \cdot \boldsymbol{\Delta})_x$ — braucht akkumulierte Matrix $\mathbf{M}$ | $s = \Delta_x$ — direkt |
| **Length** | $l = (\mathbf{M}^{-1} \cdot \boldsymbol{\Delta})_y$ — M-abhängig | $l = \sqrt{\Delta_y^2 + \Delta_z^2}$ — direkt |
| **Dihedral** | Nur bei $\theta^{\text{tip}} \approx 0$, sonst Fallback auf Translation | **Immer** via $\arctan(\Delta_z / \Delta_y)$ |
| **`dihedral_as_translation`** | Fallback wenn Twist $\neq 0$ | **Nicht mehr nötig** |
| **M-Matrix Tracking** | Ja, iterativ aufgebaut | **Entfällt komplett** |
| **Roundtrip** | Positionen exakt, Parameter können driften | **Positionen UND Parameter exakt** |

### Fazit

Mit der Entkopplung sind WC und ASB **vollständig äquivalent und verlustfrei
hin- und her-transformierbar**:

- Kein Fallback auf `dihedral_as_translation`
- Keine M-Matrix
- Keine Ambiguität
- `from_asb()` wird trivial (5 Zeilen Arithmetik pro Segment)
