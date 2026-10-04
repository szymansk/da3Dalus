"""Gallery page of the isometric Urmodell renders (renders/*.png -> galerie.html), 2026-10-04."""

import base64
import html
import json
import pathlib

HERE = pathlib.Path(__file__).parent
ORDER = ["trainer", "park", "sport", "kunstflug", "3d", "speed", "elektrosegler",
         "segel_trainer", "thermik", "hang", "wurf"]
LABEL = {"trainer": "Trainer", "park": "Park", "sport": "Sport", "kunstflug": "Kunstflug", "3d": "3D",
         "speed": "Speed", "elektrosegler": "Elektrosegler", "segel_trainer": "Segeltrainer",
         "thermik": "Thermik", "hang": "Hang", "wurf": "Wurf"}
LW = {"normal": "Normalleitwerk", "t": "T-Leitwerk", "kreuz": "Kreuzleitwerk", "v": "V-Leitwerk",
      "nf_mitte": "Nurflügel, Mittelflosse", "nf_winglet": "Nurflügel, Winglets", "nf_ohne": "Nurflügel ohne Flosse"}
ST = {"hs": "Höhe + Seite", "hsq": "+ Querruder", "hsqk": "+ Querruder + Klappen", "elevon": "Elevons"}
LAGE = {"hochdecker": "Hochdecker", "schulterdecker": "Schulterdecker", "mitteldecker": "Mitteldecker",
        "tiefdecker": "Tiefdecker", "ohne_rumpf": "ohne Rumpf", None: "Doppeldecker"}

planes = [json.loads(p.read_text()) for p in sorted((HERE / "fleet").glob("*.airplane.json"))]
sections = []
for m in ORDER:
    group = [d for d in planes if d["urmodell"]["mission"] == m]
    cards = []
    for d in group:
        u = d["urmodell"]
        img = base64.b64encode((HERE / "renders" / f"{d['name']}.png").read_bytes()).decode()
        ws = d["total_mass_kg"] * 1000 / (u["S_m2"] * 100)
        cards.append(f'''<figure class="card" data-m="{m}">
<img alt="Isometrie {html.escape(d['name'])}" loading="lazy" src="data:image/png;base64,{img}">
<figcaption><b>{LAGE[u['lage']] if u['trag'] == 'eindecker' else 'Doppeldecker'}</b>
<span>{LW[u['leitwerk']]} · {ST[u['steuerung']]}</span>
<span class="num">b {u['span_m']*1000:.0f} mm · {d['total_mass_kg']*1000:.0f} g · {ws:.0f} g/dm² · AR {u['AR']:.1f}</span></figcaption></figure>''')
    motor = "Motor" if group[0]["urmodell"]["motor"] == "ja" else "Segler"
    sections.append(f'''<section id="{m}"><h2>{LABEL[m]} <small>{motor} · {len(group)}</small></h2>
<div class="grid">{''.join(cards)}</div></section>''')
chips = "".join(f'<a href="#{m}">{LABEL[m]}</a>' for m in ORDER)

page = f'''<title>Urmodell-Flotte</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
/* Layout: drawing-sheet gallery, one section per mission, cards in an auto-fill grid */
:root {{ --bg:#f6f4f1; --panel:#ffffff; --fg:#1d1c1a; --muted:#6b665f; --line:#e2ddd6; --accent:#c95f00;
  --display:"Geist",system-ui,sans-serif; --mono:"JetBrains Mono",ui-monospace,monospace; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#141312; --panel:#1d1c1a;
  --fg:#ece8e2; --muted:#9a948b; --line:#2e2c29; --accent:#ff8400; color-scheme:dark; }} }}
:root[data-theme="dark"] {{ --bg:#141312; --panel:#1d1c1a; --fg:#ece8e2; --muted:#9a948b; --line:#2e2c29;
  --accent:#ff8400; color-scheme:dark; }}
body {{ background:var(--bg); color:var(--fg); font-family:var(--display); padding-inline:16px; padding-block:24px 48px; }}
.wrap {{ max-width:1280px; margin:0 auto; display:flex; flex-direction:column; gap:28px; }}
header h1 {{ font-size:1.6rem; margin:0 0 6px; text-wrap:balance; }}
header p {{ margin:0; color:var(--muted); max-width:70ch; line-height:1.5; }}
nav {{ display:flex; flex-wrap:wrap; gap:6px; position:sticky; top:env(safe-area-inset-top,0px); background:var(--bg);
  padding-block:8px; z-index:2; }}
nav a {{ font:600 12px var(--mono); color:var(--fg); text-decoration:none; border:1px solid var(--line);
  padding:4px 10px; border-radius:3px; }}
nav a:hover, nav a:focus-visible {{ border-color:var(--accent); color:var(--accent); outline:none; }}
h2 {{ font-size:1.15rem; margin:0 0 12px; border-bottom:1px solid var(--line); padding-bottom:6px; }}
h2 small {{ font:400 12px var(--mono); color:var(--muted); letter-spacing:.04em; margin-left:8px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:12px; }}
.card {{ margin:0; background:var(--panel); border:1px solid var(--line); border-radius:4px; overflow:hidden;
  display:flex; flex-direction:column; min-width:0; }}
.card img {{ width:100%; aspect-ratio:4/3.2; object-fit:contain; max-width:100%; }}
figcaption {{ display:flex; flex-direction:column; gap:2px; padding:8px 10px 10px; border-top:1px solid var(--line); font-size:13px; }}
figcaption span {{ color:var(--muted); }}
.num {{ font:12px var(--mono); font-variant-numeric:tabular-nums; color:var(--accent) !important; }}
</style>
<div class="wrap">
<header><h1>Urmodell-Flotte · 74 typische Urmodelle</h1>
<p>Isometrische Ansicht (von vorn links oben, gleicher Maßstab auf allen Achsen, jedes Bild auf seine Größe
eingepasst). Je Mission eine recherchierte Spannweite. Bei V-Leitwerken nahe 40° Öffnungswinkel steht eine
Hälfte in der Isometrie fast genau auf Kante und erscheint als Strich.</p></header>
<nav aria-label="Missionen">{chips}</nav>
{''.join(sections)}
</div>
'''
(HERE / "galerie.html").write_text(page)
print(len(page) // 1024, "KB")
