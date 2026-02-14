# Operating Point Generator: Testfälle und Grenzwerte

## Ziel
Dieses Dokument beschreibt:
- welche Testfälle aktuell im Projekt abgedeckt sind,
- warum diese Testfälle wichtig sind,
- welche Grenzen (Boundary Conditions) explizit getestet werden sollen.

Scope: Operating-Point-Set-Generierung, Capability-Validierung, API-Verhalten, Persistenz.

## Bestehende automatisierte Testfälle

## Service-Tests
Datei: `app/tests/test_operating_point_generator_service.py`

1. `test_generate_default_set_with_profile_assignment`
- Prüft: zugewiesenes Flight Profile wird verwendet.
- Erwartung: `source_flight_profile_id` gesetzt, 11 Operating Points erzeugt, `dutch_role_start` enthalten.

2. `test_generate_default_set_without_profile_uses_defaults`
- Prüft: Fallback auf Default-Profile ohne Aircraft-Zuweisung.
- Erwartung: `source_flight_profile_id is None`, 11 Punkte erzeugt.

3. `test_generate_replace_existing_replaces_old_rows`
- Prüft: `replace_existing=True` ersetzt alte Datensätze.
- Erwartung: nach zwei Läufen weiterhin konsistente Anzahl (11) für das Aircraft.

4. `test_generate_skips_points_when_required_controls_missing`
- Prüft: Capability-Skip bei fehlenden Controls.
- Erwartung: `turn_n2` und `dutch_role_start` fehlen, nur 9 Punkte, Warning-Logs + Summary-Log korrekt.

5. `test_generate_with_rudder_keeps_dutch_role_point`
- Prüft: Rudder reicht für Dutch-Role-Start.
- Erwartung: `dutch_role_start` enthalten, 11 Punkte.

6. `test_generate_replace_existing_with_skips_keeps_consistent_rows`
- Prüft: Kombination aus Skip + Replace.
- Erwartung: konsistente Persistenz mit reduzierter Punktzahl (9).

## API-Tests
Datei: `app/tests/test_operating_point_generator_api.py`

1. `test_generate_default_endpoint_returns_generated_set`
- Prüft: Endpoint-Response-Schema bei erfolgreicher Generierung.
- Erwartung: HTTP 200, Operating Point Set im erwarteten Format.

2. `test_generate_default_endpoint_handles_skipped_points_response`
- Prüft: API bleibt stabil, wenn Generator weniger/keine Punkte zurückliefert.
- Erwartung: HTTP 200, leere `operating_points` ist erlaubt.

3. `test_operating_points_filter_by_aircraft_id`
- Prüft: Aircraft-spezifischer Filter für OP-Listing.
- Erwartung: nur OPs des angefragten Aircrafts.

## Migrations-Test
Datei: `app/tests/test_operating_point_migrations.py`

1. `test_operating_point_generation_migration_columns_exist`
- Prüft: Schema-Erweiterungen vorhanden.
- Erwartung: neue Spalten/FKs für `operating_points` und `operating_pointsets` existieren.

## Zu testende Grenzen (Boundary Conditions)

## Fachliche Grenzen
1. Vollständiges Set vs. reduziertes Set
- Vollständig: 11 Punkte.
- Reduziert: bei fehlenden Controls mindestens 9 (aktuelle Regelmatrix).
- Erwartung: Pipeline bricht nicht ab.

2. Capability-Regeln
- `turn_n2`: benötigt `has_roll_control` oder `has_yaw_control`.
- `dutch_role_start`: benötigt `has_yaw_control`.
- Erwartung: bei Verletzung Skip + strukturierte Warning.

3. Profile-Fallback
- Mit zugewiesenem Profil: Profilwerte müssen genutzt werden.
- Ohne Profil: Defaultwerte müssen deterministisch greifen.

## Numerische Grenzen im Trimming
1. Opti-Bounds
- `alpha_deg` im Solver: `[-8, max_alpha_deg]` (Default `max_alpha_deg=25`).
- Erwartung: Lösung bleibt innerhalb Bounds oder fällt zurück.

2. Grid-Fallback-Bounds
- `alpha_deg`-Kandidaten: `[-4, 20]` (diskret).
- Geschwindigkeit: OP-abhängige Fallback-Faktoren, Mindestgeschwindigkeit `>= 2.0 m/s`.
- Erwartung: immer robustes Ergebnisobjekt, auch bei Nicht-Konvergenz.

3. Trim-Status-Schwelle
- `TRIMMED` falls Score `< 0.35`, sonst `NOT_TRIMMED`.
- Erwartung: deterministische Statuszuordnung.

4. Limit-Status
- Bei `abs(alpha) > max_alpha_deg` oder `abs(beta) > max_beta_deg` -> `LIMIT_REACHED`.
- Erwartung: Warnflags (`ALPHA_LIMIT_REACHED`, `BETA_LIMIT_REACHED`) gesetzt.

## Persistenz- und API-Grenzen
1. `replace_existing=True`
- Erwartung: alte OP/Set-Daten des Aircraft werden ersetzt, keine Duplikat-Akkumulation.

2. Leeres Ergebnis (alle Punkte geskippt)
- Erwartung: Set-Erzeugung bleibt technisch gültig; API antwortet weiterhin 200.

3. API-Parametergrenzen
- `skip >= 0`
- `1 <= limit <= 1000`
- Erwartung: FastAPI-Validierung schlägt bei ungültigen Werten an.

## Zusätzliche empfohlene Tests (noch nicht vollständig abgedeckt)
1. Opti-spezifische Assertions
- Prüfen, dass `controls` bei erfolgreichem Opti-Trim nicht leer sind (wo Controls verfügbar).

2. Grenzwerttest `max_alpha_deg`/`max_beta_deg`
- Profile mit sehr engen Grenzen testen, um `LIMIT_REACHED` deterministisch auszulösen.

3. Fehlende Aircraft-/Profile-Referenzen
- `NotFoundError`-Pfad für unbekanntes Aircraft oder `profile_id_override`.

4. Realistische Integrationsläufe
- End-to-End mit realer Geometrie (z. B. Cessna-Beispiel), inklusive Laufzeitbeobachtung und Ergebnisstabilität.

## Testausführung
Beispiel:

```bash
poetry run pytest app/tests/test_operating_point_generator_service.py app/tests/test_operating_point_generator_api.py app/tests/test_operating_point_migrations.py -q
```

## Abnahmekriterien
1. Kein ungefangener Fehler bei fehlenden Controls oder fehlendem Flight Profile.
2. API bleibt kompatibel (HTTP 200, stabiles Response-Schema).
3. Persistenz bleibt aircraft-spezifisch und konsistent bei `replace_existing`.
4. Numerische Grenzen führen zu erwarteten Status/Warnungen statt Pipeline-Abbruch.
