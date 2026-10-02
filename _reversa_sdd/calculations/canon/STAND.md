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
