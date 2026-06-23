# Release Notes — Low-Re Airfoil Suitability (2026-06-04)

## In einem Satz
Du kannst jetzt für jede Flügel-Sektion sehen, **wie gut ein Profil bei deinen
tatsächlichen Flugbedingungen ist** (niedrige Reynolds-Zahlen, wie sie RC- und
UAV-Modelle fliegen) — vorberechnet für ~1.640 Profile, direkt im Airfoil-Preview.

---

## Neu: Profil-Eignungs-Bewertung (#821, #822)
- **Wo:** `/workbench/airfoil-preview` — pro Profil (Root & Tip) eine
  „Eignung"-Karte mit Bewertungen, plus Eignungs-Badges in der Profil-Auswahl.
- **Suche/Ranking:** neuer Endpoint `GET /airfoils/db/suitability` — gibt Profile
  nach Eignung sortiert zurück (für die aktuelle Sehnenlänge → Reynolds-Zahl,
  optional mit Modell-Kontext).
- **Datengrundlage:** mit **NeuralFoil** vorberechnete 2D-Polaren über ein
  Reynolds-Grid **40k–750k** (dicht im RC-typischen Bereich 50k–250k). Einmalig
  per Backfill berechnet; neu importierte Profile werden automatisch nachgerechnet.

## Die drei Bewertungs-Lesarten (#825)
Für jedes Profil, jeweils 0–1:
1. **Re-agnostisch** — allgemeine Low-Re-Güte beim Sektions-Reynolds (L/D,
   CL_max, Drag-Bucket, sanfter Abriss).
2. **Mission** — gewichtet nach Modelltyp (Trainer / Sport / Kunstflug / Segler /
   Flying-Wing).
3. **Ziel-CL** an **drei Betriebspunkten — Cruise / Best-Glide / Min-Sink:**
   bewertet, ob das Profil genau bei dem Auftriebsbeiwert sparsam ist, den *dein*
   Modell in dem Flugzustand braucht (Treffer auf den profil-eigenen Sweet-Spot;
   ein breiter, toleranter Drag-Bucket wird belohnt).

**Zusätzlich sichtbar:** Confidence-Badge (Modell-Vertrauen), Stall-Gutmütigkeit,
CL_max-Marge, ein Caveat-Hinweis und eine Tip-Re-Warnung bei verjüngten Flächen.

## Profil-Familien & Nurflügel (#825, #834)
- Jedes Profil wird klassifiziert: **flat_bottom / semi_symmetric / symmetric /
  cambered / reflexed**.
- **Reflex-Erkennung korrigiert (#834):** echte Flying-Wing-Profile (MH-Serie,
  EH-Serie, Eppler E18x, Clark YH, S5010) werden jetzt korrekt als `reflexed`
  geführt — relevant für **Nurflügler**.

## Bugfixes
- **#829** — kein `500` / SQL-Leak mehr bei ungültiger `aeroplane_id`; degradiert
  sauber.
- **#825-Cleanup (#833)** — Confidence wird über den *anliegenden* α-Bereich
  gemessen (Trust-Badge endlich aussagekräftig statt fast immer „niedrig");
  Caveat einsprachig; Tip-Re-Warnung nur noch bei echtem Flag; die Backfill-CLI
  läuft jetzt eigenständig.

## Wichtig zu wissen (ehrliche Grenzen)
- Die Scores sind ein **relatives Ranking**, keine absolute Wahrheit; **keine**
  Hysterese / Blasen-Bursting / Oberflächenrauheit modelliert. Bei niedriger
  Confidence → mit XFoil / Windkanal gegenprüfen.
- **High-Re** ist begrenzt (Grid endet bei 750k).
- Die **`reflexed`-Familie ist evtl. leicht über-inklusiv** (225 Profile) — die
  geplanten Filter (#835) helfen einzugrenzen.
- Der **Ziel-CL** nimmt einen elliptischen, unverwundenen Auslegungsflügel an
  (Sektions-CL ≈ Flügel-CL). Da die Masse oft eine Schätzung ist, zeigt ein
  **Provenance-Hinweis** an, ob der Zielwert „berechnet" (bewegliche Referenz,
  verschiebt sich mit dem Design) oder „geschätzt" (feste Referenz) ist.

## Nutzung / Betrieb
- Lokal sind **1.638 Profile** bereits bewertet. Nach dem Import neuer Profile
  passiert das automatisch. Vollständiger (Neu-)Lauf:
  `poetry run python scripts/backfill_airfoil_low_re.py [--force]`
  (nach Migrationen vorher `poetry run alembic upgrade head`, Backend danach neu
  starten).

## Geplant (noch offen)
- **#835** — Filter in der Profilsuche: Familie, Dicke und Rollen-Tags
  (Winglet / H-Stab / V-Stab / Acro / Low-Re …). Damit lässt sich z. B. direkt
  „nur Reflex-Profile für einen Nurflügler" anzeigen.

---
*Geliefert über PRs #823, #824, #827, #828, #830, #831, #832, #833, #836 (Issues
#821, #822, #825, #829, #834).*
