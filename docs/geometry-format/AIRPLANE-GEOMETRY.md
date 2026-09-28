# Das Geometrieformat — Rumpf und Flächen

*Wie ein Flugzeug in diesem System beschrieben wird, und wie die Parameter für eine
Konstruktion zu lesen sind.*

Begleitdatei: [`airplane-geometry.schema.json`](./airplane-geometry.schema.json) —
JSON Schema (Draft 2020-12), maschinell prüfbar.

---

## 0. Was hier steht und was nicht

Dieses Dokument beschreibt **das Datenformat**: welche Felder es gibt, in welcher Einheit
sie stehen, und wie man daraus Geometrie erzeugt.

Die **Rahmenmathematik der Flächen** ist bereits an drei Stellen belegt, und ich wiederhole
sie hier nicht, sondern verweise:

| | |
|---|---|
| `docs/AerosandboxWingXSecFrame.adoc` | die Rahmentransformation je Rippe, vollständig hergeleitet |
| `docs/WingConfigRoundtripProof.adoc` | der formale Beweis, dass Hin- und Rückweg exakt sind |
| `docs/WingConfiguration.adoc` | die Segmentkette, Holme, Rudergeometrie im Detail |

Neu an diesem Dokument ist dreierlei: eine **maschinenlesbare** Fassung des Formats, die
Beschreibung des **Rumpfs** (die es bisher nirgends gab), und die **Einheitentabelle**, weil
die Einheiten nicht einheitlich sind und das die häufigste Fehlerquelle ist.

---

## 1. Koordinatensystem

Rechtshändig, der Konvention von AeroSandbox folgend:

| Achse | Richtung | wächst nach |
|---|---|---|
| $x$ | Längsachse | **hinten** (stromab) |
| $y$ | Querachse | **steuerbord** (rechte Flächenhälfte) |
| $z$ | Hochachse | **oben** |

Daraus folgt unmittelbar: Pfeilung ist ein positiver $x$-Zuwachs, V-Form ist eine Drehung
um $x$, Schränkung ist eine Drehung um $y$, und eine positive Schränkung hebt die Nase des
Profils.

Der Bezugspunkt `xyz_ref` ist der Momentenbezugspunkt, im Regelfall der Schwerpunkt.
**Er ist nicht dekorativ:** Der Neutralpunkt ist von ihm unabhängig, das Nickmoment
$C_{m\alpha}$ dagegen nicht — es wechselt das Vorzeichen genau bei
$\mathbf{x}_\mathrm{ref} = x_\mathrm{NP}$.

---

## 2. Einheiten — die Tabelle, die man gelesen haben muss

Die Grundregel lautet **Meter und Grad**. Sie hat echte Ausnahmen, und die sind nicht
willkürlich verteilt, sondern folgen der Herkunft des Feldes: Was aus der Aerodynamik
kommt, ist metrisch; was aus dem Bauteilkatalog kommt, ist in Millimetern.

| Feldgruppe | Einheit | Anmerkung |
|---|---|---|
| `xyz_le`, `chord`, `xyz`, `a`, `b`, `xyz_ref` | **m** | die eigentliche Geometrie |
| `twist`, `dihedral`, alle `*_deflection_deg` | **Grad** | |
| `spare_*` (Maße, Länge, Start, Ursprung) | **m** in der API | in der **Datenbank mm**; `wing_service` rechnet beim Lesen und Schreiben um |
| `spare_vector` | — | Einheitsvektor, **dimensionslos**, wird nie skaliert |
| `hinge_spacing`, `side_spacing_root`, `side_spacing_tip` | **mm** | am Ruder, **nicht** umgerechnet |
| `turbulator.height_mm` | **mm** | trägt die Einheit im Namen |
| alle Felder von `servo` | **mm** | Katalogmaße eines Bauteils |
| `rel_chord_*`, `*_position_factor`, `position_root/tip`, `hinge_point` | — | dimensionslose Anteile |
| `n` (Superellipsenexponent) | — | dimensionslos |

