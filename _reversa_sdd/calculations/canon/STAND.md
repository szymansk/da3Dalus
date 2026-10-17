# Stand und Vorgehen — Rechenkanon

*Fortschreibung, damit nach einem Kontextwechsel dort weitergearbeitet werden kann, wo wir
stehen. Stand 2026-08-20.*

---

## 1. Das Vorgehen, in der Form, in der es sich bewährt hat

### Zwei Graphen, nicht einer

**Ist-Graph** — was der Code tut. Quelle ist der Code. Er entsteht aus dem Register
(`../`), das 1112 Knoten mit Formel, Einheit, Eingängen und `file:line` führt.

**Soll-Graph** — was er tun soll. **Quelle ist der Maintainer, nicht der Code.**
Das ist die wichtigste Regel dieses Vorgehens, und sie wurde teuer gelernt: Vier
Korrekturen in Folge entstanden, weil ich den Sollzustand aus der Datenbankstruktur
abgeleitet habe. Die Struktur zeigt, wie Daten herumgereicht werden; der Soll-Graph
braucht, woher sie stammen und wer sie entscheidet.

> **Beim Soll-Graphen wird gefragt, nicht gelesen.**

Die Differenz beider ist die Arbeitsliste.

### Was in den Soll-Graphen gehört

| gehört hinein | gehört nicht hinein |
|---|---|
| Rechenwege | Entscheidungs**verfahren** des Konstrukteurs |
| Entscheidungs**punkte** (welche Quelle ist aktiv) | wie er entscheidet (Baumstatus, Farben) |
| die Werte, die eine Entscheidung stützen | der Weg von dort zur Entscheidung |
| Formeln **in** den Kästen | Beschriftungen, die nur als Korrektur des Ist-Zustands Sinn ergeben |
| jede Eingabe des Solvers | Konstanten, die in einem zitierten Standard stecken |

**Regel für Kästen:** Jedes Symbol in einer Formel hat eine eingehende Kante, und der
Quellknoten trägt dasselbe Symbol. Ein Symbol ohne Kante ist ein unbelegter Eingang; eine
Kante auf ein Symbol, das in keiner Formel vorkommt, ist eine ungenutzte Beziehung. Beides
ist maschinell prüfbar.

**Regel für Lesbarkeit:** Der Soll-Graph muss ohne den Ist-Graphen lesbar sein. Wer ihn zur
Freigabe bekommt, kennt die Defekte nicht und soll sie nicht kennen müssen.

### Darstellung

Schräge blaue Kästen sind Eingaben, gestrichelt umrandet wenn geschätzt — **die Form trägt
die Rolle, der Strich die Sicherheit**. Grau: physikalische Konstante. Weiß: eine Rechnung.
Raute: eine Wahl oder eine Probe. Grün: Ergebnis. **Rot und dick: eine Iteration, die
konvergieren muss.**

Gebaut mit `scripts/build_canon_pdf.sh` — die ```mermaid-Umzäunung bleibt im Markdown
(GitHub rendert sie), das Skript zieht sie heraus und setzt fürs PDF ein
`\includegraphics` ein.

---

## 2. Das Modell, wie es nach drei Pfaden aussieht

Sieben Nachschärfungen, jede von einem realen Fall erzwungen — keine vorher ausgedacht.

**Vier Ebenen:** Größe · Formel · Anwendung · Vorbedingung.

**`kind`** entscheidet, was die Freigabe **zusätzlich** zu Quelle und Maßstab fragt:
`law` (nichts) · `procedure` (Beziehung, Methode, Annahmen, Verhalten bei
Nichtkonvergenz) · `fit` (Modell, Gültigkeitsbereich, Verwerfungskriterien) · `rating`
(wessen Entscheidung die Gewichtung ist).

**`shape`** entscheidet, ob es überhaupt etwas zu entscheiden gibt:
`single` · `route` (erzeugt einen **Test**, keine Entscheidung) · `duplicate` (mit
`copies_agree` — auseinandergelaufen ist der gefährliche Fall) · `approximation` ·
`conflict`.

**Quellenachse:** `design choice` (nur der Konstrukteur) · `dual-sourced` (Schätzung *und*
Kandidat, **er** schaltet) · `computed` (ein Erzeuger, keine Wahl).

**Ausschluss braucht einen typisierten Grund** — `input-quantity`, `other-chain`, `echo`,
`presentation`, `plumbing`. Zwei Sorten sind **nie** ausschließbar: eine Rückfallkonstante
(sie ändert die Antwort) und eine Zweitdeklaration einer bestehenden Größe (das ist der
Fund). *„Das ist keine Formel"* und *„das gehört nicht in den Kanon"* sind verschiedene
Aussagen.

**Benennung:** `<größe>_<konfiguration>_<einheit>`, ausgeschrieben, keine Normkürzel. Und:
**eine reynoldsabhängige Größe trägt die Bedingung im Namen** — `CL_max,stall`, nicht
`CL_max`.

---

## 3. Wohin es geht — zwei Diagramme statt einem

Der Durchbruch der letzten Runde, und er vereinfacht alles Vorherige.

**Der Rechengraph zerlegt nach Größen.** Zeitlos, ein Abhängigkeitsgraph.

**Das Aktivitätsdiagramm zerlegt nach Arbeitsschritten** — Mission wählen und füllen →
Konstruktion → Analyse. Zeitlich, hierarchisch: jeder Schritt bei Bedarf aufklappbar in
einen eigenen Ablauf mit eigenen Rechengraphen. Eine Aussage aus der Analyse fließt in die
Konstruktion des betreffenden Bauteils zurück.

Damit trennen sich **zwei Arten von Kreis**, die ich bisher gleich gezeichnet hatte:

| | wo er hingehört | wie er endet |
|---|---|---|
| **Rechenzyklus** — `V_stall ↔ CL_max,stall` | Rechengraph | Konvergenzkriterium |
| **Entwurfszyklus** — analysieren, Leitwerk ändern, neu analysieren | Aktivitätsdiagramm | das Urteil des Konstrukteurs |

### Drei Folgerungen daraus

**Ein Gesamtbild wird machbar.** Die Anwendungen fallen in ihre Formel zusammen:
`v_stall_clean`, `v_stall_launch`, `v_stall_landing` sind **ein** Knoten mit drei
Bindungen. Der Graph zählt Formeln, nicht Größen — etwa die Hälfte der Schätzung.

**Namen werden ableitbar und damit prüfbar.** Die Prozessstufe wählt die Bindung, die
Bindung bestimmt den Namen. Jeder benannte Ausgabewert muss sich auf ein Paar
*(Formel, Bindung)* zurückführen lassen; ein Name, der das nicht kann, ist eine nicht
erklärte Anwendung oder ein Duplikat.

**Invalidierung ist eine Traversierung, keine gepflegte Regel.** Was ungültig wird, ist die
transitive Hülle stromabwärts. Eine getrennt geführte Invalidierungsliste ist
konstruktionsbedingt ein Duplikat der Kanten — und Duplikate laufen auseinander. Der Graph
liefert zusätzlich **Granularität** (nicht alles, sondern das Erreichbare) und
**Reihenfolge** (topologisch, mit den Iterationen darin).

---

## 4. Was für Pfad 3 entschieden ist

| | |
|---|---|
| `airplane` | Eingabe. Referenzgrößen und `MAC` folgen daraus — **`MAC` ist keine Solver-Ausgabe** |
| `SM_target` | Entwurfswahl; die Mission schlägt vor, der Konstrukteur überschreibt |
| `x_cg` | **gerechnet** aus `x_NP − SM_target·c̄`, nie geschätzt |
| `m` | Schätzung. Der Komponentenbaum ist eine **eigene Kette**, die einen Kandidaten liefert |
| `h` | Schätzung; zerfällt in bekannte Platzhöhe und geschätzte Flughöhe |
| `ρ` | aus `h` über die Standardatmosphäre, **keine Eingabe** |
| `CL_max,stall` | aus einem α-Sweep bei `V_stall`, **keine Eingabe** |
| `g` | physikalische Konstante, keine Eingabe |
| Betriebspunkt | **`V` vorgegeben, `α` aus `L = W` gelöst, Ruder neutral** |
| `model_size` | **`xxxlarge`**, gemessen begründet |

**Ebene 0 sind damit sieben Positionen** — von ursprünglich etwa fünfzehn. Jede
Verkleinerung entstand, weil eine vermeintliche Eingabe ableitbar war.

**Herausgenommen:** Komponentenbaum und CG-Hüllkurve (eigene Kette), Handstartvergleich und
zulässige Massenabweichung (Missionsentscheidungen, eine Ebene darüber).

---

## 5. Offen

**Der Korrekturzweig** — Flügelversatz und Leitwerksskalierung. Nicht gezeichnet, weil
nicht entschieden ist, ob er existieren soll. Fällt er weg, verschwinden `a_VH`, beide
Empfindlichkeiten, die 5·MAC-Klemme und die nie ankommende Leitwerksgeometrie.

**Die vier Angaben je Prozedur.** Beide Prozeduren dieses Pfades — der Fixpunkt und die
`α`-Lösung — haben bisher nur die Beziehung. Methode, Annahmen und Verhalten bei
Nichtkonvergenz fehlen. Das ist die konkreteste Freigabelücke.

**Das Aktivitätsdiagramm** ist der nächste Schritt: grob *Mission füllen → Konstruktion →
Analyse*, dann je Schritt die Bindungen und die darin laufenden Rechnungen.

**Der ASB-Sweep als Hebel.** Der Solver kann über nahezu jeden Parameter sweepen. Jeder
Parameter, den er sinnvoll durchfahren kann, ist einer, den der Konstrukteur nicht raten
muss — und verschiebt die Grenze zwischen Eingabe und Ableitung weiter.

---

## 6. Arbeitsregeln, die gelten

**Tickets (02.10.2026):** Bugs im heutigen Code sofort; Kanon-Entscheidungen tragen bis zur Freigabe **`Soll · Kanon`** (Register ANFORDERUNGEN §7, Ausnahme in `MARKERS.md`), bei Freigabe ein Epic mit Untertickets. Befunde werden im Kanon festgehalten, wo sie
die Rechnung binden — nicht in einer Fundliste und nicht als Backlog.

**Kein Skill und kein CI-Gate, bevor der Kanon stabil ist.** Sieben Nachschärfungen in drei
Pfaden; ein Skill hätte jede vorherige Fassung zementiert. Und ein Gate, das sich auf einen
Entwurf beruft, erbt dessen Instabilität.

*Abgrenzung (Maintainer 14.10.2026, Epic #1173):* Der CI-Job `aero-kernel-aero` (#1177) ist **kein Gate auf
Kanon-Einträge**. Er schützt nur das Paket `aero_kernel/` gegen Regressionen seiner eigenen Goldwerte. Der
Rechenkern ist die ausführbare Referenz, mit der die Stabilität des Kanons vor der Freigabe belegt wird.

**Reproduktion vor Bericht.** Jede gemeldete Verletzung wird selbst nachgerechnet, bevor
sie weitergegeben wird. Zweimal war die Meldung schärfer als beschrieben, einmal lag der
Prüfagent falsch.

---

## 7. Der Navigator

`navigator.html` — der vollständige Rechengraph als begehbare Seite, erzeugt aus
`quantities/` und `formulas/`. 68 Größen in zwölf Schichten, Eingaben oben, Endergebnisse
unten. Eine Größe anklicken hebt ihre Vorgänger und Nachfolger bis zur eingestellten Tiefe
hervor; das Seitenfeld zeigt Beschreibung, erzeugende Formel als gesetzte Mathematik und
die Quelle.

Er ist **abgeleitet, nicht gepflegt**: Bei jeder Änderung am Katalog neu erzeugen, sonst
läuft er auseinander — dasselbe Duplikatproblem, vor dem A1 warnt. Neu erzeugen mit

```
poetry run python scripts/build_canon_navigator.py \
    _reversa_sdd/calculations/canon _reversa_sdd/calculations/canon/navigator.html
