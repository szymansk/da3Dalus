---
title: "Anforderungen an das Rechenwerk"
subtitle: "Der Sollzustand — was gerechnet werden soll, wo und unter welchen Randbedingungen"
author: |
  | da3Dalus — Rechenkanon
  | in Arbeit — wird sukzessive befüllt
date: "20. August 2026"
lang: de
documentclass: scrartcl
classoption:
  - 11pt
  - DIV=11
  - parskip=half-
geometry:
  - a4paper
  - margin=2.3cm
mainfont: "STIX Two Text"
monofont: "Menlo"
monofontoptions:
  - Scale=0.78
colorlinks: true
linkcolor: akzent
urlcolor: akzent
toc: true
toc-depth: 3
numbersections: false
header-includes: |
  \usepackage{xcolor}
  \usepackage{amssymb}
  \usepackage{booktabs}
  \usepackage{longtable}
  \usepackage{microtype}
  \usepackage{graphicx}
  \definecolor{okgreen}{HTML}{1B7F3B}
  \definecolor{midamber}{HTML}{B4690E}
  \definecolor{badred}{HTML}{B02A21}
  \definecolor{neutral}{HTML}{8A8F98}
  \definecolor{akzent}{HTML}{1F4E79}
  \newcommand{\statusok}{\textcolor{okgreen}{$\bullet$}}
  \newcommand{\statusmid}{\textcolor{midamber}{$\bullet$}}
  \newcommand{\statusbad}{\textcolor{badred}{$\bullet$}}
  \newcommand{\statusna}{\textcolor{neutral}{$\circ$}}
  \newcommand{\statusyes}{\textcolor{okgreen}{$\checkmark$}}
  \newcommand{\statuswarn}{\textcolor{midamber}{\textbf{!}}}
  \setlength{\emergencystretch}{2em}
  \usepackage{sectsty}
  \allsectionsfont{\normalfont\sffamily\bfseries\color{akzent}}
---

# Anforderungen an das Rechenwerk — der Sollzustand

*Was gerechnet werden soll, an welcher Stelle des Ablaufs, mit welcher Formel, unter
welchen Randbedingungen. Nicht, was der Code heute tut.*

**Dieses Dokument wird sukzessive befüllt.** Was hier steht, ist entschieden; was fehlt,
fehlt sichtbar. Ein leeres Feld ist ein besserer Zustand als ein ausgedachtes.

---

## 0. Wie dieses Dokument zu lesen ist

### 0.1 Drei Ebenen, und wer welche besitzt

Der Sollzustand zerfällt in drei Ebenen. Jede hat **genau eine** Autorität — sonst
entsteht auf der Dokumentebene derselbe Duplikatschaden, den wir im Code beschreiben.

| Ebene | was sie festlegt | Autorität |
|---|---|---|
| **Größe** | Name, Symbol, Einheit, Rolle | `quantities/<name>.md` |
| **Formel** | kanonische Form, Quelle, Gültigkeit bei 0,5–15 kg, Dimensionsprobe | `formulas/<name>.md` |
| **Anwendung** | welche Bindung, unter welcher Bedingung sie existiert | im Formeleintrag, Abschnitt *Applications* |
| **Ablauf · Rechengraph · Verfahren** | **wann gerechnet wird, in welcher Reihenfolge, mit welchen Bindungen** | **dieses Dokument** |

Dieses Dokument wiederholt nichts, was der Katalog trägt. Wo es eine Formel braucht, nennt
es den Eintrag.

**Eine Ausnahme, und sie ist gewollt:** Im Rechengraphen steht die Formel **im Kasten**,
nicht nur ihr Name. Das verlangt die Freigaberegel — an einem Graphen aus bloßen Namen
sieht man nicht, ob alle Eingänge belegt sind. Kasten und Katalogeintrag müssen deshalb
übereinstimmen, und diese Übereinstimmung ist maschinell prüfbar: Formel aus dem Kasten
lesen, gegen den Eintrag halten. Ein Duplikat ist unschädlich, solange es geprüft wird —
gefährlich wird es erst, wenn es unbemerkt auseinanderläuft.

### 0.2 Statusworte

Jeder Eintrag trägt genau eines:

| | |
|---|---|
| **entschieden** | der Maintainer hat es festgelegt; ab hier ist es die Vorgabe |
| **offen** | steht aus — **mit der konkreten Frage**, nicht als Platzhalter |
| **freigegeben** | entschieden *und* der Katalogeintrag hat alle Freigabetore passiert |

Die Vertrauensmarker der Spezifikation (🟢/🟡/🔴) gelten hier **nicht**. Sie sagen, wie
sicher eine Aussage über den Code ist. Dieses Dokument macht keine Aussagen über den Code.

### 0.3 Notation