Der `units`-Block am Flügel meldet `geometry_length: "m"`, `detail_length: "m"`,
`angle: "deg"`. **Er deckt die Geometrie und die Holme ab, nicht das Ruder** — die drei
Millimeterfelder oben fallen nicht darunter. Das ist keine Ungenauigkeit des Blocks: Seine
eigene Beschreibung nennt ausdrücklich nur die Holmfelder.

> **Die teuerste Verwechslung** ist der Faktor 1000 bei den Holmen. Ein Holm, dessen
> Stützmaß als `4.42` durch das System läuft, ist 4,42 **mm** in der Datenbank und
> 0,00442 **m** in der API-Antwort. Wer den Konverter umgeht und direkt am Modell liest,
> bekommt Millimeter und muss es wissen.

---

## 3. Das Flugzeugdokument

```
name            string
total_mass_kg   number | null
xyz_ref         [x, y, z]                Momentenbezugspunkt, m
wings           { "<Name>": Wing }       jede auftrieberzeugende Fläche
fuselages       { "<Name>": Fuselage }   jeder Körper
```

Flächen und Rümpfe sind **Abbildungen über den Namen**, keine Listen — der Name ist der
Schlüssel, und die Einfügereihenfolge bleibt erhalten. Unter `wings` steht jede tragende
Fläche: Tragfläche, Höhen- und Seitenleitwerk, Canard. Unter `fuselages` steht nicht nur
der Rumpf, sondern jeder Drehkörper — Gondel, Radverkleidung, Haube.

---

## 4. Flächen

### 4.1 Rippen und Segmente

Eine Fläche ist eine geordnete Kette von **Querschnitten** (`x_secs`, hier: Rippen), von
der Wurzel nach außen. $N$ Rippen bilden $N-1$ **Segmente**.

Die wichtigste Leseregel des ganzen Formats:

> **Eine Rippe trägt die Detailangaben des Segments, das an ihr beginnt und nach außen
> läuft** — nicht des Segments, das an ihr endet.

Also gehören `x_sec_type`, `tip_type`, `number_interpolation_points`, `spare_list`,
`trailing_edge_device` und `turbulator` jeweils zum **äußeren** Nachbarsegment. Die
**letzte** Rippe ist ein reiner Abschluss und darf keines dieser Felder tragen; das prüft
`AsbWingSchema.validate_last_xsec_has_no_segment_details` und weist es sonst ab.

### 4.2 Schränkung ist kumulativ, V-Form ist ein Zuwachs

Das ist die Asymmetrie, an der man sich schneidet, wenn man sie nicht kennt:

| Feld | Bedeutung an Rippe $k$ |
|---|---|
| `twist` | **absolute** Schränkung gegen die $x$-Achse |
| `dihedral` | **Zuwachs** der V-Form an genau dieser Rippe — außer an der Wurzelrippe, wo er der absolute Anfangswinkel ist |

Die kumulative V-Form ist also $\gamma_k = \sum_{i \le k} \texttt{dihedral}_i$, die
kumulative Schränkung dagegen steht direkt da.

Warum `dihedral` überhaupt gespeichert wird, obwohl man es aus den Positionen ausrechnen
könnte: Die **Drehung der Endrippe verschiebt keine weiter außen liegende Station** und
hinterlässt deshalb keine Spur in `xyz_le`. Ohne das Feld ginge sie beim Rundlauf verloren
(gh-951). Bei Altbeständen ist es `null`, dann gilt der aus der Geometrie abgeleitete Wert.

### 4.3 Von den Stationen zur Konstruktionskette

Konstruiert wird nicht aus absoluten Stationen, sondern aus einer **relativen Kette** je
Segment: Länge, Pfeilung, V-Form-Zuwachs, Einstellwinkel-Zuwachs. Die Umrechnung ist
geschlossen.

**Vorwärts** — aus der Kette die Positionen. Mit $\gamma$ als laufender V-Form und
$\theta$ als laufender Schränkung, beide an der Wurzel beginnend:

$$\mathbf{p}_{k+1} = \mathbf{p}_k + R_x(\gamma_k)\begin{pmatrix}\mathrm{sweep}_k\\[2pt] \mathrm{length}_k\\[2pt] 0\end{pmatrix}$$

