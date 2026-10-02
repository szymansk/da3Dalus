> ⚠ **Profile vorläufig (02.10.2026):** aus unbearbeiteten Laserteilen gefittet — siehe `BEFUNDE_PROFIL.md`. Nicht für aerodynamische Rechnungen verwenden.

# SNACK - befuelltes Datenmodell (Geometrieformat AIRPLANE-GEOMETRY)

Stand 02.10.2026. Quelle: `SNACK_Gesamtmodell.step` + FlugModell-Bauplan SNACK (Konstruktion Hilmar Lange).

| Datei | Inhalt |
|---|---|
| `snack.airplane.json` | **Das Datenmodell**: Masse 0,250 kg und Schwerpunkt laut Plan, Tragflaeche (Holm, Querruder), Hoehen- und Seitenleitwerk, Rumpf und Haube |
| `snack_fluegel_*.dat`, `snack_hlw_*.dat`, `snack_slw_*.dat` | Profil je Station (absolute Dicke, deshalb je Station eine Datei) |
| `snack.zusatz.json` | Plan-Daten ausserhalb des Formats: Antrieb, Steller, Akku, Servos, Empfaenger, Ruderausschlaege, Schwerpunkt, Materialbedarf |
| `teile.json` | 84 Koerper: Dicke, Volumen, Huellmass, Material (Annahme) |
| `fit_bericht.md` | Messweg und Abweichung je Station, Annahmen |
| `bilder/` | 3-Seiten-Vergleich STEP gegen Datenmodell, Rumpf-/Haubenschnitte, Fluegelprofile, Planseite 1 |
| `skripte/` | Erzeugung (lesen.py, geo.py, snack_format.py, snack_bericht.py), Pruefung (format_pruefen.py) |
| `format/` | Formatbeschreibung und Schema |

Pruefung: Schema Draft 2020-12 + F-01..F-07: 0 Fehler, 0 Warnungen.