**Formeln und Größen werden in LaTeX gesetzt.** Das gilt für den Fließtext, für
abgesetzte Formeln und für die Kästen der Rechengraphen: `mermaid-cli` 11 rendert KaTeX in
Knotenbeschriftungen — nachgeprüft —, es gibt also keinen Grund, dort auf ASCII
auszuweichen. Ob GitHubs eigener mermaid-Renderer dasselbe tut, ist **nicht** nachgeprüft;
maßgeblich ist das PDF.

$$V_S = \sqrt{\frac{2\,m\,g}{\rho\,S_\mathrm{ref}\,C_{L,\max,\mathrm{stall}}}}$$

**Eine Grenze des Graphenrenderers:** mermaids KaTeX kennt `\overset` und `\stackrel`
nicht und verwirft sie **still** — samt Argument. Im Fließtext (xelatex) funktionieren sie,
im Kasten nicht; dort steht deshalb $\text{Probe: } \ldots\ ?$ statt $\overset{?}{=}$.
Wer eine Formel in einen Knoten setzt, sieht sich das Ergebnis an.

Vier Festlegungen, damit es einheitlich bleibt:

| | |
|---|---|
| **Mehrbuchstabige Indizes aufrecht** | $S_\mathrm{ref}$, $x_\mathrm{NP}$, $\rho_\mathrm{ISA}$ — sie sind Namen, keine Produkte von Variablen |
| **Operatoren aufrecht** | $\max$, $\min$, $\mathrm{d}y$ |
| **Bedingung im Index, nicht im Text** | $C_{L,\max,\mathrm{stall}}$ — die Auswertebedingung gehört an die Größe (A2) |
| **Größe ≠ Bezeichner** | $SM_\mathrm{target}$ ist die *Größe*; `sm_target` ist das *Feld*, das sie trägt. Mathe kursiv, Code in Schreibmaschine. |

Die letzte Zeile ist die wichtigste. Ein Datenbankfeld, ein API-Name und ein
Dateipfad sind keine Mathematik und werden nie als solche gesetzt; eine physikalische
Größe wird nie in Schreibmaschine gesetzt. Wo beide im selben Satz vorkommen, sieht man
dann sofort, wovon die Rede ist.

**Der Katalog wird bei Berührung umgestellt.** Seine Einträge tragen die kanonische Form
heute in einem einfachen Codeblock, weil `scripts/check_canon.py` sie dort ausliest und
die Dimensionsprobe darauf rechnet. Das bleibt vorerst so: 43 der 46 Formeln stehen ohnehin
auf `draft` und werden bei der Freigabe entlang der Pfade angefasst — dann bekommt jeder
Eintrag seine LaTeX-Form. Ein Umschreiben aller Einträge auf einmal würde den Prüfer
brechen, ohne dass ein einziger Eintrag dadurch näher an der Freigabe wäre.

### 0.4 Zwei Diagrammsprachen, und was in welche gehört

Ein Rechengraph und ein Aktivitätsdiagramm beantworten verschiedene Fragen. Werden sie in
ein Bild gelegt, beantwortet es keine von beiden: Ein Kasten ist dann mal eine Größe, mal
eine Handlung, ein Pfeil mal eine Abhängigkeit, mal eine Reihenfolge — und keine der
Prüfungen, für die wir die Graphen bauen, lässt sich noch darauf anwenden.

| | **Rechengraph** | **Aktivitätsdiagramm** (UML) |
|---|---|---|
| Frage | *was hängt wovon ab* | *was geschieht wann* |
| Zeit | zeitlos | geordnet |
| Knoten | Größen **und** Beziehungen, zweigeteilt | Aktionen |
| Kante | „ist Eingang von" · „erzeugt" | Kontrollfluss |
| Zyklus | eine **Eigenschaft** des Graphen | eine **Schleife** mit Abbruchbedingung |
| Verzweigung | gibt es nicht | Entscheidungsknoten mit Wächter |
| Nebenläufigkeit | zwei Zweige ohne gemeinsame Kante | Fork / Join |
| trägt | Invalidierung, Benennung, Formelfreigabe | Reihenfolge, Iterationssteuerung, Fehlerwege |

Die Naht zwischen beiden lässt sich in einem Satz sagen:

> **Der Rechengraph liefert eine Teilordnung. Das Aktivitätsdiagramm macht daraus eine
> Ausführung — und alles, was es dabei hinzufügt, ist eine Entscheidung.**

Das ist zugleich die Prüfregel. Was im Aktivitätsdiagramm steht und **nicht** aus den
Kanten des Rechengraphen folgt, muss jemand entschieden haben: die Reihenfolge zweier
unabhängiger Zweige, das Abbruchkriterium einer Schleife, der Weg im Fehlerfall. Steht es
da, ohne entschieden worden zu sein, ist es geraten.

