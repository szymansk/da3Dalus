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

**Keine Tickets, bis der Rechenkanon steht.** Befunde werden im Kanon festgehalten, wo sie
die Rechnung binden — nicht in einer Fundliste und nicht als Backlog.

**Kein Skill und kein CI-Gate, bevor der Kanon stabil ist.** Sieben Nachschärfungen in drei
Pfaden; ein Skill hätte jede vorherige Fassung zementiert. Und ein Gate, das sich auf einen
Entwurf beruft, erbt dessen Instabilität.

**Reproduktion vor Bericht.** Jede gemeldete Verletzung wird selbst nachgerechnet, bevor
sie weitergegeben wird. Zweimal war die Meldung schärfer als beschrieben, einmal lag der
Prüfagent falsch.