```

Die Seitenvorlage liegt in `scripts/canon_navigator_template.html`; das Skript setzt nur
die Daten ein. Die generierte HTML-Datei nie von Hand ändern.

Zwei Dinge, die beim Bauen zu beachten sind: Die Artifact-Sicherheitsrichtlinie lädt
Schriften nur von Google Fonts, deshalb scheidet KaTeX aus (seine Glyphen kämen vom
falschen Host) — **MathJax mit SVG-Ausgabe** trägt sie als Pfade im Bündel. Und die
Einpassung muss warten, bis das Gitter wirklich eine Größe hat, sonst startet der Graph
zufällig gezoomt.

**Zwei Fehler aus dem ersten Wurf, damit sie nicht wiederkommen.** `setPointerCapture` auf
dem SVG leitet alle Zeigerereignisse dorthin um — der Klick erreicht den Knoten dann nie,
und die Auswahl bleibt auf dem Startwert stehen. Statt Erfassung: auf `window` horchen und
per Bewegungsschwelle zwischen Ziehen und Klicken unterscheiden. Und die Seite wird
**rein ASCII** geschrieben, im Skript als `\uXXXX`, im Markup als Zahlenverweise, im
Stilblock als CSS-Escape; sonst hängt die Lesbarkeit der Umlaute daran, wer welche
Zeichensatzangabe mitschickt.

---

## 8. Die Datenbank ist keine Referenzflotte

Die Flugzeuge in `db/test.db` sind zum Teil aus VSPaero importiert und skaliert; Masse und
Massenschätzung passen dann nicht zur Größe, und ob jeder Import korrekt ist, ist offen.
**Ein Lauf über sie belegt nichts über eine Methode.** Auffälligkeiten gehen als Frage an
den Maintainer, nicht als Schluss.

Geplant: eine **Referenzflotte aus echten Bauplänen**, rekonstruiert mit dem
Bauplan-Plugin des Maintainers. Je Modell: Geometrie mit Profilen, Abflugmasse, Akku
(Kapazität, Masse), die passenden Motor-Propeller-Kombinationen — am besten APC, weil
deren Kennlinien vorliegen —, wo bekannt ein Flugwert aus Plan oder Herstellerangabe als
Probe, und eine Mischung aus Trainer, Segler, Kunstflug, Nurflügel.

---

## 9. Steigflug gerechnet (01.10.2026)

Schub bei Vollgas aus dem Motor–Propeller-Gleichgewicht (`motor-propeller-equilibrium`),
zwei Routen nach Datenlage wie in `Q-PT-6` entschieden: B mit Kreiswiderstand $R_m$
(Drehmomentgleichgewicht), A ohne (Leerlaufdrehzahl, ~25 % zu optimistisch). $R_m$ **nie**
aus $K_v$/$I_0$ schätzen — `Q-PT-6`; Daten: #1149. $V_y$/$\mathit{ROC}_{max}$ und
$V_x$/$\gamma_{max}$ sind Optimierungsprobleme mit beiden Kräftegleichgewichten
(nicht Kleinwinkel); $\gamma = 90^\circ$ ist eine erlaubte, benannte aktive Schranke.
Offen bleiben Kurven- und Sturzflug (beide brauchen den Schub bei Fahrt).

**Kurvenflug (01.10.2026):** nur die gehaltene Kurve — $\omega_{max}$ und $r_{min}$ bei
Vollgas als Optimierungsprobleme ($T = D$, $1 \le n \le n_{lim}$); welche Grenze greift
(Schub, Flügel, Struktur) ist Teil der Antwort. Querneigung als Eingabe,
`turn-load-factor` und `stall-speed-in-turn` gestrichen. Eckgeschwindigkeit
$V^* = V_S\sqrt{n_{lim}}$ ist eine Sicherheitsaussage und kommt zum Sturzflug.

**Sturzflug/Hüllkurve (01.10.2026):** $V_{max}$ als Optimierungsproblem ($T = D$ bei
Vollgas, vorher Eingabe 28 m/s); $V_D$ = Endgeschwindigkeit im senkrechten Sturz
($L = 0$, $D = mg + T$), obere Schranke ohne Propellerwiderstand, ersetzt $1{,}4\,V_{max}$
(vom Maintainer übernommen; Bryan 31,6 m/s); $V_A$ = Abrissproblem bei $n = n_{lim}$.
Offen: $n_{neg} = -0{,}4\,n_{lim}$ (Zulassungsverhältnis), `cruise-speed-resolution`.

**Querruderdifferenzierung — nicht im MVP (01.10.2026, Maintainer):** zu komplex, zu wenig
aussagekräftig. AeroBuildup fehlt das Giermoment aus induziertem Widerstand, AVL der
Profilwiderstand des Ruders; bei fester Rollrate ändert die Aufteilung reibungsfrei kaum
etwas. Details §3.1, Skripte `bryan_aileron_*.py`. Nicht wieder aufmachen ohne neues Werkzeug.

**Negatives Lastvielfaches (01.10.2026):** $n_{neg} = -0{,}4\,n_{lim}$ gestrichen. Stattdessen
`spar-break-load-factor`: $n_{break,\pm}$ aus dem eingebauten Holm, aus `airplane` abgeleitet;
**Befestigungen ignoriert** (Maintainer). Soll über #1139 und #1106.

**Rollwirkung (01.10.2026), §2.2:** `max-roll-rate` / `aileron-throw-fraction` prüfen eine geforderte Rollrate — je
Geschwindigkeit (Reiseflug, Anflug), vom Maintainer bestätigt — gegen die **im Flugzeug
festgelegten** Querruderausschläge (Konstruktionsparameter: Freiraum, Servokinematik,
Ruderhorn). Ergebnis: $p_{max}$ bei vollem Ausschlag und der nötige Anteil $s_{req}$;
$s_{req} > 1$ = nicht erreichbar. AeroBuildup reicht (Auftrieb, nicht induzierter Widerstand).

**Ausblick (02.10.2026), ANFORDERUNGEN §6:** später auf dem Kanon Maßnahmen zum Zielwert
und Zielkonflikte als Pareto-Front (ε-Constraint mit `asb.Opti`; Hebel = alles an
`airplane`, Zielgrößen = gestrichelt). Musterfall $V_S$ gegen $V_{max}$; Klappen weiten die
Front. Richtung, keine Entscheidung — ohne Ticket.

**Prüfung durch drei unabhängige Reviewer (02.10.2026) — eingearbeitet:** Masse ist Eingabe (A6,
`mass-summation` gestrichen); Klappen in der Geometrie, sonst keine Konfiguration (A3,
`high-lift-clmax`/`flap-clmax-factor` gestrichen, `V_S0`/`V_S,TO` als Abriss-Bindungen);
Schub bei Fahrt verbindet sich mit Steigen/Kurve/V_max/V_D (Route A leistungsbegrenzt);
`stall-speed` auf draft (Methode nicht freigegeben); Symbole `n_prop`, `w_sink`, `e_osw`,
`C_roll`, `k_S`; Einheiten Grad; veraltete Textstellen. **Offen für den Maintainer:**
Ticketregel (Soll ohne Nummer vs. „keine Tickets bis der Kanon steht“), Stabilitätsteil und
Nutzlast (Zweck), C_D0-Schleife (`reynolds-scheduled-polar`), `mean-thrust-derate`/f_T,
`cruise-speed-resolution`, Kinds außerhalb der erlaubten Menge (`substitution`).

**C_D0-Schleife behoben (02.10.2026)** nach unabhängigem Review: Kanon an **ADR 0004** angeglichen
(`parasite-drag-split`: C_D0 schädlich am Reiseflugpunkt, e Trefftz); `C_D,par` für die Parabel;
geschlossene V_md-Formel nur Probe. **O13 offen:** Analyse direkt mit Solver-Widerstand bräuchte
eine neue ADR gegen 0004.

**ADR 0026 (02.10.2026)** löst ADR 0004 in den Definitionen ab (Prinzip bleibt): Analyse mit
Solver-Widerstand, (L/D)max = W/D(V_md), Parabelformel = Probe; C_D0/e = Ausgleichsparabel, nur
Anzeige + berechneter Wert (ADR 0010); Auslegung Scholz-Kette mit c_f bei Missions-Re;
Vorbehalt k_e,D0 (Bryan +9 % induziert vs. AVL). O13 entschieden.

**Reisegeschwindigkeit (02.10.2026):** `cruise-speed-resolution`/`cruise-speed` gestrichen; benannte
Schließungen `endurance-and-range` (t_max bei V_mp, R_max bei V_md, Solver-Widerstand);
`V_cruise,target` als optionaler UAV-Zielwert (`cruise-target-performance`); Rollrate im
Reiseflug nur bei diesem Zielwert, sonst p̂ = pb/2V; `stall-margin-ratio` gestrichen (= k_S).

**f_T (02.10.2026):** `mean-thrust-derate`/`mean-thrust`/`static-thrust` gestrichen; `static-thrust-to-weight` T_0/W aus dem berechneten Standschub (V = 0).

**02.10.2026:** Pistenstufe gestrichen (Over-Engineering, Maintainer; K20). Butterfly aufgenommen
(`butterfly-approach`: V_S0(s), V_app(s), Gleitwinkel, s_max; Vorbehalt NeuralFoil bei großen
Klappenausschlägen; K21). Handstart neu gefasst als Urteil „handstartfähig oder Bodenstart",
Kriterien erst nach RC-Fachquelle.

**Handstart-Urteil gestrichen (02.10.2026, Maintainer):** kein Mehrwert; keine belastbaren Grenzen in den Quellen. Vom Start bleibt V_TO.

**Stabilität (02.10.2026)** — Umfang mit Maintainer: statisch längs + seitlich, vordere
SP-Grenze aus Höhenruderwirkung; Dynamik später. Schritt 1 angelegt: `neutral-point` (V_md),
`static-margin`, `cg-for-target-margin`, `static-margin-probe`; x_CG Eingabe, SM_target Zielwert.
Als Nächstes: Seitenstabilität (C_lβ, C_nβ), vordere Grenze.

**A10 (02.10.2026, Maintainer): Der Kanon rechnet, er bewertet nicht.** SM_min/Bänder/Pass-Fail →
Bewertung. Stabilität Schritt 2: `forward-cg-limit` (x_fwd, Abriss in Landekonfiguration, volles
Höhenruder wie gebaut), `lateral-static-stability-md/-app` (C_lβ, C_nβ, Spiralkriterium);
AVL-Gegenprüfung vor Freigabe.

**Massenhüllkurve (02.10.2026, ersetzt Nutzlast):** `mass-envelope` — V_S(m), V_max(m), ROC_max(m),
m_max,level, m_max,TO (Bomberbild), trimmbarer SP-Bereich über m; `max-mass-structure`;
`forward-cg-limit` darin aufgegangen. Nutzlast ist kein Kanonthema.

**O12 entschieden (02.10.2026):** Auslegung = Urmodell aus vier Fragen (motorisiert? → Mission →
Bauart → Spannweite), vom Kanon wie jedes Flugzeug gerechnet; `cruise-thrust-constraint`
gestrichen. Auswahlgraph als HTML unter `_reversa_sdd/calculations/auswahl/`.

**Auswahlgraph veröffentlicht:** https://claude.ai/artifact/XqNVPRRcsqcJEkckMpipxS — Quelle `_reversa_sdd/calculations/auswahl/auswahl.json`, Bau `poetry run python scripts/build_selection_graph.py` (HTML nie von Hand ändern).

**Auswahlgraph v2 (02.10.2026):** fünf Fragen (Leitwerk als Frage 4), Tandem und Kastenflügel/Joined Wing als Bauarten, jede Kombination Motor × Mission × Bauart bewertet (RC-Prüfer: Fachquellen + Modelltabelle 2 674 Modelle; Doppeldecker-Segler unsinnig, kein einziger in der Tabelle). Offen vom Prüfer vorgeschlagen: Startart (Segler), Antriebsanordnung, Rumpfform, Steuerachsen, Fahrwerk, Nurflügel-Grundriss; fehlende Missionen Combat/Funflyer, Jet/Impeller, FPV.

**Auswahlgraph v4 (02.10.2026):** sechs Fragen; Steuerachsen als Frage 5 (Höhe+Seite / Höhe+Quer / drei Achsen / drei Achsen+Klappen; Nurflügel Elevons ± Seitenruder), Mission „Trainer (Segler)" neu, Anmerkungen je Mission (Querruder-Trainer, Segelflug-Trainer meist Höhe+Seite). Ente ist eine Leitwerkskonfiguration (Höhenleitwerk vorn), nicht Bauart — Flügellage bleibt frei (Maintainer).

**Auswahlgraph v5 (02.10.2026):** Taxonomie bereinigt (Maintainer): Ente und Nurflügel sind Leitwerkskonfigurationen; sieben Fragen — Motor, Mission, Tragflügel, Flügellage (nur Eindecker, inkl. „ohne Rumpf"), Leitwerk, Steuerachsen, Spannweite. Nurflügel: Elevons typisch (Horten-Art).

**Auswahlgraph v6 (02.10.2026):** schematische Dreiseitenansicht (Draufsicht, Seiten-, Vorderansicht) aus den Antworten, reines SVG; Ruder orange. Streckung je Mission nur zur Anschauung (`skizze.streckung`), kein Band.

**Auswahlgraph v7 (02.10.2026):** Bewertungsmatrix vom RC-Prüfer in der neuen Einteilung neu erstellt (Tragflügel × Mission, Flügellage × Mission, Leitwerksgruppe hinten/Ente/Nurflügel × Mission, typische Leitwerke je Mission); keine neuen Sperren, nur die drei Doppeldecker-Segler. Bänder und Lücken: `auswahl/BAENDER.md`.

**Band Leistungsbelastung entschieden (02.10.2026):** W/kg min/typ/max je motorisierter Mission übernommen (`auswahl/BAENDER.md` §3a, `auswahl.json` → `baender`).

**Bänder vollständig (02.10.2026):** Jede Lücke ist mit Quelle, Platzhalter oder gekennzeichnetem Vorgabewert geschlossen (`auswahl/BAENDER.md` §3a–§3f). Grundsatz des Maintainers: Das Urmodell muss grundsätzlich fliegen, nicht perfekt sein.

**Urmodell-Generator als Ticket #1152 angelegt (02.10.2026).** Entschieden: Die Presets folgen den 13 Missionen des Auswahlgraphen (BR-MS5 teilweise ersetzt); ein erzeugtes Urmodell trägt `created_by="preset"`. BAENDER an Q-MS-14 angeglichen (Missions-Preset ist der einzige Autor der Missionswerte).

**BRYAN: Stabilität und Massenhüllkurve gerechnet (02.10.2026),**
`scripts/canon_checks/reference_fleet/bryan/ERGEBNISSE_STABILITAET.md`.
- Neutralpunkt 43,8 % MAC; Plan-Schwerpunkt 31,4 % MAC; Stabilitätsmaß 12,3 %.
- Spirale schwach instabil.
- m_max,level 1228 g, m_max,TO 1218 g (ohne Struktur). Hinten begrenzt der Neutralpunkt.
- Befunde: Der Abriss bei Re ≈ 50k ist nicht sauber erfasst (α ≈ 23°), ein Gegencheck ist nötig. Die
  vordere Grenze braucht Abriss-α fest und x < x_NP; das ist in mass-envelope.md nachgetragen.

**BRYAN korrigiert (03.10.2026):** Das Abrissproblem ist nicht konvex; ein Post-Stall-Plateau hat ein
zweites lokales Maximum (1,07 bei 23° gegen 1,26 bei 12°), in dem IPOPT ohne aktive Schranke hängen
blieb. V_S bei 151 g ist 5,29 statt 5,68 m/s. Die vordere Schwerpunktgrenze liegt bei 14,3 % MAC, hinten
begrenzt der Neutralpunkt bei 43,8 %. `stall-speed.md` verlangt jetzt das erste C_L-Maximum. **Offen für
die Freigabe:** dieselbe Prüfung auf das globale Optimum bei allen Kanon-Problemen nahe am Abriss.

**Nachprüfung nahe am Abriss (03.10.2026):** Von sieben Problemen ist nur `max-sustained-turn-rate`
betroffen (9,83 statt 8,79 m/s). In O3 steht jetzt das Freigabetor: Das Optimum muss auf dem Ast vor dem
ersten C_L-Maximum liegen. Butterfly ist ungeprüft (Bryan ohne Klappen).

**BRYAN Holm (03.10.2026):** n_break = 45 (Druckgurt an der Wurzel; Birkensperrholz 37,5 MPa nach USDA ×
2/3), m_max,struct = 6,8 kg ≫ m_max,level 1,23 kg. Der VLM-Befund war ein Fehler im eigenen Aufruf (24 Panels je Segment auf
winzigen Randbogen-Segmenten). Der App-Pfad (gh-855) ist sauber: Wurzelmoment 87,0 gegen 88,7 N·mm nach
Schrenk.
Nachtrag 13.10.2026 (gh-1171): Die Holmhöhe ist jetzt die Profildicke an der Holmachse (bündige Gurte);
an der Wurzel 14,7 statt 15,5 mm. Damit n_break = 41 und m_max,struct = 6,2 kg, die Aussage bleibt.

**AVL-Gegencheck Seitenstabilität am BRYAN (03.10.2026):** C_lβ stimmt auf 20 %; C_nβ ohne Rumpf grob,
mit Rumpf halbiert AeroBuildup (Rumpfanteil offen). **Korrigiert:** Die lokale C_lp in AeroBuildup ist etwa doppelt so groß wie in AVL/VLM, die stationäre
Rollrate weicht aber nur 23 % ab (nichtlinear, Spitzenabriss); nicht blockierend. Die VLM kennt keine
Ruder. Offen: eine gemessene Rollrate entscheidet. Die App gibt C_lp aus AeroBuildup ohne Hinweis aus.

**e-Hawk als zweites Referenzflugzeug (03.10.2026):** aus den Projekten des Maintainers zusammengesetzt
(`reference_fleet/ehawk/`). V_S 4,51, (L/D)max 14,3, Sinken 0,38 m/s. **Blockierender Befund an beiden
Flugzeugen:** Der Neutralpunkt aus AeroBuildup liegt etwa 10 % MAC zu weit hinten (kein Abwind am
Leitwerk). Der App-Fehler ist Ticket #1154; `neutral-point.md` braucht ein Wirbelgitter-Werkzeug
(Entscheidung des Maintainers). Am BRYAN schrumpft das Stabilitätsmaß des Plan-Schwerpunkts damit auf etwa
2 %.

**Querruder über mehrere Segmente (03.10.2026):** Gleichnamige Folgesegmente erben vom ersten Segment
(Maintainer). Die App wendet das beim Import nicht an und rechnet die Fortsetzungen als Klappen: Ticket
#1155. Der e-Hawk der Referenzflotte setzt die Vererbung jetzt um.

**Neutralpunkt bei kleiner Re (03.10.2026, `reference_fleet/NP_NIEDRIGE_RE.md`):** AVL ist besser als
AeroBuildup (hat den Abwind), aber nicht kalibriert. Beim BRYAN verschiebt allein die CLAF-Wahl den
Neutralpunkt um 3 % MAC; mit NeuralFoil-Steigungen um über 20 %. Keine Literatur mit Fehlerzahlen unter
Re 500k. Freigabe braucht geflogene Schwerpunkte der Referenzflotte.

**Geometrische RC-Methode für den Neutralpunkt (03.10.2026):** Gerechnet nach rcplanedesigner (Flügel
plus halbe Höhenleitwerksfläche, Rumpf −5 % MAC). Damit liegen beide Plan-Schwerpunkte im Zielbereich
(BRYAN 10,1 %, e-Hawk 8,6 %), anders als mit AVL (1,5 % / 15,8 %) oder AeroBuildup. Vorbehalt: teilweise
zirkulär. Entscheidung des Maintainers zum Werkzeug des Kanons steht aus.

**Neutralpunkt: Gegenprüfung aller belegten Methoden (03.10.2026, `np_methods.py`):** Pappas (MA 10/2009)
und das Lehrbuch (mit Abwind und Streckung) stimmen mit AVL auf 1–4 % MAC überein, an beiden Flugzeugen.
Die pauschale RC-Faustregel (K 0,5, −5 %) kennt keine Streckung und irrt um 5–11 % (beim BRYAN in der
unsicheren Richtung). Der frühere Schluss „RC-Faustregel trifft" ist zurückgenommen. Offen ist der
Rumpfanteil.

**A11 entschieden und umgesetzt (03.10.2026, ADR 0027):** Unscharfe Größen sind Intervalle [min, max]
ohne Kern über Methodenwelten. Je Welt wird durch die ganze Kette gerechnet, nie Intervall auf Intervall.
Monotonie wird geprüft. Übereinstimmung heißt „nicht validiert", nicht scharf; die Streuung ist eine
untere Schranke. Erster Fall Neutralpunkt mit Lehrbuch, Pappas und AVL (AeroBuildup raus). Register
K25/K26; der Navigator kennzeichnet unscharfe Größen und ihre Folgen; #1154 ist kommentiert.

**Vordere Trimmgrenze am BRYAN (03.10.2026):** AeroBuildup 14,3 %, AVL 10,4 % bzw. 13,5 % MAC.
AeroBuildup liegt auf der vorsichtigen Seite, weil der Abwind am Leitwerk den nötigen Abtrieb unterstützt
und AeroBuildup ihn nicht kennt. Die Erwartung war falsch herum. Kandidat für A11, Streuung 10,4–14,3 %.

**A11 geschärft (03.10.2026):** Unscharf nur, wenn die Streuung eine Auslegungsentscheidung ändern kann.
Liegt ein Werkzeug belegt auf der vorsichtigen Seite, bleibt die Größe scharf mit Gültigkeitsbedingung.
Die vordere Trimmgrenze bleibt scharf (AeroBuildup, vorsichtig; AVL bis 4 % MAC weiter vorn).

**Seitenstabilität nach A11-Regel 5 eingeordnet (03.10.2026):** Rollrate und Querruderausschlag sind
unscharf (Welten AeroBuildup und AVL, 23 %). C_nβ und das Spiralkriterium bleiben scharf mit
Gültigkeitsbedingung (Faktor 2,4 ohne feste Richtung; die Entscheidungen stimmen überein).

**Urmodell-Flotte (03.10.2026, `scripts/canon_checks/reference_fleet/urmodell/`):** 74 typische Urmodelle,
je eine recherchierte Spannweite, Kanon fehlerfrei durchgerechnet. Befunde:
- B1: Kleine SM-Ziele (3 %) liegen unter der Neutralpunkt-Streuung. Wer nur die geometrischen Welten
  nutzt, setzt Kunstflieger in der AVL-Welt instabil. Der Generator (#1152) muss den vorderen Rand
  aller Welten nehmen.
- B2: Der Neutralpunkt aus AeroBuildup liegt bei Leitwerksmodellen −6 bis +29 % MAC neben AVL
  (Median +14,5), bei Nurflügeln −4 (#1154 kommentiert).
- B3: Das Spiralurteil kippt bei 16 von 74 Flugzeugen. AeroBuildup fehlt der Pfeilungsbeitrag zu C_lβ
  (Reproduktion, GH #1156). Die Seitenstabilität ist deshalb unscharf eingeordnet (K27,
  **Bestätigung offen**).
- B4: Rollrate AeroBuildup/AVL 1,04–1,20, AeroBuildup immer höher. Bleibt unscharf.
- B5: Nurflügel ohne Flosse mit 17° Pfeilung ist richtungsneutral (C_nβ ≈ 0). Offen für #1152.

**Flotte nachgerechnet (04.10.2026):** Die Mittelflosse der Nurflügel schwebte im Generator hinter dem
Flügel (in den Renderings sichtbar) und ist jetzt korrigiert. Neu: Spiralurteil uneinig bei 24 von 74,
C_nβ-Vorzeichen bei 15. Betroffen sind nur Nurflügel ohne oder mit Mittelflosse. Galerie:
https://claude.ai/artifact/So2qRuebq75FuNu5W3wZuC

**K27 entschieden (05.10.2026):** Die Seitenstabilität kommt für alle Bauarten aus AVL, mit Rumpf und als
nicht validiert gekennzeichnet. ASB-VLM ist geprüft und taugt nicht: 46 von 74 Spiralurteilen weichen
von AVL ab (Flotte B8). Neu im Kanon: Verdopplungszeit der Spirale statt Vorzeichen, sowie V_V und
Drelas B als Geometrie-Anker mit Vorbedingung Leitwerk. Offen ist O14: Rechenzeit und wann gerechnet wird.

**O14 teilweise entschieden (05.10.2026, K28):** Rechnungen, die Minuten dauern, werden aktiv angestoßen und
laufen im Hintergrund auf einem unveränderlichen Snapshot der Versionierung. Den Snapshot gibt es schon
(`aeroplane_version_service.snapshot`). Offen: Behandlung der Sekunden-Rechnungen und Anzeige veralteter
Werte.

**O14 weiter entschieden (05.10.2026, K29):** Sekunden-Rechnungen laufen beim Verlassen der
Konstruktionsansicht. Veraltete Werte sind ausgegraut, der alte Wert bleibt per Mouse-over sichtbar. Offen
ist nur noch, wo die Stufe festgelegt wird (Kanon-Eintrag oder App).

**O10 entschieden (05.10.2026):** Masse, Höhe, Geschwindigkeit und Ruderstellung gehören zum
Betriebspunkt (§3.2); die Ruderstellung ist dort eine Ausgabe (eingetrimmt). Die Genauigkeitsstufe ist
eine Rechner-Einstellung (A3).

**O5 entschieden (05.10.2026, K30):** Die Luftdichte kommt aus der exakten ISA (`method="isa"`). Heute nutzen alle 15 Aufrufer die geglättete Näherung.

**O1 entschieden (05.10.2026, K31):** Der Korrekturzweig (Flügelversatz, Leitwerksskalierung) besteht aus Auslegungsrechnungen und gehört in einen eigenen Auslegungskanon, nicht in den Rechenkanon. Die Grenzfälle `cg-for-target-margin`, `stall-wing-loading-limit` und `aileron-throw-fraction` bleiben im Rechenkanon (Maintainer).

**O3 entschieden (05.10.2026, K32):** Der Anstellwinkel aus L = n·W wird nach §3.4.2 gelöst: Abtastung bis zum ersten C_L-Gipfel als Schranke, IPOPT, und ohne Lösung kein Wert, sondern eine DesignWarning. `stall-onset-detection` sucht künftig ab dem ersten Gipfel.

---

## 10. Format migration findings (#1181)

Beim Nachtragen der maschinenlesbaren Felder (README „Machine-readable fields“) in alle 57 Formel- und
137 Größeneinträge (anfangs 116; die Entscheidungen unten fügten Größen hinzu) gefunden. **Nicht stillschweigend korrigiert** — außer den als *behoben* markierten
mechanischen Fehlern. *Eskaliert* heißt: Feld ausgelassen, `# ESCALATED:` im Eintrag, Entscheidung beim
Maintainer; `check_canon.py` meldet es als *open*.