$$\gamma_{k+1} = \gamma_k + \mathrm{dihedral}_{k}^{\mathrm{tip}}, \qquad
\theta_{k+1} = \theta_k + \mathrm{incidence}_{k}^{\mathrm{tip}}$$

und der Rahmen der Rippe $k$ ist

$$H_k = T(\mathbf{n})\; T(\mathbf{p}_k)\; R_x(\gamma_k)\; R_y(\theta_k)$$

mit $\mathbf{n}$ als Nasenpunkt der Fläche.

**Rückwärts** — aus den Positionen die Kette. Mit $\Delta_k = \mathbf{xyz\_le}_{k+1} - \mathbf{xyz\_le}_k$:

$$\mathrm{sweep}_k = \Delta_{k,x}, \qquad
\mathrm{length}_k = \sqrt{\Delta_{k,y}^2 + \Delta_{k,z}^2}, \qquad
\gamma_k = \operatorname{atan2}(\Delta_{k,z},\, \Delta_{k,y})$$

Der Zuwachs folgt durch Differenzbildung: $\mathrm{dihedral}_k = \gamma_k - \gamma_{k-1}$
und $\mathrm{incidence}_k = \mathrm{twist}_k - \mathrm{twist}_{k-1}$.

**Die Eigenschaft, die das alles trägt: Die Schränkung geht nicht in die Positionen ein.**
Die Positionskette benutzt ausschließlich $R_x(\gamma)$; $R_y(\theta)$ dreht nur das Profil
in seiner Ebene. Deshalb ist die V-Form aus den Positionen eindeutig rückgewinnbar, ohne
von der Schränkung verunreinigt zu sein — und deshalb ist die Umkehrung oben schlichte
Arithmetik statt einer Matrixzerlegung. Der Beweis steht in
`docs/WingConfigRoundtripProof.adoc`.

Die Pfeilung darf wahlweise als **Strecke** oder als **Winkel** angegeben werden; die
Kette rechnet dann $\mathrm{sweep} = \mathrm{length}\cdot\tan(\text{Winkel})$.

### 4.4 Das Profil

`airfoil` verweist auf eine Selig-`.dat`-Datei, als Pfad im Repository oder als URL. Die
Sehne kommt **nicht** aus der Datei, sondern aus `chord`; die Profildatei liefert die
normierte Kontur, die damit skaliert wird. `number_interpolation_points` steuert, wie viele
Zwischenprofile beim Loften eingesetzt werden — hochsetzen, wo ein Segment stark schränkt
oder zuspitzt. Das kostet Rechenzeit in der CAD-Erzeugung, nicht Genauigkeit in der
Analyse.

---

## 5. Holme

Ein Holm wird über seine **Achse** definiert: `spare_origin` als Startpunkt und
`spare_vector` als Einheitsrichtung. Beide werden im Regelfall **gelöst, nicht eingegeben**
— aus `spare_position_factor` (Lage in der Sehne) und dem Modus.

Der Ursprung liegt auf der **Skelettlinie** an der gewünschten Sehnenposition, nicht auf der
Profiloberfläche: Er entsteht aus dem Ebenenursprung plus Sehnenanteil in $x$-Richtung plus
der dortigen Wölbungshöhe in $z$-Richtung.

Die Modi unterscheiden sich darin, **was an einem Knick geschieht** — und das entscheidet,
ob der Holm ein einziges gekauftes Rohr sein kann:

| Modus | Achse | |
|---|---|---|
| `standard` | Wurzel zu Spitze **dieses** Segments | jedes Segment hat seinen eigenen Holm |
| `standard_backward` | Wurzel des **ersten** zugehörigen Segments zur Spitze dieses Segments | **ein durchgehender gerader Holm** über mehrere Segmente |
| `orthogonal_backward` | wie oben, aber die Achse wird in der Wurzelebene rechtwinklig gestellt | Holm steht senkrecht in der Wurzelrippe — wichtig für einen steckbaren Übergang |
| `follow` | übernimmt die Achse des Holms **gleichen Index** aus dem Nachbarsegment | die Fortsetzung eines `*_backward`-Holms |
| `normal` | entlang der Segment-$y$-Achse, oder explizit vorgegeben | der einzige Modus, in dem `spare_vector` eine **Eingabe** ist |