Umgekehrt gilt: Ein Solveraufruf ist im Rechengraphen **keine Handlung**, sondern eine
Beziehung, die aus Eingängen Ausgänge macht — auf der `kind`-Achse ein `procedure`. Erst
*wann* er läuft und *wie oft* ist Aktivität.

### 0.5 Was ein Verfahren schuldet

Ein Gesetz (`law`) wird über Formel, Quelle und Maßstab freigegeben. Ein **Verfahren**
(`procedure`) schuldet vier Angaben — keine davon darf erfunden werden, beide Ursprünge
sind zitierbar:

1. **Welche Beziehung** es löst — das ist die Physik, und sie steht im Formelkatalog.
2. **Mit welcher Methode** — das ist Numerik, und sie hat eine eigene Quelle.
3. **Unter welchen Annahmen** die Methode gilt.
4. **Was es zurückgibt, wenn es nicht konvergiert.**

Punkt 4 ist kein Randfall: Ein Verfahren ohne erklärtes Verhalten bei Nichtkonvergenz
liefert im Fehlerfall eine Zahl, die aussieht wie ein Ergebnis (ADR 0020).

---

## 1. Der Ablauf

**Status: offen.** Das Gerüst unten sind die drei Schritte, die genannt wurden — mehr
nicht. Welche Schritte es wirklich gibt und wo ihre Grenzen liegen, ist die nächste
Festlegung.

```mermaid
stateDiagram-v2
  direction LR
  [*] --> Mission
  Mission: Mission wählen und füllen
  Mission --> Konstruktion
  Konstruktion --> Analyse
  Analyse --> Konstruktion: Aussage über ein Bauteil
  Analyse --> [*]
```

Der Ablauf trägt die **Entwurfszyklen** — analysieren, etwas ändern, neu analysieren. Sie
enden durch das Urteil des Konstrukteurs. Die **Rechenzyklen** (Fixpunkte) bleiben unten in
den Rechengraphen und enden durch ein Konvergenzkriterium. Diese Trennung ist der Grund,
warum es zwei Diagrammarten gibt und nicht eine.

### Was der Ablauf leisten soll

**Er wählt die Bindungen.** Dieselbe Formel, andere Klappenstellung, anderer Name des
Ergebnisses: $V_{S,\mathrm{clean}}$, $V_{S,\mathrm{launch}}$ und $V_{S,\mathrm{landing}}$
sind **eine** Formel mit drei Bindungen, nicht drei Formeln. Der Rechengraph zählt Formeln,
nicht Größen.

**Er macht Namen prüfbar.** Die Prozessstufe wählt die Bindung, die Bindung bestimmt den
Namen. Jeder benannte Ausgabewert muss sich auf ein Paar *(Formel, Bindung)* zurückführen
lassen. Ein Name, der das nicht kann, ist eine unerklärte Anwendung oder ein Duplikat.

**Er zeigt, was dirty wird** — siehe Anforderung A1.

### Offen

- Welche Prozessschritte gibt es wirklich, und wo verläuft die Grenze zwischen ihnen?
- Welche Schritte sind wiederholbar, welche nur einmal am Anfang?
- Welche Aussagen laufen aus der Analyse in die Konstruktion zurück?

---

## 2. Prozessschritte

### 2.1 Analyse — Stabilitätsreserve und Abrissgeschwindigkeit

**Status: entschieden** bis auf die beiden Verfahren in §3.2 und die offene Entscheidung O1.

**Zweck.** Aus Geometrie, Masse und Zielstabilität die beiden Größen ermitteln, an denen
der Entwurf zuerst scheitert: wo der Schwerpunkt liegen muss, und wie langsam das Modell
werden darf.

#### Eingaben dieses Schritts

| Größe | Art | Anmerkung |
|---|---|---|
| `airplane` | Eingabe | die Konstruktion; **Referenzgrößen und $\bar{c}$ folgen daraus** |
| $SM_\mathrm{target}$ | Entwurfswahl | die Mission schlägt vor, der Konstrukteur überschreibt |
| $m$ | Schätzung | der Komponentenbaum ist eine eigene Kette und liefert einen Kandidaten |
| $h$ | Schätzung | zerfällt in **bekannte** Platzhöhe und **geschätzte** Flughöhe $\leq 150\,\mathrm{m}$ |
| $V$ | Eingabe | die Fluggeschwindigkeit; $\alpha$ wird daraus gelöst |
| Ruderstellung | Eingabe | **neutral** — die Ableitungen sollen die des sauberen Flugzeugs sein |
| `model_size` | Eingabe | **`xxxlarge`**, siehe A3 |
| $g$ | phys. Konstante | keine Eingabe, keine Wahl — siehe A5 |

Sieben Positionen. Alles Weitere ist abgeleitet: $\rho$ aus der Höhe,
$C_{L,\max,\mathrm{stall}}$ aus dem Sweep, $x_\mathrm{CG}$ aus $SM_\mathrm{target}$, $W$ aus
$m$ und $g$.

