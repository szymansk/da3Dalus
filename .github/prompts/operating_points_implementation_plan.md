# Operating Points Implementation Plan (Repo-specific)

## Ziel
Implementiere einen Generator für aircraft-spezifische Operating-Point-Sets auf Basis vorhandener Flight Profiles.

## Bereits umgesetzt
- Flight Profile CRUD + Aircraft Assignment
- Migrationen für `rc_flight_profiles` und `aeroplanes.flight_profile_id`

## Implementierungsschwerpunkte
1. Erweiterung der OP-DB-Modelle um:
   - `aircraft_id`, `config`, `status`, `warnings`, `controls`
   - Set-Felder `aircraft_id`, `source_flight_profile_id`
2. Neuer Service `operating_point_generator_service`:
   - lädt Aircraft + Flight Profile
   - erzeugt 11 Standardpunkte inkl. `dutch_role_start`
   - verwendet MVP-Heuristik für Trim-Schätzung
   - persistiert Set + Punkte atomar
3. API-Erweiterung:
   - `POST /aircraft/{aircraft_id}/operating-pointsets/generate-default`
   - list/filter Endpunkte für `operating_points` und `operating_pointsets` nach `aircraft_id`
4. Alembic-Migration für neue OP-/Set-Spalten und FKs
5. Tests:
   - Generator-Service
   - Generator-API
   - Migration

## Offene Grenzen (MVP)
- Kein vollwertiger Control-Trim-Solver, nur Zustandsschätzung
- `controls` wird vorbereitet, aber in MVP leer bzw. minimal befüllt
