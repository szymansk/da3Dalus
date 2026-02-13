Rolle
Du bist ein Backend-Engineer-Agent. Du implementierst ein “RC Flight Profile (Intent)” Feature (siehe unten) als persistenten Datentyp inklusive Datenbankmodell, Pydantic-v2-Schema, REST CRUD Endpoints, Validierung, Fehlerbehandlung, Tests (pytest) und Alembic-Migrationen. Ziel: Ein Anfänger versteht anhand der Beschreibungen, wie die Felder auszufüllen sind. Ein Aircraft (Flugzeug) kann nach Erstellung einem Profil zugewiesen werden.

Kontext / Zielobjekt (RC Flight Profile – Intent)
Ein RC Flight Profile beschreibt NICHT eine Trajektorie, sondern gewünschte Flugeigenschaften und Randbedingungen, um daraus automatisch Operating Points/Design-Ziele ableiten zu können.

Das Profil-JSON (fachlich) orientiert sich an:

{
  "name": "rc_trainer_balanced",
  "type": "trainer",
  "environment": { "altitude_m": 0, "wind_mps": 0 },
  "goals": {
    "cruise_speed_mps": 18,
    "max_level_speed_mps": 28,
    "min_speed_margin_vs_clean": 1.20,
    "takeoff_speed_margin_vs_to": 1.25,
    "approach_speed_margin_vs_ldg": 1.30,
    "target_turn_n": 2.0,
    "loiter_minutes": 8
  },
  "handling": {
    "stability_preference": "stable",
    "roll_rate_target_dps": 120,
    "pitch_response": "smooth",
    "yaw_coupling_tolerance": "low"
  },
  "constraints": {
    "max_bank_deg": 60,
    "max_alpha_deg": 14,
    "max_beta_deg": 8
  }
}

Technologieannahmen
- Python API (z.B. FastAPI)
- Pydantic v2 für Request/Response-Modelle und Validierung
- ORM (z.B. SQLAlchemy) + Alembic Migrationen
- pytest für Tests
Wenn das bestehende Projekt andere Libraries nutzt, passe die Implementierung konsistent an, aber erfülle alle Anforderungen.

Aufgabenpaket A: Daten-Schema + Datenbankmodell
1) Erstelle DB-Modelle:
   - rc_flight_profiles:
     - id (UUID oder int, primärschlüssel)
     - name (string, unique, required)
     - type (string/enum, required)  # trainer, warbird, fpv_cruiser, 3d, glider, motor_glider, custom
     - environment (jsonb, required)
     - goals (jsonb, required)
     - handling (jsonb, required)
     - constraints (jsonb, required)
     - created_at, updated_at
   - aircraft (existiert wahrscheinlich): erweitere um flight_profile_id (nullable FK -> rc_flight_profiles.id)
     - Ein Flugzeug hat 0..1 Profile (zugewiesen oder nicht)
     - Ein Profil kann 0..N Flugzeugen zugewiesen sein

2) Alembic:
   - Erzeuge Migration(en), die:
     - Tabelle rc_flight_profiles anlegt
     - aircraft um flight_profile_id erweitert, FK anlegt und indexiert
     - Unique-Constraint auf rc_flight_profiles.name
   - Rückwärtsmigration (downgrade) implementieren.

3) Dokumentation in Code:
   - Schreibe Docstrings/Kommentare direkt an Model- und Schema-Feldern in einfacher Sprache.

Aufgabenpaket B: Pydantic v2 Schemas + Validierung
Implementiere Pydantic v2 Modelle für:
- RCFlightProfileCreate (Request)
- RCFlightProfileUpdate (PATCH Request, alle Felder optional)
- RCFlightProfileRead (Response)
- Embedded Submodels:
  - Environment
  - Goals
  - Handling
  - Constraints

Validation-Regeln (Pydantic v2)
Nutze field validators / model validators und klare Fehlermeldungen. Mindestanforderungen:

Allgemein:
- name:
  - required bei Create, 3..64 Zeichen
  - erlaubt: a-zA-Z0-9 _ - und Leerzeichen; trimmen; keine führenden/folgenden Leerzeichen