#### Rechengraph — was wovon abhängt

Zweigeteilt: **Rechtecke sind Größen, abgerundete Kästen sind Beziehungen.** Eine Kante
heißt „ist Eingang von" oder „erzeugt", nie „danach". Es gibt keine Reihenfolge in diesem
Bild und keine Verzweigung — beides steht im Ablauf darunter.

Der Nutzen der Zweiteilung ist unmittelbar: Eine Größe mit **zwei** eingehenden
Beziehungen verletzt ADR 0022, und das sieht man jetzt, ohne etwas zu lesen.

```mermaid
flowchart TD
  classDef inp fill:#eef3f8,stroke:#5a7fa6,stroke-width:1.5px,color:#173a5e
  classDef est fill:#eef3f8,stroke:#5a7fa6,stroke-width:1.5px,stroke-dasharray:6 3,color:#173a5e
  classDef konst fill:#f0f0ee,stroke:#6b6b66,color:#3a3a36
  classDef qty fill:#ffffff,stroke:#8a8f98,color:#222
  classDef rel fill:#faf7f2,stroke:#b08b4f,color:#4a3410
  classDef out fill:#eaf5ee,stroke:#3d8a5a,stroke-width:1.5px,color:#14432a

  GEO[/"$$\text{airplane}$$"/]:::inp
  SMT[/"$$SM_\mathrm{target}$$"/]:::inp
  M[/"$$m \quad \text{Abflugmasse}$$"/]:::est
  H[/"$$h \quad \text{Platzhöhe} + \text{Flughöhe}$$"/]:::est
  V[/"$$V \quad \text{Fluggeschwindigkeit}$$"/]:::inp
  DEL[/"$$\text{Ruder neutral}$$"/]:::inp
  FID[/"$$\text{model size} = \text{xxxlarge}$$"/]:::inp
  G["$$g = 9{,}80665\ \mathrm{m/s^2}$$"]:::konst

  RMAC(["$$\bar{c} = \frac{2}{S}\int c(y)^2\,\mathrm{d}y$$"]):::rel
  RREF(["$$\text{Referenzgrößen aus der Geometrie}$$"]):::rel
  RISA(["$$\rho = \rho_\mathrm{ISA}(h)$$"]):::rel
  RW(["$$W = m\,g$$"]):::rel
  RAL(["$$\text{löse } L = W \text{ bei } V$$"]):::rel
  RAB1(["$$\text{AeroBuildup, ein Punkt}$$"]):::rel
  RAB2(["$$\text{AeroBuildup, } \alpha\text{-Sweep}$$"]):::rel
  RXCG(["$$x_\mathrm{CG} = x_\mathrm{NP} - SM_\mathrm{target}\,\bar{c}$$"]):::rel
  RSM(["$$SM = \frac{x_\mathrm{NP} - x_\mathrm{CG}}{\bar{c}}$$"]):::rel
  RVS(["$$V_S = \sqrt{\frac{2W}{\rho\,S_\mathrm{ref}\,C_{L,\max,\mathrm{stall}}}}$$"]):::rel
  RPR(["$$SM = -C_{m\alpha}/C_{L\alpha}\ ?$$"]):::rel

  CBAR["$$\bar{c}$$"]:::qty
  SREF["$$S_\mathrm{ref},\ b_\mathrm{ref}$$"]:::qty
  RHO["$$\rho$$"]:::qty
  W["$$W$$"]:::qty
  AL["$$\alpha$$"]:::qty
  XNP["$$x_\mathrm{NP}$$"]:::qty
  CMA["$$C_{m\alpha}$$"]:::qty
  CLA["$$C_{L\alpha}$$"]:::qty
  CLMAX["$$C_{L,\max,\mathrm{stall}}$$"]:::qty

  XCG["$$x_\mathrm{CG}$$"]:::out
  SM["$$SM$$"]:::out
  VS["$$V_S$$"]:::out
  PR["$$\text{Probe bestanden}$$"]:::out

  GEO --> RMAC
  RMAC --> CBAR
  GEO --> RREF
  RREF --> SREF
  H --> RISA
  RISA --> RHO
  M --> RW
  G --> RW
  RW --> W
  V --> RAL
  W --> RAL
  RHO --> RAL
  SREF --> RAL
  GEO --> RAL
  RAL --> AL
  GEO --> RAB1
  SREF --> RAB1
  DEL --> RAB1
  FID --> RAB1
  H --> RAB1
  V --> RAB1
  AL --> RAB1
  XCG --> RAB1
  RAB1 --> XNP
  RAB1 --> CMA
  RAB1 --> CLA
  GEO --> RAB2
  SREF --> RAB2
  DEL --> RAB2
  FID --> RAB2
  H --> RAB2
  VS --> RAB2
  RAB2 --> CLMAX
  XNP --> RXCG
  SMT --> RXCG
  CBAR --> RXCG
  RXCG --> XCG
  XNP --> RSM
  XCG --> RSM
  CBAR --> RSM
  RSM --> SM
  W --> RVS
  RHO --> RVS
  SREF --> RVS
  CLMAX --> RVS
  RVS --> VS
  SM --> RPR
  CMA --> RPR
  CLA --> RPR
  RPR --> PR

  linkStyle 31 stroke:#b02a21,stroke-width:3px
  linkStyle 32 stroke:#b02a21,stroke-width:3px
  linkStyle 44 stroke:#b02a21,stroke-width:3px
  linkStyle 45 stroke:#b02a21,stroke-width:3px
  linkStyle 22 stroke:#b4690e,stroke-width:2px,stroke-dasharray:5 4
  linkStyle 23 stroke:#b4690e,stroke-width:2px,stroke-dasharray:5 4
  linkStyle 33 stroke:#b4690e,stroke-width:2px,stroke-dasharray:5 4
  linkStyle 36 stroke:#b4690e,stroke-width:2px,stroke-dasharray:5 4
```