Zwei Dinge, die man daraus wissen muss. Erstens: **Der Listenindex trägt Bedeutung.** Ein
`follow`- oder `*_backward`-Holm bezieht sich auf den Holm mit **demselben Index** im
Nachbarsegment — die Reihenfolge in `spare_list` ist also Teil der Konstruktion, nicht bloß
Darstellung. Zweitens: Bei `normal` ist `spare_origin` ein **Versatz** gegenüber dem
Segmentursprung, in allen anderen Modi ein absoluter Punkt.

Fehlt `spare_position_factor`, setzt die Kette beim Lösen 0,25 ein.

---

## 6. Ruder, Turbulator, Servo

### Ruder

Zwei Darstellungen desselben Gegenstands, und sie haben verschiedene Aufgaben:

- `trailing_edge_device` — die **Konstruktion**: Scharnierlage, Spalte, Anschläge,
  Scharniertyp, Servoeinbau.
- `control_surface` — die **Aerodynamik**: nur `hinge_point`, `symmetric`, `deflection`,
  `name`. Es ist eine **Projektion** des ersten und wird daraus abgeleitet. Nicht
  unabhängig setzen.

Die Scharnierlinie darf wandern: `rel_chord_root` und `rel_chord_tip` dürfen sich
unterscheiden, dann ist sie gegenüber der Sehnenlinie gepfeilt. Fehlt der Spitzenwert, gilt
der Wurzelwert.

Bei den Ausschlägen zwei Sorten auseinanderhalten: `positive_deflection_deg` und
`negative_deflection_deg` sind **Anschläge**, `deflection_deg` ist der **Zustand**, in dem
gerade gerechnet wird.

`trailing_edge_offset_factor` skaliert die **Freimachung der Rippe** hinter der
Scharnierlinie:

$$\text{Freimachung} = \max\bigl(c_\mathrm{root}(1-\mathrm{rel\_chord\_root}),\;
(c_\mathrm{tip}+\mathrm{sweep})(1-\mathrm{rel\_chord\_tip})\bigr)\cdot f$$

$f = 1{,}0$ ist genau die Rudertiefe, $f = 1{,}2$ hält ein Fünftel mehr Luft. **Es ist kein
Anteil zwischen 0 und 1** — die Bestandsdaten laufen von 1,0 bis 1,2.

Die drei Mischfelder betreffen nur Doppelrollen. `mix_gain_primary` und
`mix_gain_secondary` sind AVL-Verstärkungen auf der symmetrischen bzw. antisymmetrischen
Achse und nur bei `elevon`, `flaperon` und `ruddervator` sinnvoll. `differential_ratio` ist
**reine Darstellung**: Es verändert die Trimm- und Aerodynamiklösung nicht.

### Turbulator

Ein Zackenband, Punkte oder ein Faden auf der **Oberseite**, einer je Segment. Die
Positionen sind $x/c$, also dimensionslos; nur `height_mm` ist eine Länge und trägt die
Einheit im Namen. `enabled: false` behält die Definition, baut sie aber nicht.

### Servo

Alle Maße in **Millimetern**. Das Objekt beschreibt die Hüllform eines Katalogbauteils —
Körper, Befestigungslasche, Kabelaustritt, Schraubloch — und daraus wird die Tasche
gefräst. `component_id` verweist zurück in die Bauteilbibliothek. Null ist als Maß erlaubt,
wenn es noch nicht bekannt ist.

---

## 7. Rumpf

### 7.1 Die Superellipse

Ein Rumpf ist eine Kette von Querschnitten, die entlang $x$ gelotet werden. Jeder
Querschnitt ist eine **Superellipse** (Lamé-Kurve):

$$\left|\frac{y}{a}\right|^{n} + \left|\frac{z}{b}\right|^{n} = 1$$

| | |
|---|---|
| $a$ | **Halb**achse in $y$ — halbe Breite, nicht Breite |
| $b$ | **Halb**achse in $z$ — halbe Höhe, nicht Höhe |
| $n$ | Exponent |