- type:
  - enum: ["trainer","warbird","fpv_cruiser","3d","glider","motor_glider","custom"]

Environment:
- altitude_m:
  - float, default 0
  - erlaubter Bereich: -100 .. 6000 (RC realistisch)
- wind_mps:
  - float, default 0
  - Bereich: 0 .. 25

Goals:
- cruise_speed_mps:
  - float, required, > 0
- max_level_speed_mps:
  - float, optional; falls gesetzt: > cruise_speed_mps
- min_speed_margin_vs_clean:
  - float, default 1.20; Bereich 1.05 .. 1.60
- takeoff_speed_margin_vs_to:
  - float, default 1.25; Bereich 1.05 .. 1.80
- approach_speed_margin_vs_ldg:
  - float, default 1.30; Bereich 1.10 .. 2.00
- target_turn_n:
  - float, default 2.0; Bereich 1.0 .. 4.0
- loiter_minutes:
  - int, optional; falls gesetzt: 0 .. 180

Handling:
- stability_preference:
  - enum ["stable","neutral","agile"]
- roll_rate_target_dps:
  - int, optional; falls gesetzt: 10 .. 600
- pitch_response:
  - enum ["smooth","balanced","snappy"]
- yaw_coupling_tolerance:
  - enum ["low","medium","high"]

Constraints:
- max_bank_deg:
  - int, default 60; Bereich 0 .. 85
- max_alpha_deg:
  - int, optional; falls gesetzt: 0 .. 25
- max_beta_deg:
  - int, optional; falls gesetzt: 0 .. 30

Cross-field validations (model validators):
- Wenn max_level_speed_mps gesetzt ist: max_level_speed_mps > cruise_speed_mps, sonst ValidationError mit verständlicher Meldung.
- target_turn_n muss zur max_bank_deg passen, sofern beide gesetzt:
  - n = 1/cos(phi). Verwende phi = max_bank_deg in rad.
  - Validierung: target_turn_n <= 1/cos(phi) + 0.05 (Toleranz), sonst Fehlermeldung:
    “target_turn_n ist größer als das, was mit max_bank_deg erreichbar ist. Erhöhe max_bank_deg oder senke target_turn_n.”
- Optional: Wenn stability_preference="agile" und roll_rate_target_dps fehlt, setze default (z.B. 240) ODER gebe Hinweis im description (entscheidungsfrei, aber konsistent).

Response-Serialisierung:
- Gib Werte normiert zurück (z.B. floats als float, ints als int).
- Keine zusätzlichen Felder.

Aufgabenpaket C: REST API Endpoints (CRUD + Assignment)
Implementiere folgende Endpoints inkl. OpenAPI descriptions, die für Anfänger verständlich sind (verwende diese Beschreibungen direkt als docstrings/description):

Profiles:
1) POST /flight-profiles
   - Erstellt ein neues RC Flight Profile.
   - Fehler:
     - 409 wenn name bereits existiert
     - 422 bei Validierungsfehlern
   - Response: RCFlightProfileRead

2) GET /flight-profiles
   - Listet alle Profile, optional filter by type, optional pagination.

3) GET /flight-profiles/{profile_id}
   - Gibt ein Profil zurück.
   - 404 wenn nicht gefunden.

4) PATCH /flight-profiles/{profile_id}
   - Teil-Update eines Profils.
   - Nur übergebene Felder ändern.
   - Validierung wie oben, 422 bei Fehlern.
   - 404 wenn nicht gefunden.
   - 409 wenn name auf bestehenden Namen geändert würde.

5) DELETE /flight-profiles/{profile_id}
   - Löscht ein Profil.
   - Verhalten bei zugewiesenen Flugzeugen:
     - Entscheide eindeutig und implementiere:
       Option A (empfohlen): 409 Conflict, solange Profile noch an Aircraft gebunden sind.
       Oder Option B: Setze flight_profile_id bei Aircraft auf NULL (detach) und lösche.
     - Implementiere eine Option und dokumentiere die Entscheidung in der Endpoint-Description.

