# Rechenkern — Architektur (arc42, schlank)

> **Status: Entwurf zur Freigabe (#1174).** Nach der Freigabe durch den Maintainer ist dieses Dokument
> die **verbindliche Vorlage** für alle Tickets des Epics #1173 (#1174–#1179). Wer etwas ändert, das hier
> steht, ändert zuerst dieses Dokument.
>
> **Was hier nicht steht:** Inhalt der Formeln (→ Kanon `_reversa_sdd/calculations/canon/`), Entscheidungen
> (→ ADRs und Register K, Kap. 9). Dieses Dokument verlinkt, es wiederholt nicht.

---

## 1. Ziele und Qualitätsziele

**Aufgabe.** Der Rechenkern führt den Rechenkanon aus. Er bekommt die vollständigen Daten eines
Flugzeugs und eine Liste gewünschter Größen. Zurück gibt er Werte, Intervalle, Warnungen und Fehler.
Ob ein Eingabewert angenommen oder gemessen ist, ist ihm gleich. Er rechnet, er bewertet nicht (A10).

**Erster Zweck (Epic #1173).** Belegen, dass der Kanon stabil rechnet, bevor er freigegeben wird.
Später wird er die eine Rechenquelle der App (Register-Epic „Rechenkanon umsetzen“).

| Prio | Qualitätsziel | Woran es gemessen wird (→ Kap. 10) |
|---|---|---|
| 1 | **Widerspruchsfrei erweiterbar.** Ein neuer Kanon-Eintrag ist eine Ergänzung, kein Umbau. | Q1, Q2 |
| 2 | **Nachvollziehbar.** Jeder Wert führt auf Kanon-Eintrag, Anwendung, Werkzeug und Versionen zurück. | Q3 |
| 3 | **Stabil und ehrlich.** Kein stiller Ersatzwert; was nicht rechenbar ist, wird benannt. | Q4, Q5 |
| 4 | **KI-tauglich.** Fehler sind strukturiert, maschinen- und menschenlesbar, mit Handlungshinweis. | Q6 |
| 5 | **Effizient ohne Zustand.** Gleiche Eingaben rechnen nicht zweimal. | Q7 |

## 2. Randbedingungen

Python 3.11–3.12, Poetry; Abhängigkeiten nur numpy, pydantic, aerosandbox, avl-binary. CI-Fast-Tier läuft
**ohne** AeroSandbox/AVL. Einheiten SI. Bindend: ADRs nach Kap. 9.

## 3. Kontext und Abgrenzung

```
         Tests (rechenkern/tests)        Robustheitslauf (tools/robustness.py)
                     \                     /
   Kalibrierung ──── compute(AircraftInput, ComputeRequest) ──→ ComputeResult
   (calibration/)    |   rechenkern/   |
                     └─────────────────┘
          liest: Kanon-Manifest (aus _reversa_sdd/calculations/canon/ erzeugt)
          ruft:  AeroSandbox (AeroBuildup, Opti, Atmosphäre), AVL (Subprozess)
   später:  app/services · Copilot (#902) · MCP — über das Register-Epic, nicht jetzt
```

- **Grenze nach innen:** `rechenkern/` importiert **nie** `app/`, `cad_designer/` oder `scripts/`. Die App
  ruft den Kern, nicht umgekehrt.
- **Keine zweite Quelle (ADR 0022).** Bis das Register-Epic die App umstellt, zeigt die App keine Werte
  aus dem Kern. Der Kern ist trotzdem nicht „inert“ (ADR 0021): Tests, CI-Job, Robustheitslauf und
  Kalibrierung benutzen ihn (Epic #1173).
- **Kein Auslösen, kein Speichern.** Wann gerechnet wird (K28, K29) und wo Ergebnisse liegen (Snapshot),
  entscheidet der Aufrufer. Der Kern liefert dafür den Abhängigkeits-Unterbaum (A1) und die Kostenklasse.

## 4. Lösungsstrategie

1. **Der Kanon ist die Strukturquelle.** Ein Generator erzeugt aus den Kanon-Dateien ein versioniertes
   **Manifest** (Größen, Formeln, Anwendungen, Vorbedingungen, Einheiten, Rollen, Welten, Kostenklasse).
   Der Code meldet nur **Implementierungen** je Formel an. Abhängigkeiten kommen nie aus dem Code.
2. **Der ganze Kanon ist deklariert,** auch was noch nicht implementiert ist (`not_implemented`).
3. **Formel ≠ Anwendung.** Eine Implementierung je Formel; Anwendungen binden Eingaben und tragen eine
   Bedingung (README des Kanons, „One formula, several applications“).
4. **Methodenwelten statt Intervallarithmetik** (A11, ADR 0027): je Welt durch den ganzen Unterbaum, das
   Intervall entsteht erst am Ende.
5. **Zustandslos nach außen, Cache nach innen.** Schlüssel aus Inhalt und Versionen, nie aus Identitäten.
6. **Solver hinter dünnen Adaptern.** Formeln sprechen Adapter an, nie AeroSandbox oder AVL direkt — so
   sind sie im Fast-Tier mockbar und Fähigkeitsfehler entstehen an einer Stelle.

## 5. Bausteinsicht

```
rechenkern/
  api.py            compute()  — einziger öffentlicher Einstieg
  schema.py         AircraftInput, OperatingPoint, ComputeRequest, ComputeResult, QuantityResult,
                    CanonError, Warning, Provenance (Pydantic, extra="forbid")
  manifest/         generate.py  Kanon-.md → manifest.json (Teil des Pakets, versioniert)
                    load.py      laden + Konsistenzregeln (Kap. 8.6)
  graph.py          Unterbaum, Reihenfolge, Welten-Expansion, upstream_failed
  registry.py       @formula(slug) — Implementierungen ↔ Manifest
  formulas/         eine Datei je Kanon-Formel (Dateiname = Slug)
  solvers/          aerobuildup.py · avl.py · opti.py · atmosphere.py · data.py (KAT, APC)
  cache.py          Speicher-LRU, optional Platte
  validate.py       physikalische Zulässigkeit; Regime-Warnungen (ADR 0028)
  errors.py         Fehlerkatalog (Kap. 8.1)
  calibration/      FlightObservation, Vergleich (#1179)
  tools/            robustness.py (#1178)
  tests/            Einheiten-, Eigenschafts-, Gold-, Rückverfolgungs-, Fehlertests
```

| Baustein | Verantwortung | Darf nicht |
|---|---|---|
| `api` | Anfrage annehmen, validieren, Graph abarbeiten, Ergebnis bauen | rechnen |
| `manifest` | Kanonstruktur lesen und prüfen | Formeln kennen |
| `graph` | Abhängigkeiten, Welten, Fehlerfortpflanzung | Werkzeuge aufrufen |
| `formulas/*` | genau eine Kanon-Formel | eine zweite Formel rechnen, Schwellen bewerten (A10) |
| `solvers/*` | Werkzeugaufruf, Versionsangabe, Werkzeugfehler übersetzen | Kanon-Namen kennen |
| `cache` | Ergebnisse zu Schlüsseln | Ergebnisse verändern |

## 6. Laufzeitsicht — ein Aufruf

```
compute(aircraft, request)
 1 validate(aircraft)                      → invalid_input mit input_path, Abbruch nur hier
 2 manifest.subtree(request.quantities)    → Formeln + Anwendungen, topologisch sortiert
 3 je Anwendung: Bedingung prüfen          → nicht anwendbar → status "not_applicable"
 4 je Welt (A11) und je Betriebspunkt:
     Kostenklasse "minutes" ohne Freigabe  → needs_confirmation
     Schlüssel bilden → Cache-Treffer?     → übernehmen
     sonst Implementierung aufrufen (Zeitbudget)
       Erfolg  → Wert + Warnungen (inkl. Regime ADR 0028, Vorbedingungen)
       Fehler  → CanonError; Nachfolger → upstream_failed
 5 Welten zusammenführen → [min, max] mit Weltenliste
 6 ComputeResult mit Provenienz
```

## 7. Verteilung

Bibliothek im selben Repository, kein eigener Prozess. AVL läuft als Subprozess in einem Temp-Verzeichnis.

## 8. Querschnittliche Konzepte

### 8.1 Fehlermodell (KI-tauglich)

Ein Fehler heißt: **kein Wert**. Ein Wert mit Einschränkung ist eine **Warnung** (8.2), kein Fehler.

`CanonError`: `code` · `category` · `retryable` · `escalate` · `quantity` · `formula` · `application` ·
`world` · `input_path` · `message` (Ursache, natürlichsprachlich) · `hint` (was tun) · `detail` (Daten).

| Kategorie | retryable | escalate | Bedeutung | Beispiel-Hinweis |
|---|---|---|---|---|
| `invalid_input` | nein | nein | Eingabe physikalisch unzulässig | „Tiefe an `wings.W.x_secs[2].chord` muss > 0 sein.“ |
| `unsupported_configuration` | nein | nein | Bauart vom Verfahren nicht abgedeckt | „Neutralpunkt-Lehrbuchformel setzt ein Höhenleitwerk voraus.“ |
| `not_applicable` | — | — | **kein Fehler**: Anwendung existiert nicht (keine Klappe → kein V_S,landing) | — |
| `not_implemented` | nein | nein | Kanon-Formel noch ohne Implementierung | „`max-sustained-turn-rate` ist im Kanon, nicht im Kern.“ |
| `not_converged` | ja | nein | Solver ohne Lösung | „Höhere Genauigkeitsstufe oder anderer Startwert.“ |
| `timeout` | ja | nein | Zeitbudget überschritten | „Budget erhöhen oder als lange Rechnung anfordern.“ |
| `tool_unavailable` | nein | ja | Werkzeug fehlt (AeroSandbox, AVL) | „Umgebung mit Aero-Abhängigkeiten nutzen.“ |
| `upstream_failed` | wie Vorgänger | wie Vorgänger | Vorgänger-Größe ohne Wert | „Erst `stall-speed` beheben.“ |
| `needs_confirmation` | ja, mit Freigabe | ja | lange Rechnung (K28) | „Anwender muss die Rechnung anstoßen.“ |
| `internal` | nein | ja | Programmfehler | „Fehler melden; Eingabe und Provenienz beilegen.“ |

`escalate = true` heißt: Ein Agent kann das nicht selbst lösen, ein Mensch muss handeln.

### 8.2 Warnungen

Form wie `DesignWarning` (ADR 0020): `severity` (`practice` | `defect`), `code`, `message`, `quantity`.
Quellen: Regime (ADR 0028: Re-Band 3·10⁴–1·10⁶, „blasenempfindlich“ unter 7·10⁴, Mach), verletzte oder
ungeprüfte Vorbedingungen, aktive Schranken im Optimierer, A11 „nicht validiert“.

### 8.3 Ergebnisvertrag

`QuantityResult`: `slug` · `unit` (SI) · `status` (`ok` | `not_applicable` | `error`) · `value` **oder**
`interval {min, max, worlds{name: value}}` · `tool` · `application` · `validated` (immer `false`, bis
Kalibrierung, #1179) · `warnings[]` · `error`. Keine internen Pfade oder Mechanismen in Feldern (ADR 0019).

### 8.4 Provenienz und Cache-Schlüssel

`Provenance`: Kern-Version, Manifest-Hash (Kanon-Stand), Werkzeugversionen (aerosandbox, NeuralFoil-Modell,
AVL), Genauigkeitsstufe (A3), Solver-Einstellungen.
**Cache-Schlüssel** = Hash(Formel-Slug, Anwendung, Welt, kanonisierte **relevante** Eingaben, Manifest-
Hash des Eintrags, Implementierungs-Version, Werkzeugversionen). Kanonisierung: sortierte Schlüssel, Zahlen
auf feste signifikante Stellen. Ändert sich eine Formel, verfällt nur ihr Unterbaum (A1).

### 8.5 Anwendungen und Vorbedingungen

Anwendung = (Formel, Bindungen der Eingaben, Bedingung, Name der Ausgabegröße). Vorbedingung = ausführbare
Prüfung je Anwendung → 🟢 gehalten · 🔴 verletzt (Warnung `defect` oder Fehler, je Kanon) · ⚪ ungeprüft
(Warnung `practice`).

### 8.6 Konsistenzregeln beim Laden des Manifests

Eine Quelle je Größe, zweiter Weg nur als Probe (A7) · Symbole und Slugs eindeutig (A8) · Zielwerte nur
`role: target` (A9) · Einheiten der Implementierungs-Signaturen = Manifest (A4) · jede Implementierung hat
einen Slug im Manifest · Namensräume getrennt (Rechenkanon, später Auslegungskanon K31). Verstöße sind
**Kanon-Befunde**, keine Laufzeitfehler: der Generator meldet sie, der Kanon wird korrigiert.

### 8.7 Kostenklasse

Je Formel `instant` | `seconds` | `minutes`. `minutes` nur mit `request.allow_long_runs` (K28). Wer die
Klasse festlegt, ist offen (O14, Frage 3); der Kern trägt das Attribut aus dem Manifest.

### 8.8 Werkzeuge und Datenquellen

APP (rein), ATM, GEO, AB, AVL, OPT; Daten KAT (Komponentenkatalog) und APC (Propellertabellen) kommen **vom
Aufrufer** — als Daten im Input oder als Provider mit Inhalts-Hash. Der Kern lädt nichts selbst nach.

## 9. Entscheidungen (nur Verweise)

ADR 0003 (ASB Standard, AVL Ausnahme) · 0019 (keine Interna in der Schnittstelle) · 0020 (eine
Warnungsschiene) · 0021 (nichts Inertes) · 0022 (eine Quelle je Größe) · 0026 (Solver-Widerstand) · 0027
(Intervalle über Welten) · 0028 (Regime über Strömungsphysik) · Register K26 (NP-Welten), K27
(Seitenstabilität aus AVL), K28/K29 (Auslösung), K30 (ISA), K32 (Abriss bis zum ersten C_L-Gipfel) ·
Regeln A1–A11 in `ANFORDERUNGEN.md` §4.

## 10. Qualitätsszenarien (= Testfälle)

| Nr. | Szenario | Test |
|---|---|---|
| Q1 | Neue Kanon-Formel ohne Implementierung | Anfrage liefert `not_implemented` mit Slug; kein Code geändert |
| Q2 | Alle 57 Kanon-Einträge auf das Modell abgebildet | Anhang A vollständig, Manifest lädt ohne Modelländerung |
| Q3 | Jeder Wert rückverfolgbar | Ergebnis enthält Slug, Anwendung, Werkzeug, Manifest-Hash |
| Q4 | Solver konvergiert nicht | `not_converged`, Nachfolger `upstream_failed`, andere Größen rechnen weiter |
| Q5 | Konfiguration ohne Klappe | `stall-speed-landing` ist `not_applicable`, kein Fehler, kein Ersatzwert |
| Q6 | Jede Fehlerkategorie | serialisiert als JSON mit `message` und `hint` |
| Q7 | Zweiter identischer Aufruf | kein Formelaufruf; Ergebnis bitgleich mit und ohne Cache |
| Q8 | Eingabe Masse ≤ 0 | `invalid_input` mit `input_path`; Re < 3·10⁴ nur Warnung |
| Q9 | Grenze zu `app/` | Test: kein Import aus `app/`, `cad_designer/`, `scripts/` |
| Q10 | Ohne AeroSandbox | `tool_unavailable`, kein ImportError |

## 11. Risiken und technische Schulden

| Risiko | Folge | Umgang |
|---|---|---|
| **Kanon nur halb maschinenlesbar.** Eingänge stehen in der Zeile „Produces … from“, Anwendungen nur bei `stall-speed` als Tabelle, strukturierte Vorbedingungen bei 3 von 57 Einträgen. | Manifest kann Anwendungen und Vorbedingungen nicht vollständig ableiten. | **Entscheidung nötig** (siehe unten). |
| Kanon zu 55/57 `draft` | Tests prüfen gegen unfreigegebene Einträge | gewollt (Epic #1173); Goldwerte heißen „Regression“ |
| CI ohne Aero-Abhängigkeiten | Solver-Formeln im Fast-Tier ungetestet | Adapter mocken; Job `rechenkern-aero` (#1177) |
| Solver-Konvergenz (Abriss-Plateau, Schranken) | `not_converged` häufig | Robustheitslauf (#1178), K32-Verfahren |
| Anwendungstabelle in `stall-speed` nutzt alte Register-Namen (`v_stall_clean_mps`) statt Kanon-Slugs | Namen passen nicht zum Manifest | beim Format-Ausbau auf Kanon-Slugs umstellen |

**Offene Entscheidung für den Maintainer — Format des Kanons.** Damit das Manifest Anwendungen und
Vorbedingungen nicht aus Prosa raten muss, braucht jeder Formel-Eintrag maschinenlesbare Felder im
Kopfbereich, z. B. `inputs:`, `applications:` (Name, Bindungen, Bedingung) und `preconditions:` (Prüfung,
Status, Test). Vorschlag: Format einmal erweitern und alle 57 Einträge mechanisch nachziehen (Prosa bleibt),
**bevor** der Generator gebaut wird.

## 12. Glossar

| Begriff | Bedeutung |
|---|---|
| **Größe** | benannte physikalische Größe mit Einheit und Rolle (`input`, `derived`, `output`, `target`) |
| **Formel** | eine Beziehung zwischen Größen; Art (`kind`): law, procedure, optimization, fit, rating |
| **Anwendung** | eine Formel mit gebundenen Eingaben und Bedingung; erzeugt eine benannte Größe |
| **Bindung** | welche Größe an einen Eingang einer Formel gebunden ist |
| **Vorbedingung** | was für die Eingaben gelten muss, damit die Anwendung bedeutet, was sie behauptet |
| **Welt** | ein Verfahren, das für eine unscharfe Größe durch die ganze Kette läuft (A11) |
| **Probe** | ein zweiter Weg zu einer Größe, nur zur Kontrolle (A7) |
| **Manifest** | maschinenlesbare, versionierte Abbildung des Kanons, die der Kern lädt |
| **Kostenklasse** | `instant` / `seconds` / `minutes` |

---

## Anhang A — Abbildung aller 57 Kanon-Formeln

Spalten: Eingänge → Ausgänge aus der „Produces … from“-Zeile; Anwendungen = Zahl der Bindungen (heute nur
bei `stall-speed` als Tabelle, sonst 1 bzw. Zahl der Ausgänge bei `rating`); Vorbedingungen = strukturiert
im Eintrag vorhanden; Kostenklasse = Vorschlag. Erzeugt aus den Kanon-Dateien; der Manifest-Generator
(#1174) ersetzt diese Tabelle durch eine automatisch erzeugte.

| Formel | kind | tool | shape | Ein → Aus | Anwendungen | Vorbedingungen | Welten | Kostenklasse | v1 |
|---|---|---|---|---|---|---|---|---|---|
| `advance-ratio-from-speed` | law | APP | law | 3 → 1 | 1 | – | – | sofort | später |
| `aerobuildup-evaluation` | procedure | AB | law | 4 → 4 | 1 | – | – | Sekunden | Kernkette |
| `aileron-throw-fraction` | procedure | OPT | law | 8 → 2 | 1 | – | A11 | Sekunden | Kernkette |
| `air-density-isa` | law | ATM | law | 1 → 1 | 1 | – | – | sofort | Kernkette |
| `airplane-components` | procedure | KAT | law | 1 → 9 | 1 | – | – | sofort | Probe |
| `airplane-geometry` | procedure | GEO | law | 1 → 4 | 1 | – | – | sofort | Kernkette |
| `aspect-ratio` | law | APP | law | 2 → 1 | 1 | – | – | sofort | Kernkette |
| `battery-mass-from-capacity` | law | APP | law | 2 → 1 | 1 | – | – | sofort | später |
| `best-angle-of-climb` | optimization | OPT | law | 5 → 2 | 1 | – | – | Sekunden | später |
| `best-rate-of-climb` | optimization | OPT | law | 5 → 2 | 1 | – | – | Sekunden | später |
| `butterfly-approach` | optimization | OPT | law | 6 → 4 | 1 | – | – | Sekunden | später |
| `cg-for-target-margin` | law | APP | law | 3 → 1 | 1 | – | – | sofort | Kernkette |
| `cruise-target-performance` | procedure | OPT | law | 7 → 2 | 1 | – | – | Sekunden | später |
| `dive-speed` | procedure | OPT | law | 5 → 1 | 1 | – | – | Sekunden | später |
| `drag-polar` | law | APP | approximation | 3 → 1 | 1 | – | – | sofort | später |
| `dynamic-pressure` | law | APP | law | 2 → 1 | 1 | – | – | sofort | Kernkette |
| `endurance-and-range` | procedure | OPT | law | 8 → 2 | 1 | – | – | Sekunden | später |
| `glide-distance-from-ratio` | law | APP | law | 2 → 1 | 1 | ja | – | sofort | später |
| `induced-drag-factor` | law | APP | law | 2 → 1 | 1 | – | – | sofort | später |
| `inverted-max-lift-coefficient` | procedure | AB | law | 2 → 1 | 1 | ja | – | Sekunden | später |
| `lateral-static-stability-app` | procedure | AVL | law | 6 → 4 | 1 | – | – | Sekunden | Kernkette |
| `lateral-static-stability-md` | procedure | AVL | law | 6 → 4 | 1 | – | – | Sekunden | Kernkette |
| `lift-coefficient-required` | law | APP | law | 5 → 1 | 1 | – | – | sofort | Kernkette |
| `lift-to-drag-ratio` | law | APP | law | 2 → 1 | 1 | – | – | sofort | Kernkette |
| `linear-lift-curve-inverse` | law | APP | law | 3 → 1 | 1 | – | – | sofort | später |
| `maneuvering-speed` | optimization | OPT | law | 5 → 1 | 1 | – | – | Sekunden | später |
| `mass-envelope` | optimization | OPT | law | 6 → 5 | 1 | – | – | Minuten | Kernkette |
| `max-level-speed` | optimization | OPT | law | 5 → 1 | 1 | – | – | Sekunden | Probe |
| `max-lift-to-drag-parabolic` | law | APP | law | 3 → 1 | 1 | – | – | sofort | später |
| `max-mass-structure` | law | APP | law | 2 → 1 | 1 | – | – | sofort | später |
| `max-roll-rate-cruise-target` | procedure | OPT | law | 5 → 1 | 1 | – | A11 | Sekunden | später |
| `max-roll-rate` | procedure | OPT | law | 5 → 2 | 1 | – | A11 | Sekunden | Kernkette |
| `max-sustained-turn-rate` | optimization | OPT | law | 6 → 2 | 1 | – | – | Sekunden | später |
| `mean-geometric-chord` | law | APP | law | 2 → 1 | 1 | – | – | sofort | Kernkette |
| `min-sustained-turn-radius` | optimization | OPT | law | 6 → 2 | 1 | – | – | Sekunden | später |
| `minimum-drag-speed-closed-form` | law | APP | approximation | 4 → 1 | 1 | – | – | sofort | später |
| `minimum-drag-speed-from-polar` | optimization | OPT | route | 5 → 2 | 1 | – | – | Sekunden | Kernkette |
| `minimum-sink-speed-from-polar` | optimization | OPT | law | 5 → 1 | 1 | – | – | Sekunden | Kernkette |
| `motor-propeller-equilibrium` | procedure | APP | route | 9 → 1 | 1 | – | – | sofort | Probe |
| `neutral-point` | procedure | AVL | law | 5 → 1 | 1 | – | A11 | Sekunden | Kernkette |
| `parabolic-polar-fit` | fit | OPT | law | 6 → 2 | 1 | – | – | Sekunden | Probe |
| `propeller-table-lookup` | procedure | APC | law | 2 → 1 | 1 | – | – | sofort | Probe |
| `relative-mass-deviation` | law | APP | law | 2 → 1 | 1 | – | – | sofort | später |
| `sink-rate` | law | APP | law | 3 → 1 | 1 | – | – | sofort | Kernkette |
| `spar-break-load-factor` | procedure | APP | law | 3 → 2 | 1 | – | – | sofort | später |
| `speed-from-stall-margin` | rating | APP | approximation | 2 → 3 | 3 | – | – | sofort | Probe |
| `spiral-parameter` | law | APP | law | 5 → 1 | 1 | – | – | sofort | Kernkette |
| `stall-onset-detection` | procedure | AB | law | 3 → 1 | 1 | – | – | Sekunden | Kernkette |
| `stall-speed` | optimization | OPT | law | 5 → 4 | 3 | ja | – | Sekunden | Kernkette |
| `stall-wing-loading-limit` | law | APP | law | 3 → 1 | 1 | – | – | sofort | später |
| `static-margin-probe` | procedure | AB | law | 6 → 2 | 1 | – | – | Sekunden | Kernkette |
| `static-margin` | law | APP | law | 3 → 1 | 1 | – | – | sofort | Kernkette |
| `static-thrust-to-weight` | law | APP | law | 2 → 1 | 1 | – | – | sofort | später |
| `thrust-at-airspeed-from-coefficient` | law | APP | law | 4 → 1 | 1 | – | – | sofort | später |
| `vertical-tail-volume` | law | APP | law | 1 → 1 | 1 | – | – | sofort | Kernkette |
| `weight-from-mass` | law | APP | law | 2 → 1 | 1 | – | – | sofort | Kernkette |
| `wing-loading` | law | APP | law | 3 → 1 | 1 | – | – | sofort | Kernkette |

*57 Einträge; Kernkette 26, Proben 6, später 25.*

**Befund aus der Abbildung:** Alle 57 Einträge passen auf das Modell (fünf `kind`s, acht Werkzeuge, drei
`shape`s, Welten, Kostenklassen). Was fehlt, ist kein Konzept, sondern **Maschinenlesbarkeit** im Kanon
(Kap. 11).
