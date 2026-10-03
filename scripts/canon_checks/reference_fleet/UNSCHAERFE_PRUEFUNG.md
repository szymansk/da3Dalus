# Unschärfe im Kanon: Prüfung des Verfahrens (03.10.2026)

Entschieden ist, dass der Kanon Unschärfe aufnimmt (Maintainer). Hier wird geprüft, **wie** Unschärfen
zusammengerechnet werden. Ob das so festgehalten wird, entscheidet der Maintainer.

## Vorgeschlagenes Verfahren

1. Unschärfe ist Möglichkeit, keine Wahrscheinlichkeit; keine Wurzel aus der Summe der Quadrate.
2. Unscharf sind die Ursachen (Methodenwahl, unsichere Parameter), jede mit Quelle.
3. Fortpflanzung deterministisch an Szenarien bzw. Eckpunkten durch die ganze Kette (Dong & Shah 1987).
4. Kein Intervall-auf-Intervall-Rechnen, wenn eine Ursache mehrfach eingeht.
5. Unscharf nur, wo Methoden belegt abweichen.
6. Die Methodenwahl ist ein Satz von Welten; der Kern ist der Median der Methoden.

## Rechentest am BRYAN (`fuzzy_propagation_test.py`)

- **Welten** Lehrbuch / Pappas / AVL:
  - Neutralpunkt [32,9; 34,0; 36,9] % MAC
  - Stabilitätsmaß am Plan-Schwerpunkt [1,5; 2,6; 5,5] %
  - Erstflug-Schwerpunkt bei SM 10 %: [22,9; 24,0; 26,9] %
- **Abhängigkeitsproblem, gegenläufige Wirkung:** Das Stabilitätsmaß des Erstflug-Schwerpunkts ist per
  Konstruktion genau 10 %. Naiv als Intervall verrechnet ergibt sich **6–14 %**, je Welt durch die Kette
  **10,0 %**. Regel 4 ist also nötig.
- **Gleichläufige Wirkung:** Ein schwächeres Leitwerk verschiebt den Neutralpunkt nach vorn und den
  Trimmrand nach hinten. Beides verkleinert die Reserve, beide Ränder liegen an derselben Ecke. Naiv und
  kettenweise ergeben dann dasselbe Ergebnis. Das Abhängigkeitsproblem tritt nur bei gegenläufiger
  Wirkung auf.
- **Monotonie:** Im Testmodell (linear) treffen die Eckpunkte die dichte Abtastung exakt. Für
  Optimierungsketten ist das nicht garantiert.

## Adversariales Review (Literatur)

| Regel | Urteil | Änderung |
|---|---|---|
| 1 Möglichkeit statt Wahrscheinlichkeit | haltbar | NASA Langley (NTRS 20160007678) und Roy & Oberkampf (2011) führen Model-Form-Unsicherheit als epistemisch bzw. als Intervall. Kommt echte Streuung dazu (Fertigung, Masse), dann p-box (Ferson). |
| 2 Ursachen mit Quelle | haltbar | Je Ursache festhalten: diskret (Methode) oder stetig (Parameter). Parametergrenzen brauchen eine Quelle (ADR 0023). |
| 3 Eckpunkt-Methode | mit Änderung | Nur bei Monotonie exakt (Dong & Shah 1987; Kritik arXiv 0712.3264). Je Kette eine Monotonieprüfung (Vorzeichen der Differenzen auf einem Gitter); sonst Optimierung über die Box. Obergrenze für die Zahl der Ursachen (Aufwand 2^n). Welten × Ecken als volles Produkt. |
| 4 kein Intervall auf Intervall | haltbar | Präzisiert: auch keine unabhängige Kombination zweier Ergebnisintervalle mit gemeinsamer Ursache. |
| 5 nur wo Methoden abweichen | mit Änderung | Übereinstimmende Methoden beweisen keine Sicherheit (gemeinsamer blinder Fleck). Nicht validierte Größen als „nicht validiert" kennzeichnen, nicht als scharf. |
| 6 Welten, Kern = Median | mit Änderung | Welten und Hülle sind haltbar. **Kern = Median nicht haltbar:** Drei Methoden begründen keinen Möglichkeitsgrad 1, und ein Dreieck aus drei Punkten erfindet eine Gestalt. Stattdessen reines Intervall, oder als Kern eine benannte, kalibrierte Referenzmethode. Welten nicht mischen. |

**Zusätzlich:**
- **Die Methodenstreuung ist nur eine untere Schranke** der wahren Unsicherheit. Die V&V-Antwort ist eine
  Validierungsmarge aus Messungen (Area Validation Metric, arXiv 2012.09449). Ohne Marge ist die Hülle
  als „untere Schranke" auszuweisen.
- **Info-Gap (Ben-Haim) als Ergänzung:** Der Robustheitsradius („SM bleibt ≥ 0 bis Δx_NP = …") passt zu
  „rechnet, bewertet nicht".
- **Dempster-Shafer:** für drei Methoden zu aufwendig.
- **Unscented Transform:** zielt auf Momente, nicht auf Schranken; der Vergleich trägt nur für die Idee
  „wenige Punkte durch das volle Modell".
