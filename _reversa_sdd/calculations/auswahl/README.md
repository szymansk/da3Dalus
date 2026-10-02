# Auswahlgraph und Urmodell

**Status: Soll, entschieden 02.10.2026 (O12). Noch kein GH-Ticket. Das ist ein Befund, siehe §6.**

Sieben geführte Fragen erzeugen ein **Urmodell**: ein erstes Flugzeug, das grundsätzlich fliegt. Der
Rechenkanon (`../canon/`) rechnet es danach wie jedes andere Flugzeug.

Grundsatz des Maintainers: „Es muss grundsätzlich fliegen, nicht perfekt sein. Es ist ein
Startwert."

Generator und Design-Agent liegen **außerhalb des Kanons**:
- Der Kanon rechnet und bewertet nicht (A10).
- Bänder erzeugen und bewerten, sie rechnen nicht.

## 1. Dateien

| Datei | Inhalt | Pflege |
|---|---|---|
| `auswahl.json` | Fragen, Optionen, Bedingungen, Bewertungsmatrix mit Begründungen, Bänder (`baender`), Skizzen-Streckung | von Hand, die Quelle der Wahrheit |
| `auswahl.html` | interaktive Seite mit Dreiseitenansicht ([Artifact](https://claude.ai/artifact/XqNVPRRcsqcJEkckMpipxS)) | **erzeugt**: `poetry run python scripts/build_selection_graph.py` |
| `BAENDER.md` | alle Bänder mit Quelle, Widersprüchen und Entscheidungen (§1–§3f) | von Hand |
| `flottenstatistik.json` | Statistik der RC-Modelltabelle (2 674 Modelle) je Mission | **erzeugt**: `python3 scripts/selection_fleet_stats.py <ziel>` |

## 2. Die sieben Fragen

| # | Frage | Optionen | Quelle der Entscheidung |
|---|---|---|---|
| 1 | Motorisiert? | ja / nein | ANFORDERUNGEN §6.1 |
| 2 | Mission | mit Motor: Trainer, Sport, Kunstflug, 3D, Speed, Elektrosegler, Scale, Park; ohne Motor: Segelflug-Trainer, Thermik, Hang, Wurf, Scale-Segler | §6.1 |
| 3 | Tragflügel | Eindecker, Doppeldecker, Tandem, Kastenflügel / Joined Wing | §6.1, Taxonomie |
| 4 | Flügellage (nur Eindecker) | Hoch-, Schulter-, Mittel-, Tiefdecker, ohne Rumpf | §6.1 |
| 5 | Leitwerk | hinten (Normal, T, Kreuz, V, Dach, H), vorn (Ente), keins (Nurflügel) | §6.1: Ente und Nurflügel sind Leitwerke, keine Bauarten |
| 6 | Steuerachsen | H+S, H+Q, H+S+Q, H+S+Q+Klappen; Nurflügel Elevons (± Seite) | §6.1 |
| 7 | Spannweite | 300–4000 mm | §6.1 |

**Bewertung der Kombinationen:**
- Jede Kombination ist eingestuft: typisch, möglich, ungewöhnlich oder unsinnig.
- „Unsinnig" ist **nicht wählbar** und braucht eine schriftliche Quelle oder die Aussage des
  Maintainers. Eine Einschätzung aus der Praxis allein ergibt höchstens „ungewöhnlich".
- Gesperrt sind heute nur die Doppeldecker-Segler: Elektrosegler, Thermik und Wurf.

## 3. Ablauf des Generators

Jeder Schritt nennt seine Quelle in `BAENDER.md`.

**Vorgabe** bedeutet: ein Wert ohne Quelle, gekennzeichnet nach dem Grundsatz oben.

1. **Bänder wählen.**
   - Die Mission bestimmt die Bänder.
   - Platzhalter (§3d, §3e): Scale nimmt die Sport-Bänder, 3D die Kunstflug-Bänder plus
     3D-Ausschläge, Park die Trainer-Bänder, Speed die Segler-Bänder mit Querrudern und Steuerachsen
     H+Q.
   - Segler nehmen die Bänder nach Steuerachsen (§3b).
2. **Masse** $m = C\,b^k$ mit dem Fit der Mission aus `flottenstatistik.json` (§2).
3. **Flügel.**
   - Die Streckung $A$ ist der Median der Mission [T]. Daraus folgen $S = b^2/A$ und $\bar c = b/A$.
   - Die Zuspitzung ist der Typwert des Bands.
   - Daraus folgen Wurzel- und Spitzentiefe sowie die MAC.
   - Die Flächenbelastung $m/S$ ist **Ergebnis** und wird nur gegen das Band geprüft.
4. **Rumpf.**
   - Länge $L = (L/b)_{Mission}\cdot b$ [T].
   - Querschnitt: Superellipse mit $n = 2$, Durchmesser $0{,}1\,L$ (Vorgabe, §3f).
   - Der Nasenhebel kommt aus dem Band in MAC, wo eines belegt ist.
   - Kein Rumpf bei „ohne Rumpf".
5. **Hebelarme.**
   - Motorflug: Leitwerkshebel aus dem Band in MAC (Trainer, Sport, Kunstflug), höchstens 60 % von $L$.
   - Segler: $l = 0{,}6\,L$ (§3b).
6. **Leitwerk.**
   - $S_H = V_H\,S\,\bar c/l_H$ und $S_V = V_V\,S\,b/l_V$ mit den Typwerten.
   - V-Leitwerk: Umrechnung nach Drela (§3b).
   - Ente, Tandem, Kastenflügel: Platzhalter mit `DesignWarning` (§3f).
   - Nurflügel: kein Leitwerk; 17° Pfeilung (§3c); Seitenflächen nach Lennon (§3).
7. **V-Form.**
   - Motorflug: nach Lennon, je Flügellage und Steuerachsen (§3).
   - Segler: $\Gamma_{eq} = B\,C_{L,therm}\,b/l_V$, mit $B$ = 5,25 bei H+S und 3 mit Querrudern (§3b).
   - Gepfeilter Nurflügel: etwa 0° (NACA, §3c).
8. **Einstellwinkel.**
   - Segler: Flügel 4–6°, Einstellwinkeldifferenz 2–3° (Lelke).
   - Motorflug: 0–3° (Lelke).
   - Nurflügel: Schränkung mit dem Kanon getrimmt; Panknin liefert den Startwert (§3c).
9. **Profil.**
   - Die Profilklasse folgt aus der Mission (§3, §3f).
   - Die Reynoldszahl ergibt sich aus $\bar c$ und der Geschwindigkeit aus der Auftriebsgleichung bei
     $C_{L,Auslegung}$: Segler 0,7, Wurf 0,6 (Drela), Motorflug 0,4 (**Vorgabe**).
   - Gewählt wird das beste Profil der Klasse aus der Profil-DB; die Eignung für kleine
     Reynoldszahlen ist dort bereits erfasst (gh-821).
   - Leitwerksprofil: symmetrisch und dünn (**Vorgabe**).
10. **Segmente und Ruder.**
    - Es gibt nur so viele Segmente, wie die Steuerachsen brauchen.
    - Querruder: 25 % Tiefe, 35–40 % der Halbspannweite außen (Lennon).
    - Klappen: Innenflügel mit 25 % Tiefe (**Vorgabe**).
    - Höhen- und Seitenruder: Flächenanteil nach Band.
    - Ausschläge: nach Band bzw. Lelke.
11. **Schwerpunkt** aus dem Kanon `cg-for-target-margin` mit dem Typwert des Stabilitätsreserve-Bands.
    Damit ist das Urmodell stabil per Konstruktion.
12. **Antrieb** (nur mit Motor).
    - $P = (W/kg)_{typ}\cdot m$ (§3a).
    - Daraus eine erste Wahl aus dem Teilekatalog.
    - Danach rechnet der Kanon Schub und Steigen (`motor-propeller-equilibrium`, Route A
      leistungsbegrenzt).
13. **Warnungen.** Jeder Platzhalter und jede Vorgabe ohne Quelle wird als `DesignWarning` mit
    Schweregrad sichtbar (ADR 0020).
14. **Anlegen in der App.**
    - Weg: `POST /aeroplanes`, `POST …/wings/{name}` (je Flügel mindestens zwei Schnitte),
      `POST …/fuselages/{name}`, Masse. Alternativ über die gleichnamigen MCP-Tools.
    - Einheiten: Flügel und Rumpf in m.
    - **Achtung:** Die Superellipsen-Parameter `a` und `b` sind Halbachsen (offener Fehler
      **#1146**: der Konverter übergibt sie als volle Breite).

## 4. Offene Punkte im Ablauf

- **Antriebswahl:** Die Regel für Zellenzahl und Spannung, und wie Motor und Propeller aus dem
  Katalog gewählt werden, ist nicht festgelegt.
- **Auslegungs-$C_L$ im Motorflug:** 0,4 ist eine Vorgabe ohne Quelle.
- **Masse beim Nurflügel:** Es wird der Massenfit der Mission genommen, nicht der Nurflügel-Fit
  (n = 17, Streuung ×1,63).
- **Seitenflächen des Nurflügels:** Lennon nennt die Bauformen; die Fläche selbst ist eine Vorgabe.

## 5. Beziehungen

- **ANFORDERUNGEN:** §5 O12 (Entscheidung), §6.1 (Fragen und Taxonomie), A10 (der Kanon bewertet nicht).
- **ADRs:** 0020 (Warnungen), 0022 (eine Autorität: Der Generator erzeugt Geometrie, der Kanon
  rechnet Werte), 0023 (Quellen, RC-Maßstab).
- **Design-Agent:** Epic #902 (KI-Copilot).

## 6. Befund: Soll ohne Ticket

Der Generator ist entschieden, aber nicht gebaut, und hat noch keine GH-Nummer. Nach `MARKERS.md` ist
ein Soll ohne Ticket ein Befund.

Ein Feature-Ticket braucht die Zustimmung des Maintainers (`/supercycle-ticket`). Der Generator gehört
nicht zum Kanon; das Ticket fällt deshalb **nicht** unter die Kanon-Ausnahme „Soll · Kanon" mit
Register K.