Schräge blaue Kästen sind Eingaben, **gestrichelt wo geschätzt** — die Form trägt die
Rolle, der Strich die Sicherheit. Grau: physikalische Konstante. Sandfarben abgerundet:
eine Beziehung. Weiß: eine gerechnete Größe. Grün: ein Ergebnis dieses Schritts.

#### Der Graph hat zwei Zyklen, und nur einer ist echt

Das sieht man erst, seit Größen und Beziehungen getrennt sind — im vermischten Bild war der
eine ein Pfeil und der andere eine Bemerkung.

**Rot: $V_S \to$ Sweep $\to C_{L,\max,\mathrm{stall}} \to$ Abrissformel $\to V_S$.** Ein
echter Fixpunkt. $C_{L,\max}$ gilt bei der Reynoldszahl, die aus $V_S$ folgt, und bei
Modellgrößen hängt es stark davon ab. Er braucht ein Verfahren (§3.2.1) und ein
Abbruchkriterium.

**Bernstein gestrichelt: $x_\mathrm{CG} \to$ Punktlauf $\to x_\mathrm{NP} \to$ CG-Formel
$\to x_\mathrm{CG}$.** Formal derselbe Kreis, praktisch keiner — nachgemessen wandert
$x_\mathrm{NP}$ über 150 mm Bezugsverschiebung um 0,17 mm. Die Abhängigkeit steht im Graphen,
weil sie besteht; sie ist numerisch vernachlässigbar, und das ist eine **Aussage über die
Physik**, keine Vereinfachung der Zeichnung.

Wichtig ist die Einschränkung: Für $x_\mathrm{NP}$ ist der Zyklus entartet, für
$C_{m\alpha}$ **nicht** — dessen Vorzeichen wechselt genau bei
$\mathbf{x}_\mathrm{ref} = x_\mathrm{NP}$. $C_{m\alpha}$ speist nur die Probe, also hängt
genau die Probe am konvergierten $x_\mathrm{CG}$ und sonst nichts.

#### Rechnungen dieses Schritts

| Knoten | Art | Katalogeintrag |
|---|---|---|
| $\bar{c} = \frac{2}{S}\int c(y)^2\,\mathrm{d}y$ | law | **fehlt** — nur `quantities/mean-aerodynamic-chord.md` |
| $S_\mathrm{ref},\ b_\mathrm{ref}$ | Geometrie | `quantities/wing-reference-area.md` · `quantities/wing-span.md` |
| $\rho = \rho_\mathrm{ISA}(h)$ | law | `formulas/air-density-isa.md` — **freigegeben** |
| $W = m\,g$ | law | `formulas/weight-from-mass.md` — **freigegeben** |
| $\alpha$ aus $L = W$ bei $V$ | **procedure** | §3.2.2 — Beziehung entschieden, drei Angaben offen |
| AeroBuildup, ein Punkt | Solveraufruf | $\mathbf{x}_\mathrm{ref} = x_\mathrm{CG}$; liefert $x_\mathrm{NP}$, $C_{m\alpha}$, $C_{L\alpha}$ |
| AeroBuildup, $\alpha$-Sweep | Solveraufruf | gebunden an $V_S$; liefert $C_{L,\max,\mathrm{stall}}$ |
| $x_\mathrm{CG} = x_\mathrm{NP} - SM_\mathrm{target}\,\bar{c}$ | law | **fehlt** — ADR 0011 |
| $SM = (x_\mathrm{NP} - x_\mathrm{CG})/\bar{c}$ | law | **fehlt** |
| Probe $SM \overset{?}{=} -C_{m\alpha}/C_{L\alpha}$ | Probe | **fehlt** — zwei Wege zu einer Größe sind ein *Test*, keine zweite Wahrheit |
| $V_S = \sqrt{2W/(\rho\,S_\mathrm{ref}\,C_{L,\max,\mathrm{stall}})}$ | law | `formulas/stall-speed.md` — **freigegeben** |

