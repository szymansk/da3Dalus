# BRYAN - Motorisierungen laut Bauplan

Quelle: Bauplan BRYAN (FlugModell 06/26), Seite 1, Block "Antrieb" (Ausschnitt `bilder/Plan_S1_Antrieb.png`).

| Variante | Motor | KV | Masse | Propeller | Steller (ESC) | Akku |
|---|---|---|---|---|---|---|
| A (Plan-Beispiel) | Brushless 15-22 g, z. B. Pichler Pulsar Micro 1510 | 2000 | 15-22 g (1510: 19 g) | 6 x 4" (D 152,4) | Pichler Pulsar A-15 | LiPo 2S 450 mAh |
| B | Copter-Motor 1806 | 2500 | 18 g | 5 x 3" bis 5 x 4" (D 127) | Pichler Pulsar A-15 | LiPo 2S 450 mAh |
| C | Copter-Motor 1507 | 2500 | 15 g | 5 x 3" bis 5 x 4" (D 127) | Pichler Pulsar A-15 | LiPo 2S 450 mAh |

Gemeinsam: Empfaenger 6 Kanaele (2 Querruderservos), Servos 4 x Hitec HS-40 (4,8 g), Motorsturz/-seitenzug einstellbar
(Ausgang Seitenzug 2 Grad, Sturz 0 Grad). Technische Daten: Spannweite 547, Rumpflaenge 507, Abfluggewicht ab 150 g,
Flaeche 6,3 dm2, Flaechenbelastung ab 24 g/dm2.

Der Plan nennt **einen** Steller und **einen** Akku fuer alle drei Varianten; nur Motor und Propeller wechseln.

## Im Modell / Datenmodell

- 3D-Modell und Schwerpunkt (`05_modell/komponenten`) sind mit **Variante A** gerechnet: Pulsar 1510 (19 g, D 18 x 17),
  Propellerscheibe D 152,4 mit 8,7 mm Freigang zum Rumpf und 41,9 mm zum Boden (Heckrad am Boden), Steller 7 g (ANNAHME),
  Akku 58 x 30 x 12, 28 g (ANNAHME aus Datenblatt-Tabelle).
- Bei B/C wird der Propeller 25 mm kleiner im Durchmesser -> mehr Freigang. Motormasse 15-18 g statt 19 g: Schwerpunkt
  geringfuegig nach hinten, ueber den Akku-Stellbereich (X 99,5..121,1) ausgleichbar.
- **Vor dem Einbau pruefen:** Lochbild des Motors gegen den Motorspant 17 (gelasert: Lochkreis D 12,0, 8 Loecher D 1,9,
  Mittelloch D 4,95). Die Plan-Angaben enthalten kein Lochbild der Copter-Motoren.
- Das Geometrieformat hat fuer Antriebe kein Feld (format_luecken L7); der Antrieb steht im Konstruktionsprofil
  (`bryan.konstruktion.json`, komponenten.motor = Variante A) und hier als Variantenliste (`motorisierung.json`).
