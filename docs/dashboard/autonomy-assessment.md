# Autonomie-Assessment des Entwicklungsteams

**Frage des Product Owners:** Welche offenen GitHub-Issues kann das Team
**vollständig ohne den Menschen** bis zum gemergten PR umsetzen — und wo
braucht es eine Design-/Produktentscheidung des Nutzers?

**Bewertungs-Panel:** Senior Architect · Senior Backend Dev · Senior
Frontend Dev · Fullstack Reviewer/Critic · Senior QM · Fach-Experten
(Scholz/Anderson/AeroSandbox/AVL) · **4 Kundenpersonas**:
1. **Profi-RC-Designer** (F3A/Scale, kennt Polaren & Trimm)
2. **Hobbyist-Builder** (Trainer/Sport, will „funktioniert einfach")
3. **UAV-Ingenieur** (Loiter/Endurance, reproduzierbare Coeffizienten)
4. **Segelflug-/Nurflügel-Bauer** (Reflex, Streckung, Sink-Polare)

Ampel-Logik: **GREEN** = Spez eindeutig + isoliert + testbar → autonom.
**YELLOW** = umsetzbar, aber eine UX-/Verhaltens-/Scope-Entscheidung
gehört dem Nutzer. **RED** = tiefe Unsicherheit, harte Geometrie-/
Abhängigkeitsfragen oder explizit deferred.

---

## In dieser Kampagne autonom umgesetzt & gemergt

| Issue | Titel | PR | Verdikt |
|---|---|---|---|
| **#788** | ASB-Referenzfläche von der größten Tragfläche (nicht Import-Reihenfolge) — *critical, 8× falsche Coeffizienten bei Tail-first-Imports* | #847 | GREEN ✓ |
| **#787** | User-eingegebene `0` in Analyse-Numerik-Feldern bleibt erhalten (Falsy-Fallback-Bug) | #848 | GREEN ✓ |
| **#789** | Doppelte Nachbarpunkte in importierten `.dat` entfernen (ASB-repanel-Crash) | #849 | GREEN ✓ |
| **#790** | Degenerierte Fuselage aus dem ASB-Aero-Modell entfernen (AeroBuildup all-NaN) | #850 | GREEN ✓ |

Jede Korrektur kam mit failing-test-first, mocked Fast-Tier-Coverage (SonarCloud
`new_coverage` ≥ 80 %), Lane-Reinheit und CI-gate-Merge. #790 deckte beim
Test-Schreiben einen **latenten Zweitbug** auf (vertikale Fahrwerks-Streben
NaN-en AeroBuildup ebenfalls — jetzt mitgefixt; CAD-Spiegelung unberührt).

---

## Verdikt über den restlichen offenen Backlog

### GREEN — autonom umsetzbar (Spez eindeutig, isoliert)
- **#672** — α-Auflösungs-Auto-Recovery bei Polar-Fit-Rejection.
  *Aber:* Kern-Compute-Service (Oswald e → speist min-drag/min-sink/die
  ganze Wertepipeline), 2 Call-Sites + Schema + `polar_by_config`-
  Assemblierung, und **eigene erklärte Abhängigkeit von #670**
  (Vektorisierung; ohne sie kosten die ≤2 Retries spürbar Latenz).
  → **Empfehlung: eigene fokussierte Session, idealerweise nach #670.**
  Risikoprofil zu hoch für denselben autonomen Schwung wie isolierte
  Bugfixes.

### YELLOW — umsetzbar, aber Entscheidung gehört dem Nutzer
- **#786** — Polar-Config-Selektoren (`sweep_var`, Tool, Flight-Profile)
  sind dekorativ. *Frontend-Verdrahtung ist trivial, aber „AVL/
  velocity-Sweep wirklich ausführen" verlangt Backend-Endpoint-Support +
  eine Scope-Entscheidung (welche Sweeps wir offiziell anbieten).*
- **#674** — VLM als Default-Solver für Strip-Forces (statt AVL).
  *Memory-konform (`asb_over_avl`), aber ändert das Default-Verhalten
  einer öffentlichen API → Resultate verschieben sich; Nutzer sollte den
  Cut-over freigeben.*
- **#791** — OpenVSP-Importer verliert Profil-Camber (C_L0-Offset).
  *Root-Cause (wo genau die Camber verloren geht) noch nicht lokalisiert
  → investigation-heavy, Ergebnis offen.*
- **#762** — Profildicke bei Dieder-Rotation korrigieren (VSP/ASB-Parität).
  *Berührt den Loft-Pfad nahe der `cad_designer`-Topologie (read-only laut
  CLAUDE.md) → braucht Klärung, ob via neuem Creator lösbar.*

### RED — zurückgestellt / Nutzer-Input nötig
- **#814** — verformter sewn-solid STEP an scharfen Fuselage-Fillets.
  *Tiefer OCCT/CadQuery-Geometriebug; betrifft den CAD-Bau-Download →
  braucht visuelle Verifikation durch den Nutzer.*
- **#797** — Admin-API zum Löschen verwaister importierter Profile.
  *Im Ticket selbst „Deferred / lower priority", hängt an #794-Naming.*
- **#792** — VLM-`spanwise_resolution` an Sektionszahl skalieren.
  *GREEN-fähig & isoliert, aber im Ticket explizit „Low priority"
  (End-User nutzen AeroBuildup-Default) → bewusst nicht priorisiert.*
- **Epics/Cluster** #772/#794/#638/#584/#669, Trimm-Steuerflächen
  (#774–#781) — Design-Entscheidungen, nicht autonom.

---

## Kundenpersona-Konsens

- **Profi-RC** & **UAV**: #788 war der wichtigste Fix — vor der Korrektur
  waren importierte Coeffizienten für Tail-first-Modelle um den Flächen-
  verhältnis-Faktor (~8×) verfälscht; jetzt physikalisch plausibel.
- **Hobbyist**: #787 ist die spürbarste UX-Verbesserung — ein α-Sweep ab
  `0°` tut jetzt das Erwartete statt heimlich bei `-5°` zu starten.
- **UAV** & **Nurflügel**: #789/#790 machen den OpenVSP-Import robust
  (kein VLM-Crash bei Duplikatpunkten, kein NaN bei degenerierten Bodies).
- **Alle vier**: bei #786/#674 wollen sie ausdrücklich gefragt werden,
  bevor sich Solver-/Sweep-Verhalten ändert.

*Stand: autonomer Kampagnen-Lauf. GREEN-Batch (4 PRs) gemergt;
#672 + YELLOW/RED dem Nutzer zur Freigabe vorgelegt.*