Der Stabilitätsteil des Katalogs existiert noch nicht: weder `static-margin` noch
`neutral-point`, `centre-of-gravity` oder `pitching-moment-slope` haben einen Eintrag. Das
ist die nächste Katalogarbeit.

#### Ausgaben

$x_\mathrm{CG}$ · $SM$ · $V_S$ · das Ergebnis der Probe.

#### Ablauf dieses Schritts — was wann geschieht

Alles hier folgt aus den Kanten oben: die Teilordnung, die Nebenläufigkeit der beiden
Zweige, die Schleife. **Was das Diagramm hinzufügt, steht unter „Offen".**

```mermaid
stateDiagram-v2
  direction TB
  state teilen <<fork>>
  state konvergiert <<choice>>
  state vereinen <<join>>

  [*] --> Geometrie
  Geometrie: Geometrie auswerten
  Geometrie --> Umgebung
  Umgebung: Atmosphäre und Gewicht bestimmen
  Umgebung --> teilen

  teilen --> Horizontalflug
  Horizontalflug: Horizontalflug lösen
  Horizontalflug --> Stabilitaet
  Stabilitaet: Stabilitätslauf um den Schwerpunkt
  Stabilitaet --> vereinen

  teilen --> Abriss
  Abriss: Sweep, daraus die Abrissgeschwindigkeit
  Abriss --> konvergiert
  konvergiert --> Abriss: noch nicht konvergiert
  konvergiert --> vereinen: konvergiert

  vereinen --> Probe
  Probe: Probe rechnen
  Probe --> [*]
```

Der **Fork** ist keine Entwurfsentscheidung, sondern eine Ablesung: Der Abrisszweig braucht
$W$, $\rho$ und $S_\mathrm{ref}$, aber weder $\alpha$ noch $x_\mathrm{CG}$. Die beiden
Zweige teilen keine Kante und sind deshalb unabhängig — im vermischten Bild war das nicht
zu sehen.

#### Offen an diesem Ablauf

Das sind genau die Stellen, an denen das Aktivitätsdiagramm über den Rechengraphen
hinausgeht:

| | |
|---|---|
| **Abbruch der Schleife** | Woran wird Konvergenz gemessen, mit welcher Toleranz, und was geschieht nach $N$ erfolglosen Durchgängen? → O2 |
| **Fehlerweg** | Was, wenn der Horizontalflug keine Lösung hat — oberhalb des Abrisses gibt es kein $\alpha$ mit $L = W$? → O3 |
| **Ausgang bei nicht bestandener Probe** | Ist das ein Ergebnis mit Warnung oder ein Abbruch? |
| **Startwert** | Mit welchem $V_S$ läuft der erste Sweep? |

### 2.2 — noch nicht aufgenommen

---

## 3. Formeln und Verfahren

### 3.1 Formeln

Der Katalog führt **46 Formeln und 65 Größen**; freigegeben sind bisher drei Formeln —
`air-density-isa`, `stall-speed`, `weight-from-mass`, also genau die Gesetze aus §2.1.
Die übrigen stehen auf `draft`, weil sie aus der Bestandsaufnahme stammen und die Freigabe
entlang der Pfade läuft, nicht Eintrag für Eintrag.

Dieses Dokument nennt Formeln nur dort, wo ein Prozessschritt sie verwendet.

### 3.2 Verfahren

Verfahren haben bisher **keinen** Platz im Katalog — sie stehen hier, bis genug davon
zusammenkommen, um `procedures/` zu rechtfertigen.

#### 3.2.1 Fixpunkt $V_S \leftrightarrow C_{L,\max,\mathrm{stall}}$

**Status: offen** — die Beziehung steht, die Methode nicht.

| | |
|---|---|
| **Beziehung** | ✅ entschieden. $V_S = \sqrt{2W/(\rho\,S_\mathrm{ref}\,C_{L,\max})}$ mit $C_{L,\max}$ ausgewertet bei $Re(V_S)$. Bei Modell-Reynoldszahlen ist $C_{L,\max}$ geschwindigkeitsabhängig, also ist die Gleichung **implizit**. |
| **Methode** | ⚪ offen. Fixpunktiteration, Sekante, Newton, oder eine feste Zahl von Durchgängen? |
| **Annahmen** | ⚪ offen. Monotonie von $C_{L,\max}(Re)$ im Modellbereich? Startwert? |
| **Nichtkonvergenz** | ⚪ offen. Was wird zurückgegeben — und mit welcher `DesignWarning`? |
| **Toleranz** | ⚪ offen. Woran wird Konvergenz gemessen: an $V_S$ oder an $C_{L,\max}$, absolut oder relativ? |

