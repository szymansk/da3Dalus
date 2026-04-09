# Aeroanalysis
Implementiere einen TrimmedOperatingPoint der die Trimmung nach einer Trim Optimierung für einen vorgegebenen Operating Point enthält.
Er hat einen Verweis auf einen OperatingPoint und auf ein Flugzeug. Er enthält die Stellung (Deflection) aller ControlSurfaces des Flugzeugs.

# User-Stories 
1. Als Anwender möchte ich über die REST-API ein Flugzeug stückweise, vom niedrigen bis zum hohen Detail, aufbauen können. Beispiel: Ich lege erst das Flugzeug an, dann füge ich ein Tragfläche hinzu, dann füge ich x_sections ein, danach Füge ich ausgewählten x_sections eine Control Surface hinzu (das zur aerodynamischen analyse ausreichend ist), danach füge ich Spars den x_sections hinzu, am ende füge ich eine x_section noch eine genaue definition hinzu, die benötigt werden um das control_surface/TrailingEdgeDevice im CAD zu modellieren, danach füge ich einen Servo hinzu und bestimme seine position. 

2. Als Anwender möchte ich Tragflächen und Rümpfe anlegen können, die die Mindestsanforderungen von aerosandbox genügen, um erste aerodynamische Analysen machen zu können, ohne an die 3D CAD Konstruktion zu denken.

3. Als Anwender möchte ich eine Bestehende Tragfläche oder Rumpf um informationen die für die CAD erzeugung notwendig sind erweitern können, um eine sequentielle Verfeinerung des Designs zu erreichen.

Wenn du Architektur entscheidungen abfragst, dann erkläre sie vor ab ausführlich.

# Testing
1. Ich möchte, dass du einen sequentiellen Test erzeugst, der ein Model nacheinander über die REST-API aufbaut. Der Test, soll einen Design durchlauf simulieren, wie ihn ein Anwender durchführt. Der Ablauf ist wie folgt:
a. Lege ein Flugzeug "DesignTest" an.
b. Lege eine Tragfläche "main_wing" an mit:

```JSON 
{
  "name": "Main Wing",
  "symmetric": true,
  "x_secs": [
    {
      "xyz_le": [
        0,
        0,
        0
      ],
      "chord": 0.2,
      "twist": 0,
      "airfoil": "./components/airfoils/naca0015.dat"
    },
    {
      "xyz_le": [
        0.1,
        0.5,
        0
      ],
      "chord": 0.2,
      "twist": 1,
      "airfoil": "./components/airfoils/naca0015.dat"
    }
  ]
}
````
c. Dann einmal updaten des Flügels zu 
```JSON 
{
  "name": "Main Wing",
  "symmetric": true,
  "x_secs": [
    {
      "xyz_le": [
        0,
        0,
        0
      ],
      "chord": 0.2,
      "twist": 0,
      "airfoil": "./components/airfoils/naca0015.dat"
    },
    {
      "xyz_le": [
        0.05,
        0.5,
        0
      ],
      "chord": 0.95,
      "twist": 1,
      "airfoil": "./components/airfoils/naca0015.dat"
    }
  ]
}
````

46600896-7693-4fa8-a93c-1420dc48f735