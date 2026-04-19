# Skalierungsfaktor beim Fuselage-Import (#137)

## Problem

Beim Import eines Rumpfes über den ImportFuselageDialog gibt es keinen Skalierungsfaktor. Wenn die STEP-Quelldatei in mm vorliegt und die DB in Metern arbeitet, stimmen die Dimensionen nicht.

## Lösung

Reine Frontend-Änderung in `ImportFuselageDialog.tsx`. Kein Backend-Impact.

### UI

Neues Feld "Scale Factor" im Upload-Bereich, zwischen Fuselage-Name und den Slice-Parametern:

```
Fuselage Name: [Imported Fuselage        ]
Scale Factor:  [0.001                    ]  ← NEU
Slices:        [50  ]   Axis: [auto ▾]
```

Presets als Chips: `mm→m (0.001)` | `cm→m (0.01)` | `1:1`

### Verhalten

1. **State:** `scaleFactor: number` (Default: `1.0`)
2. **Anwendung sofort nach Slice-Response:** Alle `xyz`, `a`, `b` Werte werden mit `scaleFactor` multipliziert bevor sie in den `xsecs` State geschrieben werden
3. **Auch bei "Create manually":** Default-xsecs werden mit scaleFactor skaliert
4. **Preview zeigt skalierte Werte** — der User sieht immer die finalen Dimensionen
5. **Beim Speichern:** Keine weitere Skalierung nötig (schon angewendet)

### Code-Änderungen

Datei: `frontend/components/workbench/ImportFuselageDialog.tsx`

**Neuer State** (nach Zeile 226):
```typescript
const [scaleFactor, setScaleFactor] = useState(1.0);
```

**Skalierung nach Slice-Response** (Zeile 263):
```typescript
const newXsecs: XSec[] = (data.fuselage?.x_secs ?? []).map((xs: any) => ({
  xyz: xs.xyz.map((v: number) => v * scaleFactor),
  a: xs.a * scaleFactor,
  b: xs.b * scaleFactor,
  n: xs.n,
}));
```

**Skalierung bei "Create manually"** (Zeile 332):
```typescript
const defaultXsecs: XSec[] = [
  { xyz: [0, 0, 0], ... },
  ...
].map(xs => ({
  ...xs,
  xyz: xs.xyz.map(v => v * scaleFactor),
  a: xs.a * scaleFactor,
  b: xs.b * scaleFactor,
}));
```

**UI-Rendering** (nach Fuselage Name Input, ca. Zeile 448):
```tsx
<div className="flex flex-col gap-1">
  <label className="text-[11px] text-muted-foreground">Scale Factor</label>
  <div className="flex items-center gap-2">
    <input type="number" value={scaleFactor} step="any"
      onChange={(e) => setScaleFactor(parseFloat(e.target.value) || 1)} ... />
    <button onClick={() => setScaleFactor(0.001)} ...>mm→m</button>
    <button onClick={() => setScaleFactor(0.01)} ...>cm→m</button>
    <button onClick={() => setScaleFactor(1)} ...>1:1</button>
  </div>
</div>
```

## Tests (Vitest, 3 Tests)

1. **Scale factor field renders** — prüft dass Input + Preset-Buttons sichtbar sind
2. **Preset buttons setzen korrekten Wert** — Klick auf "mm→m" setzt 0.001
3. **Scale wird auf xsecs angewendet** — Mock-Slice-Response mit xyz=[1000,0,0], scale=0.001 → xsecs haben xyz=[1,0,0]

## Dateien

| Datei | Aktion |
|-------|--------|
| `frontend/components/workbench/ImportFuselageDialog.tsx` | MODIFY |
| `frontend/__tests__/ImportFuselageScaleFactor.test.tsx` | NEU |