**Behoben (mechanisch)**

- `spiral-parameter`, `vertical-tail-volume`: fehlten in den Used-by-Zeilen von `airplane` (beide), `aircraft-mass`, `gravity`, `air-density`, `minimum-drag-speed` (nur `spiral-parameter`). Ergänzt.

**Format**

- YAML 1.1 (PyYAML `safe_load`) liest den Schlüssel `on:` der Vorbedingungen als Boolean `true`. `check_canon.py` liest mit YAML-1.2-Booleans; der Importer (#1174) muss es ebenso tun (README sagt es). **Behoben (Architekt, 14.10.2026):** der Schlüssel heißt jetzt `parameter`; Schlüssel und Werte meiden YAML-1.1-Booleans, `check_canon.py` prüft es und liest wieder mit `safe_load`.
- ARCHITECTURE §8.9 (aero_kernel): das Größenbeispiel trägt `entry: quantity`; die Größeneinträge tragen `kind: quantity` und kein `entry:`.
- ARCHITECTURE §8.9: das Beispiel gibt `speed-from-stall-margin`/takeoff `when: has_flap`; der Eintrag nennt keine Bedingung, deshalb steht keine. Seit der Maintainer-Entscheidung vom 14.10.2026 gibt es `has_flap` nicht mehr (Start/Landung sind Konfigurationen).
- ARCHITECTURE Anhang A schlägt für `mass-envelope` die Kostenklasse `minutes` vor; der Eintrag sagt nirgends „Minuten“, deshalb kein `cost:` (kein Eintrag sagt es). **Behoben (14.10.2026):** `cost: minutes` auf `mass-envelope`, Quelle Epic #1173 / K28.
- README „Naming“: das Schema `<quantity>_<configuration>_<unit>` (`v_stall_landing_mps`) ist das Registerschema; die Kanon-Slugs sind kebab-case ohne Einheit (`stall-speed-landing`). Im Stall-Speed-Beispiel des README sind die Anwendungen jetzt Kanon-Slugs (**umbenannt, #1181**); die Spalte „binds `cl_max`“ behält `cl_max_clean`/`_takeoff`/`_landing`, weil es für Take-off und Landung keine Kanongröße gibt und `max-lift-coefficient` seit dem Umbau eine Ausgabe ist (siehe `stall-speed` unten). Das Naming-Schema selbst bleibt unverändert.

**Anwendungen und Bindungen**

- `stall-speed`: die Anwendungstabelle nutzt Registernamen. Zuordnung: `v_stall_clean_mps` → `stall-speed`, `v_stall_takeoff_mps` → `stall-speed-takeoff`, `v_stall_landing_mps` → `stall-speed-landing`, `cl_max_clean` → `max-lift-coefficient` (seit dem Umbau eine **Ausgabe**), `air_density_at_altitude` → `air-density`; `cl_max_takeoff`, `cl_max_landing` → keine Kanongröße (mit `high-lift-clmax` gelöscht). **Nachtrag (#1181):** jetzt `max-lift-coefficient-takeoff`/`-landing` — als Ausgaben, nicht als Bindungen.
- `stall-speed`: die Tabelle bindet `cl_max` und `rho`; seit dem Umbau (01.10.2026) unterscheiden sich die Anwendungen durch die **Konfiguration des Flugzeugs**, die keine Größe benennt. Eskaliert. **Behoben (Architekt, 14.10.2026):** neue Größen `airplane-takeoff`, `airplane-landing` aus dem neuen Eintrag `airplane-configuration`; die Anwendungen binden sie, die Tabelle ist umgeschrieben. Offen dort: der Klappenausschlag je Konfiguration (eskaliert). **Entschieden (Maintainer, 14.10.2026, D1/Option C):** zwei Entwurfseingaben `flap-deflection-takeoff`, `flap-deflection-landing` (deg, ohne Vorgabe), gebunden in den beiden Anwendungen von `airplane-configuration`. **Nicht durch den Anschlag `positive_deflection_deg` begrenzt**, keine Prüfung, keine Warnung: der Anschlag in den Flugzeugdaten kann ein erster Entwurfswert sein; der Kanon dient dazu herauszufinden, welcher Anschlag für die gewünschte Geschwindigkeit nötig ist — der Anschlag zählt für den Konstrukteur, nicht für den Kanon. Gültigkeitshinweis zum NeuralFoil-Klappenmodell im Eintrag (ANFORDERUNGEN Z. 544–546, 1007–1008). **Flugzeug ohne Klappen (Architekt, 14.10.2026):** `optional: [flap_deflection]`; der Eintrag nennt die vier Fälle (keine Klappen/fehlt → unverändert, keine Warnung; keine Klappen/gegeben → unverändert + `practice`-Warnung `deflection_without_flap`; Klappen/fehlt → `missing_input`, die Reiseflug-Abrissgeschwindigkeit rechnet weiter; Klappen/gegeben → exakt, auch über den Anschlag). README: drei Ausgänge eines fehlenden optionalen Parameters. `motor-propeller-equilibrium`: Route A ohne R_m ist eine erklärte Methodengrenze mit `practice`-Warnung (Q-PT-6). **Eskaliert:** welche Bauteile als Klappen zählen — der Kanon sagt nur „if the geometry has flaps“; die frühere README-Formulierung („trailing-edge devices on the main wing acting as flaps“) stammte von mir, nicht aus dem Kanon. **Entschieden (Maintainer, 14.10.2026):** „Klappen sind alle Ruder, die wie Klappen wirken — also auch Flaperons.“ Im Geometrieformat die Hinterkantenklappen mit `role: flap` oder `role: flaperon` (`TrailingEdgeDevice.role`); in Start- und Landekonfiguration werden alle auf den gegebenen Ausschlag gesetzt.
- `stall-speed`: Bedingung widersprüchlich — Tabelle „the wing carries a flap“, Text vom 02.10.2026 und die Größen `stall-speed-landing`/`-takeoff`: ohne Klappen gleich der Reiseflug-Abrissgeschwindigkeit. Eskaliert. **Entschieden (Maintainer, 14.10.2026):** Landung und Start sind Konfigurationen, keine Flugphasen; V_S wird je Konfiguration gerechnet und speist die Geschwindigkeiten, die es nutzen (Anflug und Aufsetzen aus V_S0, Start aus V_S,TO). Die beiden Anwendungen existieren immer, ohne `when`; ohne Klappen gleich der Reiseflug-Abrissgeschwindigkeit. Der Begriff `has_flap` ist damit unbenutzt und aus dem Vokabular gestrichen.
- `stall-speed`: Take-off- und Landeanwendung haben keine Größe für ihr `C_L,max` (zweite Ausgabe). Eskaliert. **Behoben (Architekt, 14.10.2026):** neue Größen `max-lift-coefficient-takeoff`, `-landing`.
- `stall-speed` (Größe): die Beschreibung nennt „V_S1 clean, V_S0 landing, V_S,TO takeoff“ in einer Größe, obwohl es drei Größen sind (A2).
- `speed-from-stall-margin`: `k_S` je Anwendung offen („choosing is the maintainer's call“), keine Quelle, keine Größe. Eskaliert. **Entschieden (Maintainer, 14.10.2026, Option A):** Zielgrößen `approach-speed-margin-target` (1,3; Lennon Kap. 20, CS 25.125 als Transport-Referenz), `touchdown-speed-margin-target` (1,2; Lennon Kap. 4, 14), `takeoff-speed-margin-target` (1,1; Sadraey §4.3.4) mit Quelle im `default`; die Anwendungen binden sie. Prosa korrigiert: das Band „1.2–1.25“ hat für 1,25 keine Quelle, „1.3 from regulation“ ist CS 25.125 (Transport). Neu: Lastvielfachen-Reserve n = k²; Aufsetz-Widerspruch Lennon 1,2 gegen RC-Network *Abfangen* (≈ V_min) genannt, nicht entschieden (A10).
- `aileron-deflection-required`, `roll-rate-cruise-target`, `stall-wing-loading-limit`: Existenzbedingung „wenn das Ziel gegeben ist“ — eine Bedingung über gegebene Eingaben, keine Geometrietatsache; das `when`-Vokabular kennt sie nicht. Eskaliert. **Behoben (Architekt, 14.10.2026):** neues Anwendungsfeld `given: [<slug>, …]`; die drei Einträge tragen es.
- `cruise-target-performance`: `cruise-speed-target` ist laut Größe optional; der Eintrag sagt nicht, was ohne Ziel geschieht.
- `linear-lift-curve-inverse`: die Ausgabe `characteristic-angle-of-attack` trägt drei Bedingungen (α_stall, α_bg, α_ms) in einer Größe (A2); welches C_L je Anwendung gebunden wird, hat keine Größe. Eskaliert. **Teilweise behoben (Architekt, 14.10.2026):** drei Größen `angle-of-attack-stall`, `-best-glide`, `-minimum-sink`, drei Anwendungen; `stall` bindet `max-lift-coefficient`. `cl` von `best_glide` und `minimum_sink` bleibt eskaliert (keine Größe hält C_L bei V_md bzw. V_mp). **Entschieden (Maintainer, 14.10.2026, D2/Option B):** α ist Entscheidungsvariable der Optimierungen; `angle-of-attack-best-glide`, `-minimum-sink`, `-stall` sind jetzt Ausgaben von `minimum-drag-speed-from-polar`, `minimum-sink-speed-from-polar` und `stall-speed` (Anwendung `clean`), dazu `lift-coefficient-best-glide` / `-minimum-sink` (C_L am Optimum, gelesen vom Probe). `linear-lift-curve-inverse` ist ein Probe (A7) mit `angle-of-attack-best-glide-probe` / `-minimum-sink-probe`; die Stall-Anwendung ist gelöscht. **Eskaliert:** der Abrisswinkel in Start- und Landekonfiguration (D2 nennt nur `clean`).
- `static-thrust-to-weight`: bindet `thrust-at-airspeed` „bei V = 0“; eine Bindung nennt eine Größe, nicht den Betriebspunkt; eine `static-thrust`-Größe gibt es nicht. Eskaliert. **Behoben (Architekt, 14.10.2026):** der Eintrag bettet die Antriebsbeziehungen ein (`embeds`), V = 0 steht in seiner Form; kein `thrust-at-airspeed`, keine statische Anwendung.
- `load-factor`: die Größe sagt „bound per application: 1 in straight level flight, n_lim for the envelope“; keiner der vier Leser (`lift-coefficient-required`, `minimum-drag-speed-from-polar`, `minimum-sink-speed-from-polar`, `stall-speed`) nennt seine Bindung — alle binden die generische Eingabe. **Behoben (Review, 14.10.2026):** `stall-speed` (clean, takeoff, landing), `minimum-drag-speed-from-polar`, `minimum-sink-speed-from-polar` binden `n_load` als Konstante 1 (Quelle: Definition n = L/W, wie in `max-mass-structure`; Geradeausflug L = W), `inverted` −1; `lift-coefficient-required` liest weiter `load-factor` am Betriebspunkt des Aufrufers, die Größe hat jetzt `default` 1 mit derselben Quelle. Weitere Leser von `load-factor` gibt es nicht.
- `maneuvering-speed`: ist laut Text „das `stall-speed`-Problem bei n = n_lim“ — eine Anwendung von `stall-speed` als eigener Eintrag.
- `lateral-static-stability-app` / `-md`: dieselbe Formel, zwei Einträge, die sich nur in V (V_app / V_md) unterscheiden — zwei Anwendungen einer Formel als zwei Einträge.
- `spiral-parameter`, `vertical-tail-volume`: die „Precondition“ Leitwerk ist als Anwendungsbedingung `when: has_vertical_tail` erfasst (für Nurflügel nicht gerechnet), nicht als Vorbedingung.

**Vorbedingungen**

- `stall-speed`: die Vorbedingung `cl_max` liegt seit dem Umbau auf einem Ausgabeparameter, nicht auf einer Bindung.
- `stall-speed` (`rho`), `glide-distance-from-ratio` (beide), `inverted-max-lift-coefficient` (Benennung): der Eintrag sagt nicht, was bei Verletzung geschieht → `warning` gesetzt.
- `inverted-max-lift-coefficient`: `alpha_range_past_inverted_stall` als `error` gelesen („the value is **not** reported as a minimum“) — der Eintrag nennt zugleich eine DesignWarning. **Entschieden (Koordinator, 14.10.2026):** `error` bleibt — der Kern gibt nie einen Platzhalterwert zurück (A6, ADR 0020); „not reported as a minimum“ heißt: kein Wert.
- `inverted-max-lift-coefficient`: die Benennungs-Vorbedingung verletzt der Kanon selbst — die Größe `inverted-max-lift-coefficient` trägt keine Auswertebedingung im Namen.
- `linear-lift-curve-inverse`: die gebrochene Annahme „C_L im Fit-Fenster“ (🔴-Block) steht nicht als Vorbedingung da — Kandidat, nicht gesetzt.

**Eingänge, die die kanonische Form braucht, der Eintrag aber nicht nennt**

- `best-angle-of-climb`, `best-rate-of-climb`, `dive-speed`, `max-level-speed`, `max-sustained-turn-rate`, `min-sustained-turn-radius`, `mass-envelope`: die Drehmomentbilanz im Problem braucht Motor- und Propellergrößen (K_v, I_0, R_m, U_bat, P_mot,max, D_prop) und `n_prop` als Variable; die from-Zeile nennt nur `thrust-at-airspeed`, laut Größe ein Wert „at the speed currently flown“. **Behoben (Architekt, 14.10.2026), außer `mass-envelope`:** neues Formelfeld `embeds` — die sechs Optimierer und `static-thrust-to-weight` lesen keinen Schubwert mehr, sondern werten Drehmomentbilanz, Fortschrittsgrad, Propellertabelle und Schubbeiwert in sich aus (`embeds: [motor-propeller-equilibrium, advance-ratio-from-speed, propeller-table-lookup, thrust-at-airspeed-from-coefficient]`); Motor- und Propellergrößen sind Eingänge, `flight-speed` nicht (V und n_prop sind eigene Variablen). Neues Feld `optional: [r_m]` auf ihnen und `motor-propeller-equilibrium` (Route A/B nach Datenlage). **`mass-envelope` eskaliert:** seine kanonische Form nennt `T(V, n_prop)`, aber keine Drehmomentbilanz; sie bettet die Probleme von `stall-speed`, `max-level-speed` und `best-rate-of-climb` ein — unverändert, liest weiter `thrust-at-airspeed`. **Entschieden (Architekt, 14.10.2026):** `embeds` ist transitiv, der Importer bildet den Abschluss; `mass-envelope` bettet `stall-speed`, `max-level-speed`, `best-rate-of-climb` und die vier Antriebsbeziehungen ein, liest Motor-/Propellergrößen sowie `airplane-takeoff`/`-landing`, kein `thrust-at-airspeed` mehr. `cost: minutes` — Quelle: vom Maintainer freigegebener Plan des Epics #1173 (14.10.2026), lange Rechnung nur auf ausdrückliche Anforderung (K28). `thrust-at-airspeed` hat damit keinen Leser mehr. **Entschieden (Architekt, 14.10.2026):** Rolle `output` — der nutzersichtbare Schub am gegebenen Betriebspunkt und der Knotenpfad, der die gemeinsamen Antriebsbeziehungen allein prüft.
- `mass-envelope`: die Schranke `x_CG < x_NP` nutzt den Neutralpunkt; `neutral-point` steht nicht in der from-Zeile. **Deklariert (#1181).**
- `roll-rate`: `p_hat_max = p·b_ref/(2·V_app)` nutzt `b_ref`; `wing-span` steht nicht in der from-Zeile (nur über `airplane` erreichbar). **Deklariert (#1181).**
- `motor-propeller-equilibrium`: die Form nutzt `eta_mot` (Vorgabe 0,85, BR-PM3, laut Text ohne Modellmaßstab-Quelle) — weder Eingang noch Konstante mit Quelle. **Entschieden (Maintainer, 15.10.2026, E1/Option B):** Eingang `motor-efficiency` mit Vorgabe 0,75 (Roxxy Motoren-Fibel Kap. 3, Band 75–85 %; untere Grenze, weil Route A ihn bei P_max anwendet, oberhalb des Wirkungsgradmaximums); die Übernahme der Vorgabe ist sichtbar (INFO + `provenance.defaults_used`). Gelesen von `motor-propeller-equilibrium` und den acht Einbettenden. Ein Katalogwert für den Wirkungsgrad wird nicht aus Katalogdaten gelesen (`airplane-components` erzeugt keinen); wer einen hat, übergibt ihn als Eingang `motor-efficiency` (Delta-Review F7). Ob die Katalogleistung elektrisch oder Wellenleistung ist, sagt die Quelle nicht — offen. `motor-max-power` nennt sie elektrisch, jetzt als 🟡 INFERRED markiert (Delta-Review F6).

**Typen und Bedeutungen**

- `lift-coefficient`: eine Größe, zwei Bedeutungen — „either produced by the AeroBuildup sweep or demanded by the level-flight balance“ (A2).
- `inverted-max-lift-coefficient`, `stall-onset-detection`: binden `lift-coefficient` (Skalar, Erzeuger `lift-coefficient-required`), die Form braucht die abgetastete Polare C_L(α); eine Polaren-Größe gibt es nicht. **Teilweise behoben (Architekt, 14.10.2026):** neuer Typ `polar`; beide Einträge lesen `inputs: {polar: …}`. Die Polaren-Größe und ihr Erzeuger bleiben eskaliert — der Text nennt keinen (Kandidat: der α-Sweep von `stall-speed` bei V_S).
- `stall-onset-detection`: bindet `drag-coefficient-parabolic` (C_D,par), tastet aber das C_D der Solver-Polare ab (`drag-polar`, Umbenennung 02.10.2026). **Behoben mit dem Typ `polar` (#1181)** — die Bindung an C_D,par entfällt.
- `sink-rate`: die Form nennt C_D, gebunden ist C_D,par.
- `stall-wing-loading-limit`: die Form sagt C_L,max,clean, gebunden ist `max-lift-coefficient` (C_L,max,stall aus der Stall-Optimierung, braucht ein Flugzeug), der O12-Text sagt „aus dem gewählten Profil“ — drei verschiedene C_L,max.
- `glide-distance-from-ratio`: bindet `altitude` (Auswertehöhe der Atmosphäre) als Gleithöhe über Grund — eine Größe, zwei Bedeutungen.
- `cg-for-target-margin`, `static-margin`: hängen vom Intervall `x_NP` ab (A11: was von einer unscharfen Größe abhängt, ist unscharf), weder Eintrag noch Größe sagt es; `uncertainty` nicht gesetzt.

**Werte und Quellen**

- `gravity`: zwei Werte mit Quelle im Kanon (9,81 Scholz; 9,80665 CGPM, `weight-from-mass`). **Entschieden (Koordinator, 14.10.2026):** `default` 9,80665 m/s² (Normfallbeschleunigung, CGPM 1901 / U.S. Standard Atmosphere 1976) — der definierte Wert; Scholz' 9,81 ist seine Rundung, keine zweite Konstante (A5). `weight-from-mass` zitiert den gerundeten Wert.
- `limit-load-factor` („default 3.0“), `altitude` („defaults to 0 m“): Vorgabewerte ohne Quelle → kein `default`.
- `sea-level-air-density`: `default` 1,225 kg/m³ mit der Quelle aus `air-density-isa` (U.S. Standard Atmosphere 1976).

**Veraltete Texte**

- `minimum-drag-speed` („3 formulas“), `minimum-sink-speed` („2“), `zero-lift-drag-coefficient` („2“): die ⚠️-Hinweise sind veraltet, Produced by nennt je einen Erzeuger.
- `airplane-geometry`: der Text nennt „the flap factor from the flap type“; der Klappenfaktor ist gelöscht (`stall-speed`, 02.10.2026) und keine Ausgabe.
- `butterfly-approach`: verweist für die Klappenkonfigurationen auf „A3“; A3 ist die Genauigkeitsstufe.
- `drag-polar`, `thrust-at-airspeed-from-coefficient`: Prosa verlinkt gelöschte Einträge (`power-required-electrical`, `reynolds-scheduled-polar`, `mean-thrust-derate`).

**Rudergrößen als Winkel (Maintainer, 14.10.2026; Architekt):** Jedes Ruder ist ein Winkel in Grad, nie ein Bruchteil des Anschlags; Anschläge werden im Kanon nie referenziert. Umbenannt: `max-roll-rate` → `roll-rate`, `max-roll-rate-cruise-target` → `roll-rate-cruise-target`, `aileron-throw-fraction` → `aileron-deflection-required`; Größen `max-roll-rate-approach` → `roll-rate-approach`, `max-roll-rate-nondimensional` → `roll-rate-nondimensional-approach`, `max-roll-rate-cruise` → `roll-rate-cruise`; `aileron-throw-fraction-cruise`/`-approach` gelöscht, neu `aileron-deflection-required-cruise`/`-approach` (deg). Neue Eingabe `aileron-deflection` (ein symmetrischer Winkel ±δ_a, keine Vorgabe). Ziel über dem Maximum der Methode → Fehler `unsupported_configuration`/`target_above_method_maximum` mit maximaler Rollrate und ihrem δ_a, nie ein geklemmter Winkel. **D6 (Architekt, 14.10.2026):** keine Vorbedingung und kein Gültigkeitsbereich im Kanon — Werkzeuggrenzen-Warnungen gehören in die Solver-Adapter des Kerns; Lösungsweg je Welt (AeroBuildup: δ_a aufwärts suchen bis p(δ_a) nicht mehr steigt; AVL: linear, direkt gelöst); Methodenprämisse (AeroBuildup τ·δ ohne Ablösung, AVL linear, Sadraey §12.4.3 ≈ 20–25° als Bezugspunkt ohne Grenze) in allen drei Einträgen. Ältere Abschnitte dieses Dokuments (§9, §4/O1) und ANFORDERUNGEN.md nennen die alten Namen als Stand ihres Datums.

**Flugzeug ohne Querruder (Koordinator, 14.10.2026):** die Rollrechnungen (`roll-rate`, `roll-rate-cruise-target`, `aileron-deflection-required`) tragen `when: has_aileron` — wirksam als Querruder zählen Hinterkantenklappen mit `role` `aileron`, `flaperon` oder `elevon`; ohne sie sind die Rollgrößen `not_applicable`.

**Höhenruder und Butterfly als Winkel (Koordinator, 14.10.2026):** `mass-envelope` rechnet die Schwerpunktkanten bei den neuen Entwurfseingaben `elevator-deflection-up` / `-down` (deg, Vorzeichen wie `deflection_deg` im Geometrieformat, keine Vorgabe) statt „voller Ausschlag, wie gebaut“. `butterfly-approach` liest `crow-flap-deflection` / `crow-aileron-deflection` (deg, volle Krähe, keine Vorgabe); der Mischanteil s ∈ [0, 1] skaliert diese Winkel, nicht einen Anschlag; `butterfly-max-mix` bezieht sich auf sie. `has_flap_and_aileron` ist funktional definiert (Klappe: `flap`/`flaperon`; Querruder: `aileron`/`flaperon`/`elevon`). **Offen:** danach erfüllt ein Modell nur mit Flaperons die Bedingung — Krähe braucht aber Klappen unten und Querruder oben gleichzeitig an verschiedenen Flächen; ob Flaperons allein zählen, ist eine Fachfrage. **Entschieden (Koordinator, 14.10.2026, aus der Butterfly-Definition des Kanons):** nein — die Bedingung heißt jetzt `has_separate_flap_and_aileron`: mindestens eine als Klappe wirkende Fläche und mindestens eine **andere** als Querruder wirkende; Klappen unten und Querruder oben zugleich kann eine Fläche nicht.

**Klappenwirkung in AeroBuildup (Fachberatung D6, 14.10.2026):** AeroBuildup hat kein eigenes Klappenmodell, NeuralFoil sieht die ausgeschlagene Fläche nie: AeroSandbox rechnet das saubere Profil bei α_eff = α + τ·δ, τ = 1 − x_hinge^2,7514 (δ-unabhängiger Fit an eine XFoil-Studie), und multipliziert den Widerstand mit einem Faktor nach Hoerner, *Fluid Dynamic Drag* S. 13-13 Abb. 32 (`aerosandbox/geometry/airfoil/kulfan_airfoil.py:211-255` über `aero_buildup.py:784-801`, AeroSandbox 4.2.9 / NeuralFoil 0.3.2). Keine Klappenablösung; überschätzt die Wirkung bei großem δ, bis das saubere Profil abreißt; der δ-Bereich des τ-Fits ist unbekannt. Korrigiert in `airplane-configuration`, `roll-rate`, `roll-rate-cruise-target`, `aileron-deflection-required`, `butterfly-approach`, `mass-envelope`. ANFORDERUNGEN.md Z. 544–546 und 1007–1008 bleiben die Stellen, an denen die Grenze zuerst notiert wurde; sie nennen sie ein NeuralFoil-Klappenmodell, was der Code nicht bestätigt. In `butterfly-approach` entfällt dabei die Aussage „zuverlässig bis etwa 20–30°“ — dafür gibt der Code keinen Beleg.

**AVL ist linear in δ (Fachberatung D6, 14.10.2026):** `Avl/src/amake.f:1184-1187` („linearize about zero deflection“); die Anleitung nennt für die Rollrate nur −0,10 < pb/2V < 0,10 als praktische Grenze (`Avl/avl_doc.txt:121-141`). **Befund zum A11-Rollratenintervall:** der in den Rollrechnungen zitierte BRYAN-Wert AVL pb/2V = 0,276 liegt außerhalb der eigenen Grenze von AVL. Die Intervallentscheidung bleibt beim Maintainer, unverändert.

**Polaren und C_L,min (Maintainer, 14.10.2026, D4/Option A+B; Architekt):** Neues Ausgabefeld-Format: ein Ausgang darf in `produce` explizit `null` sein (die Implementierung gibt ihn zurück, die Anwendung legt ihn nicht offen); ein fehlender Ausgang bleibt ein Fehler. `stall-speed` veröffentlicht seinen α-Sweep als `polar-stall` (Typ `polar`, saubere Anwendung, V_S, n = 1, Solver-Widerstand); `stall-onset-detection` liest `polar-stall`. Start, Landung und Rücken geben `polar: null` und `alpha_s: null` (damit ist die Eskalation „Abrisswinkel in Start-/Landekonfiguration“ erledigt, Option b). Neue Anwendung `inverted` von `stall-speed` (`n_load` = −1, Quelle bestätigt (Koordinator, 14.10.2026): „definition of the load factor n = L/W (as stated in max-mass-structure); inverted level flight means L = −W“) erzeugt `inverted-max-lift-coefficient`; eine Größe für die Rücken-Abrissgeschwindigkeit gibt es nicht (`v_s: null`). **Der Formeleintrag `inverted-max-lift-coefficient` ist gelöscht** (wäre zweiter Erzeuger, A7/ADR 0022); die Größe bleibt. Was wohin wanderte: Vorbedingung `alpha_range_past_inverted_stall` → `stall-speed` (Parameter `cl_max`, `error`; das Format kennt keine Vorbedingungen je Anwendung, sie galt formal für alle vier — **entschieden (Koordinator, 14.10.2026, Option a):** neues optionales Feld `applications: [<id>, …]` an einer Vorbedingung, fehlend = alle; die Vorbedingung trägt `applications: [inverted]`, denn eine anderswo „trivial erfüllte“ Prüfung wäre eine Scheinprüfung); Klammerregel (Annahmen 1–3, „kein Wert bei Rand-Tal“) → Abschnitt „Inverted application“ in `stall-speed` (K32 gespiegelt); „Was ersetzt wurde“ (−0,8·C_L,max, keine Quelle, 14 CFR 23.337, Wölbungsabhängigkeit) → ebendort; Benennungs-Vorbedingung `cl_min_named_by_evaluation_condition` → als A2-Hinweis in den Text (keine Laufzeitprüfung), der Befund „Größenname ohne Auswertebedingung“ bleibt offen; der Satz „one sweep … two authorities“ → umformuliert: zwei Sweeps für zwei benannte Bedingungen sind keine zwei Autoritäten für eine Polare. Nicht übernommen: die Approval-Checkliste (Standardtext jedes Eintrags).

**Review, Runde 1 (14.10.2026):**
- `check_canon.py` prüft jetzt in jedem Eintrag auf YAML-1.1-Booleans, vergleicht jedes README-Beispiel mit dem Eintrag, verlangt einen Grund nach `# ESCALATED:`, lehnt ein `when`, das kein einzelner Begriff ist, und unbekannte `uncertainty`-Werte ab. **Bekannte Lücke, nicht hier behoben:** CI führt `check_canon.py` und `scripts/tests` bei reinen Kanon-Änderungen nicht aus (Pfadfilter in `.github/workflows/test.yml`: nur `app/**`, `cad_designer/**`, `pyproject.toml`, `poetry.lock`, `alembic/**`).
- Das README-Beispiel für `optimization` war veraltet (Butterfly ohne Krähenwinkel) — korrigiert; die neue Prüfung hätte es gefunden.
- Einheiten: `dimensionless` → `1` in 31 Größen (eine Schreibweise, README); Einheit einer `polar` je Spalte im README.
- `cruise-target-performance`: `given: [cruise-speed-target]` wie die Geschwister — der Eintrag selbst nennt das Ziel nicht optional, die Größe `cruise-speed-target` sagt „Optional.“; daraus gesetzt.
- `mass-envelope`: „Die beiden Fehler laufen in entgegengesetzte Richtungen“ als 🟡 INFERRED markiert — die Begründung stützte sich auf NeuralFoils Klappenverluste, die die Korrektur in #1181 zurücknahm; **offener Fachbefund**, nicht neu hergeleitet.
- `mass-envelope` liest die Intervallgröße `neutral-point` ohne eigene `uncertainty`-Kennzeichnung (wie `static-margin`, `cg-for-target-margin`; die Welten folgen den Wertekanten, der Kern behandelt es, die Kanonmarke fehlt). Neu deklariert: `m_current: aircraft-mass` (der Text nutzt die aktuelle Masse: „one point of it“, „front edge at the current mass“); die Masse als Sweep-Variable bleibt ungebunden.
- `takeoff-speed-margin-target`: Quelle jetzt „Sadraey §4.3.4: V_TO = 1.1–1.3 V_s (lower edge)“, Wert unverändert; Prosa in `speed-from-stall-margin` angeglichen.
- `flap-deflection-*`: die unbelegten Bereiche 10–20° / 30–45° gestrichen; nur Lennon 20° / 40° (Spaltklappe, 30 % Tiefe) zur Orientierung, keine Vorgabe.
- Prosa: `static-thrust-to-weight` (eingebettete Beziehungen statt „bound at V = 0“); „Superseded“ in `roll-rate` / `aileron-deflection-required` als „Decided … (supersedes the 2026-10-01 statement …)“; Sadraey §12.4.3 wörtlich nach der Fachberatung (Ablösung jenseits etwa 20–25°, Empfehlung |δ_A,max| ≤ 25°, Transport/GA, bei Modell-Re ungeprüft).

**Nachbedingungen (Architekt, 14.10.2026, Review-Befund 5):** neues Formelfeld `postconditions` (Form wie `preconditions`); eine Vorbedingung nennt einen Eingang (läuft vor dem Aufruf), eine Nachbedingung einen Ausgang (läuft danach, auch auf mit `null` geschriebenen Ausgängen). `stall-speed`: `cl_max_at_stall_reynolds_number` (alle Anwendungen) und `alpha_range_past_inverted_stall` (Parameter jetzt `polar`, nur `inverted`) sind Nachbedingungen; `rho_at_evaluation_altitude` bleibt Vorbedingung. Durchsicht aller Einträge: sonst liegt keine Vorbedingung auf einem Ausgang (`glide-distance-from-ratio` prüft den Eingang `e`). `cl_min_named_by_evaluation_condition` bleibt entfernt — durch die `inverted`-Anwendung bei ihrer eigenen Reynoldszahl strukturell erfüllt; der Befund zum Größennamen ohne Bedingung (A2) bleibt als Benennungsfrage. **Eskaliert:** `optimum_at_first_cl_peak` (und das Rücken-Gegenstück) — `stall-speed` nennt „the optimum must be the first C_L peak, checked against the sweep“ nur als Freigabeschritt, nicht je Auswertung. **Entschieden (Koordinator, 14.10.2026):** Nachbedingungen `optimum_at_first_cl_peak` (clean, takeoff, landing) und `optimum_at_first_cl_trough` (inverted), beide `error`. Grund: K32 (O3, 05.10.2026) legte das Verfahren fest — Abtastung bis zum ersten C_L-Gipfel als Schranke, IPOPT, ohne Lösung kein Wert —, und der BRYAN-Fall zeigt, dass IPOPT ohne aktive Schranke auf dem Ast nach dem Abriss landen kann; ohne Prüfung je Auswertung käme ein Wert vom falschen Ast still zurück (ADR 0020). Der Freigabesatz bleibt, ein Satz ergänzt.


**Review, Runde 2 (14.10.2026):** Die README-Beispielprüfung vergleicht jetzt alle maschinenlesbaren Schlüssel des Eintrags, nicht nur die gezeigten (B). Neues README-Beispiel `stall-speed` mit Vor- und Nachbedingungen, von der Prüfung abgedeckt (C). Ein `# ESCALATED:`-Kommentar öffnet nur die Lücken des Parameters, den sein Grund nennt. Die Übereinstimmung mit der from-Zeile zählt, was die Anwendungen tatsächlich binden; ein in jeder Anwendung überschriebener Vorgabewert zählt nicht mehr (kommt im Kanon derzeit nicht vor — es war nicht beabsichtigt).

**Review, Runde 2 — A/D (Architekt, 14.10.2026):** `embeds`-Einträge sind `<slug>` oder `<slug>.<application>` (bei mehreren Anwendungen Pflicht; die Anwendung wählt nur die Nachbedingungen). Neues Pflichtfeld `variables` neben `embeds`: was der Einbettende selbst löst oder abtastet. Eingangsregel statt „generische Betriebspunktgröße“: jede Eingangsgröße des Abschlusses ist eine Variable, ein Eingang des Einbettenden oder im Abschluss erzeugt. `mass-envelope` bettet `stall-speed.clean`, `.landing`, `.takeoff` ein (`.takeoff` bleibt: die Form wertet V_S,TO(m) für V_TO(m) aus), `variables: [aircraft-mass, flight-speed]`. **Abweichung von der Anweisung:** `load-factor` ist keine Variable — seit Runde 1 bindet `stall-speed` n = ±1 als Konstante, kein Eintrag im Abschluss liest `load-factor`, und die Prüfung „jede Variable wird im Abschluss gelesen“ würde ihn ablehnen. `angle-of-attack` liest im Abschluss niemand als Eingang, also nicht aufgenommen. Die sieben Antriebseinbettenden tragen `variables: [flight-speed]`; alle Abschlüsse schließen nach der neuen Regel.

**Lesart der Einbettung bestätigt (Architekt, 14.10.2026):** ein Eintrag `<slug>.<application>` bettet diese Anwendung so ein, wie sie geschrieben ist — ihre Bindungen (Größen und Konstanten) und ihre Prüfungen; ein bloßer Slug ist die einzige Anwendung. Die Eingangsregel gilt für die Größen, die die eingebetteten Anwendungen nach den Vorgaben binden; Konstanten werden nie neu gebunden. `load-factor` bleibt aus den Variablen von `mass-envelope`; `airplane_to` / `airplane_ldg` bleiben Eingänge (die Wertekanten der Größen, die `stall-speed.takeoff` / `.landing` binden). `check_canon.py` prüft die Regel je eingebetteter Anwendung.

**Butterfly-Grundkonfiguration (Maintainer, 15.10.2026, E2/Option C):** `s = 0` ist die Landekonfiguration; die Krähenwinkel sind absolute Endausschläge: δ_f(s) = δ_f,landing + s·(δ_f,crow − δ_f,landing), δ_a(s) = s·δ_a,crow. Die Anwendung `crow` bindet `airplane-landing` und liest `flap-deflection-landing`; V_app(s) wird mit V_S0(0) desselben Sweeps normiert — die Mischung aus Reiseflug- und Landekonfiguration entfällt, der Eingang `stall-speed-landing` damit auch.

**Delta-Review F2 (Architekt, 15.10.2026):** `butterfly-approach` trägt die Nachbedingung `optimum_at_first_cl_peak` auf `v_s0_curve` — bei jedem s geprüft, dieselbe Prüfung wie in `stall-speed` (K32), eine gemeinsame Implementierung. Kein `embeds`: eine Form, die das Problem einer anderen Formel unter einer selbst variierten Konfiguration neu löst, ist keine Einbettung (ARCHITECTURE §8.5).

**Delta-Review F5 (Architekt, 15.10.2026):** `variables` ohne `embeds` ist ein Fehler. `variables` gehört zu den Schlüsseln, die README-Beispiele vollständig wiedergeben müssen; neues Beispiel `mass-envelope` (Einbettung je Anwendung, Variablen, Eingänge mit `m_current` und `airplane_ldg`). Neue offene Warnung (lässt den Lauf nicht scheitern): eine Skalargröße mit Rolle `input`/`target` ohne Vorgabe, die der Abschluss über einen Eingang des Einbettenden bindet und die nicht in `variables` steht. Der reale Kanon erzeugt keine solche Warnung.

**Größenfeld `positive` (Architekt, 15.10.2026, 594b5988):** `positive: true` heißt „nach Definition echt größer null“ (Tatsache, keine Bewertung, A10), nur bei Rolle `input`/`target`; gesetzt bei `aircraft-mass`, `gravity`, `sea-level-air-density`, `limit-load-factor` (laut Definition ein positives Grenzlastvielfaches). **Die sechs offenen Fälle entschied der Koordinator (15.10.2026)** nach der Regel: markiert wird, wenn ein Wert ≤ 0 die Größe zu etwas anderem macht (kein Motor, keine Geschwindigkeit, keine Reserve) — markiert: `motor-efficiency`, `approach-/touchdown-/takeoff-speed-margin-target`, `stall-speed-target`, `cruise-speed-target`; nicht markiert: `flight-speed` (V = 0 ist der Standschub), `roll-rate-target-cruise/-approach` (0 ist ein gültiges, wenn auch triviales Ziel; das Vorzeichen folgt der Rollkonvention). `limit-load-factor` bleibt markiert (laut Definition positiv).


**S15 und D10 (Maintainer, 17.10.2026, #1174):** Neuer Typ und neue Eingangsgröße `components` (Dokument der eingebauten Komponenten: Motor, Akku, Propeller mit APC-Tabelle; keine Vorgabe); `airplane` ist nur noch Geometrie. `airplane-components`, `propeller-table-lookup` und `motor-propeller-equilibrium` lesen `components` statt `airplane` (letzteres nutzt keine Geometrie); die acht Einbettenden lesen zusätzlich `components`. D10: `has_separate_flap_and_aileron` = reine Klappe (`flap`) und querruderwirkende Fläche (`aileron`/`elevon`), Flaperons zählen nicht — „Man hat entweder Flaperons oder Ailerons und Flaps.“