Der Exponent ist der Formregler: $n = 2$ ist die gewöhnliche Ellipse, $n < 2$ zieht die
Kontur zur Raute ein, $n > 2$ füllt sie zum gerundeten Rechteck auf. Für $n > 2$ spricht man
auch von einer **Hyperellipse**. Im Bestand reicht die Spanne von 1,04 bis 50,0 — der obere
Wert ist ein importierter Kastenquerschnitt.

Aus OpenVSP kommend gilt $a = \texttt{Ellipse\_Width}/2$ und
$b = \texttt{Ellipse\_Height}/2$. Die Achszuordnung ist über den ganzen Stapel festgelegt
(gh-706): $a \to$ AeroSandbox `width`, $b \to$ `height`, $n \to$ `shape`.

### 7.2 Die Kontur erzeugen

Für die Konstruktion braucht man die Punktfolge, nicht die implizite Gleichung:

$$y(t) = a\,\operatorname{sgn}(\cos t)\,\lvert\cos t\rvert^{2/n}, \qquad
z(t) = b\,\operatorname{sgn}(\sin t)\,\lvert\sin t\rvert^{2/n}, \qquad t \in [0, 2\pi)$$

Die Signum-Faktoren sind nötig, weil der Betrag in der impliziten Form die Vorzeichen
verwirft; ohne sie bekommt man nur den ersten Quadranten.

**Hinweis zur Stützstellenwahl:** Bei großem $n$ liegen gleichverteilte $t$ in den Ecken zu
dünn. Bei $n = 50$ und 400 000 Punkten lag eine numerische Flächenberechnung noch 3 % unter
dem exakten Wert. Wer solche Querschnitte lotet, verteilt die Stützstellen nach Bogenlänge
statt nach $t$.

Die eingeschlossene Fläche ist geschlossen angebbar und nützlich für Volumen und
Querschnittsverlauf:

$$A = 4ab\,\frac{\Gamma\!\left(1+\tfrac{1}{n}\right)^{2}}{\Gamma\!\left(1+\tfrac{2}{n}\right)}$$

Für $n = 2$ ergibt das $\pi ab$, für $n \to \infty$ geht es gegen $4ab$, das umschriebene
Rechteck. Beides numerisch nachgerechnet.

### 7.3 Was das Format nicht kann

**Ein Querschnitt steht immer senkrecht zur $x$-Achse.** Es gibt kein Feld für eine
Schnittnormale, und beide Konverter setzen sie fest auf $[1, 0, 0]$. Ein geneigter Schnitt
— etwa an einem stark abfallenden Heck — lässt sich nicht ausdrücken; man nähert ihn über
dichtere Stationen an.

Was man ausdrücken kann, ist ein **versetzter** Schnitt: `xyz` ist der Mittelpunkt, und
seine $y$- und $z$-Anteile verschieben ihn. So entstehen ein hängender Bug oder ein
hochgezogenes Heck.

`a` oder `b` dürfen **null** sein. Das ist ein entarteter Schnitt, der den Körper zu einer
Linie oder einem Punkt schließt — im Bestand 18 bzw. 16 Zeilen. Wird ein **ganzer** Körper
dadurch volumenlos, fängt ihn der Entartungsschutz ab und nimmt ihn mit einer Warnung aus
dem Aeromodell heraus (gh-790), statt die Analyse scheitern zu lassen.

### 7.4 Zwei Darstellungen nebeneinander

| | wozu |
|---|---|
| `x_secs` | das **vereinfachte** Modell für Widerstand, Auftriebsverteilung und Einbauplanung |
| `step_path` | die **genaue** Fläche aus dem Import, pro Körper exportiert (gh-729) |
| `solid_step_path` | dieselbe Geometrie **vernäht und geheilt** zum geschlossenen Volumen (gh-731) |

Keine der drei ist aus einer anderen abgeleitet, und keine ersetzt die andere. Boolesche
Konstruktionsarbeit — Akkuschacht, Servoaufnahme, Rohrdurchführung — braucht den
geschlossenen Volumenkörper; die Superellipsen genügen dafür nicht. Umgekehrt ist der
STEP-Körper für eine schnelle Widerstandsabschätzung zu schwer. `null` heißt jeweils, dass
der Körper nicht aus einem `.vsp3`-Import stammt oder das Vernähen nicht gelang.