**Warum das Verfahren nötig ist, ist gemessen** — Flotte, 26 Flugzeuge: Median **+2,9 %**,
schlimmstenfalls **+33,2 %**, **jede** Abweichung in dieselbe Richtung. Die gemeldete
Abrissgeschwindigkeit ist immer die zu niedrige. Vorbedingung dokumentiert in
`formulas/stall-speed.md`, Bindung `cl_max`.

#### 3.2.2 Anstellwinkel aus $L = W$

**Status: offen** — die Beziehung steht, die Methode nicht.

| | |
|---|---|
| **Beziehung** | ✅ entschieden. Zu vorgegebenem $V$ den Anstellwinkel $\alpha$ finden, für den der Auftrieb das Gewicht trägt. |
| **Methode** | ⚪ offen. Eindimensionale Nullstelle — welche? |
| **Annahmen** | ⚠️ eine steht fest und wird leicht übersehen: **$L = W$ gilt nur im stationären Horizontalflug.** Im Steigflug, in der Kurve und beim Handstart ist $L = n\,W$. Der gelieferte Anstellwinkel — und damit alle Ableitungen — gelten für den geradeaus fliegenden Zustand. |
| **Nichtkonvergenz** | ⚪ offen. Der Fall existiert real: Oberhalb des Abrisses gibt es **kein** $\alpha$, das $L = W$ erfüllt. Was dann? |

---

## 4. Querschnittliche Anforderungen

Sie gelten für **jeden** Prozessschritt und werden nicht pro Schritt wiederholt.

### A1 — Invalidierung ist eine Traversierung, keine gepflegte Regel

**Status: entschieden.**

Was nach einer Änderung ungültig wird, ist die **transitive Hülle stromabwärts** im
Rechengraphen. Eine getrennt geführte Invalidierungsliste ist konstruktionsbedingt ein
Duplikat der Kanten — und Duplikate laufen auseinander.

Der Graph liefert zwei Dinge, die eine Liste nicht hat:

- **Granularität** — nicht alles wird ungültig, sondern das Erreichbare.
- **Reihenfolge** — topologisch, mit den Fixpunkten als markierten Zyklen.

Zwei Fehlerarten, die er verhindert: **Unterinvalidierung** (eine angezeigte Zahl passt
nicht mehr zur Geometrie — still und falsch) und **Überinvalidierung** (alles rechnet neu,
und die Anwender gewöhnen sich ab, auf den Zustand zu achten).

Am Graphen aus §2.1 sieht man, warum das keine Formsache ist:

| Änderung | wird ungültig |
|---|---|
| $h$ | $\rho$, $\alpha$, beide Solverläufe, und alles danach — **fast der ganze Schritt** |
| $V$ | $\alpha$, der Punktlauf, $x_\mathrm{NP}$, $C_{m\alpha}$, $C_{L\alpha}$, $x_\mathrm{CG}$, $SM$, die Probe — **$V_S$ aber nicht** |

Dass die Fluggeschwindigkeit die Abrissgeschwindigkeit *nicht* ungültig macht, folgt aus
den Kanten: $V_S$ hängt an $W$, $\rho$, $S_\mathrm{ref}$ und $C_{L,\max,\mathrm{stall}}$,
und der Sweep hängt an $V_S$ selbst, nicht an $V$. Genau solche Aussagen bekommt eine
handgepflegte Liste falsch.

### A2 — Benennung

**Status: entschieden.**

Schema `<größe>_<konfiguration>_<einheit>`, ausgeschrieben, keine Normkürzel.

> **Eine reynoldsabhängige Größe trägt die Bedingung, bei der sie ermittelt wurde, im
> Namen.** $C_{L,\max,\mathrm{stall}}$, nicht $C_{L,\max}$.

Die Regel ist das Gegenstück zur Vorbedingung: Was die Vorbedingung fordert, macht der Name
sichtbar. Sie hätte den Reynolds-Fehler allein aufgedeckt — heute wird das Maximum über das
ganze Geschwindigkeitsgitter gebildet, also $C_{L,\max,v_{\max}}$, und dort eingesetzt, wo
$C_{L,\max,\mathrm{stall}}$ stehen müsste. Unter zwei Namen fällt das beim Lesen auf, unter
einem nicht.

### A3 — Eine erklärte Genauigkeitsstufe je freigegebener Größe

**Status: entschieden — `xxxlarge` für den Analysepfad.**

