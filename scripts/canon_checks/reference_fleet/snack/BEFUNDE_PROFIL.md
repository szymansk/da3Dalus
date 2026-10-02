# SNACK — Befunde zum Profil-Fit (02.10.2026)

**Ursache (Maintainer):** `SNACK_Gesamtmodell.step` ist aus den **unbearbeiteten Laserteilen**
aufgebaut. Der Fit misst deshalb Rohteile, nicht die geschliffene Kontur des fertigen
Flügels. Beim Bryan war das anders: dessen Profil stammt aus „Rippe 24.a + Nasenleiste 25
fertig“ — dort war der Schritt Laserteil → fertige Kontur schon getan.

**Bis zur Korrektur gelten die Profile `snack_fluegel_*.dat` als vorläufig** und sollen für
keine aerodynamische Rechnung verwendet werden. Geometrie (Grundriss, V-Form, Holm, Ruder,
Rumpf, Leitwerke) ist davon nicht betroffen.

| # | Stelle | Befund | erwartet laut Plan |
|---|---|---|---|
| 1 | Hinterkante, alle Stationen mit Querruder (z. B. Station 11: ~3 mm; Station 0: ~3 mm) | stumpf, volle Brettstärke | Querruder 28: Balsa 3 mm, **spitz geschliffen** (S. 5) |
| 2 | Station 2, y 33,2, Unterseite bei x ≈ 120 mm | Buckel kurz vor der Hinterkante, am Querruderanfang | glatte Unterseite (ebene Unterbeplankung 21) |
| 3 | Station 11, y 321,8, Nase | Oberseite steigt bei x ≈ 2–3 mm fast senkrecht | gerundete, geschliffene Nasenleiste |

**Was das Plugin braucht (Vorschlag):** einen Schritt „fertige Kontur“ zwischen Laserteil und
Profil-Fit — Nasenleiste auf Radius schleifen, Endleiste bzw. Querruder auf die im Plan
genannte Form spitz schleifen, Beplankungsstöße glätten — wie es beim Bryan offenbar schon
geschah. Danach: Profile neu erzeugen, `import_to_db.py snack --no-airfoil-table` erneut
(vorher den SNACK in der DB löschen).