### 7.5 Spiegelung

`symmetric` bedeutet beim Rumpf etwas anderes als bei der Fläche. Es ist **standardmäßig
falsch**, weil der Hauptrumpf selbst auf der Symmetrieebene liegt und nicht gespiegelt
werden darf. Gesetzt wird es für **paarweise** Nebenkörper, von denen nur eine Seite
gespeichert ist: Fahrwerksbeine, Radverkleidungen, Motorhauben (gh-715).

---

## 8. Prüfen

```bash
poetry run python - <<'PY'
import json, jsonschema
schema = json.load(open("docs/geometry-format/airplane-geometry.schema.json"))
doc    = json.load(open("mein_flugzeug.json"))
for e in jsonschema.Draft202012Validator(schema).iter_errors(doc):
    print("/".join(str(p) for p in e.path), "->", e.message)
PY
```

Geprüft gegen drei echte Ausgaben aus der Datenbank — ein importiertes Verkehrsflugzeug,
ein Modell mit Holmen und Rudern, und eines mit Rumpfquerschnitten. Alle drei validieren
fehlerfrei.

**Das Schema ist an drei Stellen strenger als die Laufzeit**, und zwar mit Absicht: Es
verbietet unbekannte Felder (FastAPI überliest sie), und es begrenzt `rel_chord_*`,
`*_position_factor` und `hinge_point` auf $[0,1]$, obwohl nur der Turbulator diese Grenze
wirklich erzwingt. Der Zweck einer Formatbeschreibung ist, Tippfehler laut scheitern zu
lassen. Wo es dagegen **weiter** ist als eine Typannotation im Code, steht der Grund dabei.

**Eine Stelle ist maschinell nicht prüfbar:** dass die letzte Rippe keine Segmentangaben
trägt. JSON Schema kann keine positionsabhängige Regel über ein Array ausdrücken; die
Prüfung sitzt in `AsbWingSchema.validate_last_xsec_has_no_segment_details`.

---

## 9. Zwei Widersprüche im Bestand

Beim Abgleich des Schemas gegen echte Daten sind zwei Stellen aufgefallen, an denen sich
Code und Daten uneinig sind. Sie stehen hier, damit sie nicht jedes Mal neu gefunden werden.

**`trailing_edge_offset_factor` ist als Anteil deklariert und wird als Freigangfaktor
benutzt.** Die Topologieklasse annotiert ihn als `Factor` (0 bis 1), das API-Schema lässt
jede Zahl zu, und drei Bestandszeilen tragen 1,2. Da die Annotation in einer gewöhnlichen
`__init__` steht, wird sie nicht erzwungen — der Widerspruch fällt nirgends auf. Die
Benutzung in `VaseModeWingCreator` zeigt, dass der Faktor um 1 herum gehört; die Annotation
ist das Falsche.

**Der `units`-Block verspricht weniger, als sein Name nahelegt.** Er beschreibt die
Geometrie und die Holmfelder. Die Millimeterfelder am Ruder — `hinge_spacing`,
`side_spacing_root`, `side_spacing_tip` — fallen nicht darunter und werden auch nicht
umgerechnet. Wer `detail_length: "m"` liest und daraus schließt, dass *alle* Detailfelder
in Metern stehen, liegt um den Faktor 1000 daneben.

---

## Herkunft

| Aussage über | steht in |
|---|---|
| Feldnamen, Typen, Vorgabewerte, Wertebereiche | `app/schemas/aeroplaneschema.py`, `app/schemas/Servo.py` |
| Speicherung und Einheiten | `app/models/aeroplanemodel.py`, `app/services/wing_service.py` |
| Kette vorwärts | `WingConfiguration._get_relative_segment_coordinate_system` |
| Kette rückwärts | `WingConfiguration.from_asb` |
| Holmachsen und Modi | `WingConfiguration._get_standard_spare_origin_and_vector` und die Modus-Zweige |
| Freimachung der Rippe | `VaseModeWingCreator._create_ribs_shape` |
| Rumpf zu AeroSandbox | `app/converters/model_schema_converters.py` |
| Entartungsschutz | `app/tests/test_asb_fuselage_degenerate_guard.py` |