Assignment:
6) PUT /aircraft/{aircraft_id}/flight-profile/{profile_id}
   - Weist einem Aircraft ein Profil zu (überschreibt bestehende Zuweisung).
   - 404 falls aircraft_id oder profile_id nicht existiert.
   - Response: AircraftRead (oder minimales DTO mit flight_profile_id)

7) DELETE /aircraft/{aircraft_id}/flight-profile
   - Entfernt die Profilzuweisung (setzt flight_profile_id = NULL).
   - 404 falls Aircraft nicht existiert.

Hinweis: Wenn es bereits Aircraft-Endpunkte gibt, integriere die Zuweisung konsistent (z.B. als Subresource).

Aufgabenpaket D: Fehlerbehandlung (Exception Handling)
Implementiere ein konsistentes Exception-Konzept:

- Domain/Service Exceptions:
  - NotFoundError(entity, id)
  - ConflictError(message)  # z.B. duplicate name, delete with assignments
  - ValidationDomainError(message) optional, falls außerhalb Pydantic

- Mappings auf HTTP:
  - NotFoundError -> 404
  - ConflictError -> 409
  - Pydantic ValidationError -> 422 (Standard)
  - Datenbank-IntegrityError (unique constraint) -> 409 mit freundlicher Meldung (“name existiert bereits”)

- Logging:
  - Logge serverseitig stack traces nur für 5xx.
  - Für 4xx logge kurz (entity, id, reason).
- Error Response Format:
  - Nutze ein einheitliches JSON-Format:
    { "error": { "code": "...", "message": "...", "details": ... } }
  - “details” optional, z.B. field errors.

Aufgabenpaket E: Tests (pytest)
Schreibe Tests auf drei Ebenen, mindestens:

1) Schema-Tests (pure Pydantic):
   - gültiges Minimalprofil akzeptiert
   - ungültige Bereiche (z.B. wind_mps negativ) -> ValidationError
   - Cross-field: max_level_speed_mps <= cruise_speed_mps -> ValidationError
   - Cross-field: target_turn_n vs max_bank_deg -> ValidationError

2) API-Tests (FastAPI TestClient):
   - POST create -> 201 + korrektes Response-Schema
   - POST duplicate name -> 409
   - GET list -> 200
   - PATCH rename to existing -> 409
   - DELETE behavior bei zugewiesenen aircraft (je nach gewählter Policy)

3) DB/Integration:
   - Migration läuft (alembic upgrade head) und Tabellen/Spalten existieren
   - Assignment:
     - PUT assign -> aircraft.flight_profile_id gesetzt
     - DELETE detach -> NULL

Testdaten:
- Nutze Fixtures für DB Session (z.B. SQLite in memory oder Testcontainer, je nach Projektstandard).
- Nutze Factory/Builder-Funktionen, um ein “valid profile payload” schnell zu erzeugen.
- Tests müssen deterministisch sein und unabhängig voneinander laufen.

Definitionen/Descriptions (für Anfänger)
In jeder Pydantic Field description und in jeder Endpoint description erkläre kurz:
- Was bedeutet das Feld?
- In welcher Einheit?
- Typische Werte (1–2 Beispiele)
- Welche Folgen hat es für die Berechnungen? (z.B. “cruise_speed_mps wird als Zielgeschwindigkeit für den Cruise-Operating-Point verwendet.”)

Akzeptanzkriterien
- CRUD vollständig implementiert
- Profile können Aircraft zugewiesen/entfernt werden
- Validierungen greifen mit verständlichen Fehlermeldungen
- 409/404/422 korrekt
- Alembic Migration vorhanden und getestet
- pytest Suite deckt Kernpfade ab

Lieferumfang
- Neue Modelle + Schemas + Router/Controller + Service Layer
- Alembic Migration
- pytest Tests
- Kurze README-Sektion (optional), wie man ein Profil anlegt und einem Aircraft zuweist.
Gib am Ende einen kompakten Überblick über die Dateien/Module, die du angelegt/geändert hast.