`model_size` folgt nicht aus dem Flugzeug; es ist die Netzgröße von NeuralFoil, also ein
Regler zwischen Genauigkeit und Rechenzeit. Gemessen an einem SD7037 im Modellbereich:
`xxsmall` liefert bei $Re = 50\,000$ einen um **14–19 % zu niedrigen** $C_{L,\max}$, und
zwar dort, wo die laminare Ablöseblase sitzt. Ab `small` sind sich alle Stufen beim
Auftriebsbeiwert einig; die **Analysekonfidenz** trennt sie, und sie steigt mit der Größe.
`xxxlarge` erreicht 0,961 bei $Re = 100\,000$ für 5 ms.

> Nicht überall die höchste Stufe — aber **eine, die dasteht.** Sonst hängt eine
> freigegebene Zahl davon ab, über welchen Endpunkt man sie geholt hat.

### A4 — Einheiten

**Status: entschieden.**

Jede Größe trägt ihre Einheit im Katalogeintrag. Jede kanonische Formel muss die
Dimensionsprobe bestehen — mit **Längenmaßstab** (mm gegen m) und getrenntem Winkelfach,
weil beides in diesem Projekt real auseinanderläuft. Werkzeug: `scripts/check_canon.py`.

### A5 — Physikalische Konstanten genau einmal

**Status: entschieden.**

Bei einer Eingabe lautet die Freigabefrage *„ist der Wert richtig gewählt"*. Bei einer
physikalischen Konstante lautet sie **„ist sie genau einmal deklariert"** — es gibt keinen
Ermessensspielraum, also auch keine Diskussion über den Wert, nur über die Anzahl der
Stellen. Im Register steht $g$ **elfmal, in zwei verschiedenen Werten**.

Gezeichnet wird eine Konstante nur, wenn sie in einer kanonischen Formel vorkommt. Steckt
sie in einem zitierten Standard — Gaskonstante und Temperaturgradient in
$\rho_\mathrm{ISA}(h)$ —, gehört sie in die Quelle des Gesetzes und nicht in den Graphen.

### A6 — Keine stillen Ersatzwerte

**Status: entschieden (ADR 0020).**

Der Sollzustand hat weiterhin Schätzungen, und er hat sie absichtlich. Was er nicht hat,
sind **stille** Schätzungen. Jede Ersetzung, Klemmung, Wiederholung und Kürzung meldet eine
`DesignWarning`, deren `severity` sagt, ob es fachliche Praxis oder ein Defekt ist. Ein
Restanteil für alles, was man nicht einzeln wiegt, ist eine **erklärte Größe** — ein Loch in
der Summe ist unsichtbar, ein Restanteil nicht.

### A7 — Eine Autorität je nutzersichtbarer Größe

**Status: entschieden (ADR 0022).**

Zu jeder Größe, die ein Anwender sieht, gibt es genau **einen** Erzeuger. Wo zwei Wege zu
derselben Größe führen, ist der zweite eine **Probe** und kein zweiter Erzeuger — so wie
der Ableitungsweg zur Stabilitätsreserve in §2.1.

---

## 5. Offene Entscheidungen

| Nr | Frage | blockiert |
|---|---|---|
| **O1** | Gehört der **Korrekturzweig** — Flügelversatz, Leitwerksskalierung — überhaupt in den Rechengraphen? Fällt er weg, verschwinden $a_{VH}$, beide Empfindlichkeiten und die $5\,\bar{c}$-Klemme mit ihm. | Abschluss von §2.1 |
| **O2** | Die **drei fehlenden Angaben** zum Fixpunkt $V_S \leftrightarrow C_{L,\max,\mathrm{stall}}$. | Freigabe von `stall-speed` als Anwendung |
| **O3** | Die **drei fehlenden Angaben** zum Anstellwinkelverfahren, insbesondere das Verhalten oberhalb des Abrisses. | Freigabe von §2.1 |
| **O4** | Welche **Prozessschritte** es wirklich gibt und wo ihre Grenzen liegen. | §1, und damit die Struktur aller weiteren Schritte |
| **O5** | Welches **Atmosphärenmodell** kanonisch ist. `air-density-isa` ist freigegeben, aber die Implementierung kennt mehrere Verfahren, und **kein einziger** der 16 Aufrufer wählt eines. | Eindeutigkeit von $\rho$ |
| **O6** | Wie weit der **ASB-Sweep** Eingaben ersetzt. Der Solver kann über nahezu jeden Parameter fahren; jeder, den er sinnvoll durchfährt, ist einer, den niemand raten muss. | Umfang von Ebene 0 |

---

## Arbeitsregeln

**Keine Tickets, bis der Kanon steht.** Befunde werden dort festgehalten, wo sie die
Rechnung binden.

**Der Sollzustand wird erfragt, nicht aus dem Code abgeleitet.** Der Code ist die Quelle
für den Ist-Zustand. Für diesen hier ist es der Maintainer.

**Reproduktion vor Behauptung.** Jede Zahl in diesem Dokument ist nachgerechnet; wo sie es
nicht ist, steht es dabei.
