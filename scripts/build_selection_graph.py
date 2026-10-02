"""Build the Urmodell selection graph page from _reversa_sdd/calculations/auswahl/auswahl.json.

    poetry run python scripts/build_selection_graph.py

The page is generated — edit the JSON, never the HTML. It runs parallel to the calculation
canon: seven guided questions (motorised? -> mission -> wing system -> wing position -> tail -> control axes -> span) lead to an Urmodell,
which the canon then computes like any airplane (ANFORDERUNGEN.md O12, section 6.1).
The output is pure ASCII (data as \\u escapes, text as HTML entities) so no viewer can
mis-decode it.
"""

from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "_reversa_sdd" / "calculations" / "auswahl" / "auswahl.json"
OUT = ROOT / "_reversa_sdd" / "calculations" / "auswahl" / "auswahl.html"

TEMPLATE = r"""<title>Urmodell-Auswahl</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
:root{
  --bg:#F2F3F5; --panel:#FFFFFF; --ink:#15171C; --muted:#5B616E; --line:#D8DBE1;
  --accent:#FF8400; --accent-ink:#A85400; --chosen:#FFF0DF; --dim:#A9AEB8;
  --tag-rech:#2F6F9E; --tag-top:#6B5BA8; --tag-aus:#3E7F4E; --tag-kan:#A85400;
    --good:#2E7D4F; --warn:#9A6200; --bad:#B23A3A;
  --sans:"Geist",ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"SFMono-Regular",Menlo,monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#111317; --panel:#1A1D22; --ink:#E8EAEE; --muted:#9AA1AC; --line:#2B3038;
    --accent:#FF8F1F; --accent-ink:#FFB066; --chosen:#2A1D0F; --dim:#555B66;
    --tag-rech:#7FB3DA; --tag-top:#B4A8E6; --tag-aus:#8CC79A; --tag-kan:#FFB066;
    --good:#7CCB97; --warn:#E5B45C; --bad:#F08A8A;
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#111317; --panel:#1A1D22; --ink:#E8EAEE; --muted:#9AA1AC; --line:#2B3038;
  --accent:#FF8F1F; --accent-ink:#FFB066; --chosen:#2A1D0F; --dim:#555B66;
  --tag-rech:#7FB3DA; --tag-top:#B4A8E6; --tag-aus:#8CC79A; --tag-kan:#FFB066;
    --good:#7CCB97; --warn:#E5B45C; --bad:#F08A8A;
  color-scheme:dark;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5;margin:0}
.wrap{max-width:1240px;margin:0 auto;padding-inline:20px;padding-block:28px 48px;display:grid;gap:22px}
header{display:grid;gap:6px}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
h1{font-size:26px;line-height:1.15;margin:0;text-wrap:balance;font-weight:700}
.lede{color:var(--muted);max-width:68ch;margin:0}
.path{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-family:var(--mono);font-size:12.5px}
.path .seg{padding:3px 9px;border:1px solid var(--line);border-radius:4px;background:var(--panel)}
.path .seg.set{border-color:var(--accent);color:var(--accent-ink)}
.path .arrow{color:var(--dim)}
.steps{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;align-items:start}
.step{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:14px;display:grid;gap:10px}
.step.locked{opacity:.55}
.stephead{display:grid;gap:3px}
.stepno{font-family:var(--mono);font-size:11px;color:var(--accent-ink);letter-spacing:.06em}
.step h2{font-size:17px;margin:0;font-weight:600}
.why{font-size:13px;color:var(--muted);margin:0}
.opts{display:grid;gap:6px}
.grp{font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-top:4px}
.opt{all:unset;cursor:pointer;display:grid;gap:1px;padding:8px 10px;border:1px solid var(--line);border-radius:5px;background:var(--panel)}
.opt:hover{border-color:var(--accent)}
.opt:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.opt.on{background:var(--chosen);border-color:var(--accent)}
.opt .n{font-weight:600;font-size:14px}
.opt .k{font-size:12.5px;color:var(--muted)}
.opt[disabled]{cursor:not-allowed;opacity:.55}
.opt .top{display:flex;gap:6px;align-items:baseline;justify-content:space-between}
.badge{font-family:var(--mono);font-size:10px;letter-spacing:.04em;padding:0 5px;border-radius:3px;border:1px solid currentColor;white-space:nowrap}
.badge.T{color:var(--good)} .badge.U{color:var(--warn)} .badge.N{color:var(--bad)}
.opt .r{font-size:11.5px;color:var(--muted);line-height:1.35;margin-top:3px}
.none-step{font-size:13px;color:var(--muted);margin:0}
.stephint.note-m{color:var(--ink);border-top-style:solid}
.stephint{font-size:12px;color:var(--muted);margin:0;border-top:1px dashed var(--line);padding-top:8px}
.legend{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:12px;color:var(--muted)}
.span{display:grid;gap:8px}
.span label{font-size:13px;color:var(--muted)}
.span .row{display:flex;gap:10px;align-items:center}
.span input[type=range]{flex:1;min-width:0;accent-color:var(--accent)}
.span input[type=number]{width:78px;flex:none;font-family:var(--mono);font-size:14px;padding:5px 7px;border:1px solid var(--line);border-radius:4px;background:var(--bg);color:var(--ink);font-variant-numeric:tabular-nums}
.span .unit{font-family:var(--mono);font-size:12.5px;color:var(--muted)}
.fixes{display:grid;gap:4px;border-top:1px dashed var(--line);padding-top:9px}
.fixes .t{font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.fixes ul{margin:0;padding-left:17px;font-size:13px;display:grid;gap:2px}
.fixes .none{font-size:13px;color:var(--dim);margin:0}
.urmodell{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:6px;padding:16px 18px;display:grid;gap:12px}
.urmodell h2{margin:0;font-size:18px}
.urhead{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:baseline;justify-content:space-between}
.state{font-family:var(--mono);font-size:12px;padding:2px 8px;border-radius:4px;border:1px solid var(--line);color:var(--muted)}
.state.ready{border-color:var(--accent);color:var(--accent-ink)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
.tbl{overflow-x:auto}
th{font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);text-align:left;font-weight:600;padding:6px 10px 6px 0;border-bottom:1px solid var(--line)}
td{padding:7px 10px 7px 0;border-bottom:1px solid var(--line);vertical-align:top}
td.was{font-weight:600;white-space:nowrap}
.tag{font-family:var(--mono);font-size:11px;padding:1px 6px;border-radius:3px;border:1px solid currentColor;white-space:nowrap}
.tag.Rechnung{color:var(--tag-rech)} .tag.Topologie{color:var(--tag-top)} .tag.Auswahl{color:var(--tag-aus)} .tag.Kanon{color:var(--tag-kan)}
tr.off td{color:var(--dim)} tr.off .tag{color:var(--dim)}
.note{font-size:12.5px;color:var(--muted);margin:0;max-width:90ch}
code{font-family:var(--mono);font-size:12.5px}
@media (max-width:980px){.steps{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:560px){.steps{grid-template-columns:1fr} td.was{white-space:normal}}
@media (prefers-reduced-motion:no-preference){.opt{transition:border-color .12s,background .12s}}
</style>

<div class="wrap">
  <header>
    <div class="eyebrow">da3Dalus &middot; Auswahlgraph &middot; parallel zum Rechenkanon</div>
    <h1>Urmodell-Auswahl</h1>
    <p class="lede">Sieben Fragen f&uuml;hren zu einem ersten, g&uuml;ltigen und stabilen Flugzeug. Jede Antwort legt etwas fest; was daraus folgt, steht unten. Der Rechenkanon rechnet das Urmodell danach wie jedes andere Flugzeug.</p>
    <div class="path" id="path" aria-live="polite"></div>
    <div class="legend"><span><span class="badge T">typisch</span> h&auml;ufig f&uuml;r diese Mission</span><span>ohne Abzeichen: m&ouml;glich</span><span><span class="badge U">ungew&ouml;hnlich</span> gibt es, aber selten</span><span><span class="badge N">unsinnig</span> widerspricht der Mission, nicht w&auml;hlbar</span></div>
  </header>
  <section class="steps" id="steps" aria-label="Fragen"></section>
  <section class="urmodell" aria-label="Urmodell">
    <div class="urhead"><h2>Was das Urmodell daraus bekommt</h2><span class="state" id="state"></span></div>
    <div class="tbl"><table><thead><tr><th>Gr&ouml;&szlig;e</th><th>kommt aus</th><th>Art</th></tr></thead><tbody id="ur"></tbody></table></div>
    <p class="note" id="hinweis"></p>
  </section>
</div>

<script>window.__AUSWAHL__=__DATA__;</script>
<script>
(function(){
  const D=window.__AUSWAHL__, S=D.schritte;
  const pick={motor:"ja", mission:"trainer", trag:"eindecker", lage:"hochdecker", leitwerk:"normal", steuerung:"hs", spannweite:1400};
  let example=true;
  const el=(t,c,h)=>{const e=document.createElement(t); if(c) e.className=c; if(h!=null) e.innerHTML=h; return e;};
  const esc=s=>String(s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
  const opt=(step,id)=>(step.optionen||[]).find(o=>o.id===id);
  // a condition {key: value | [values]} holds when every key's pick matches; wenn_nicht excludes
  const holds=c=>Object.entries(c).every(([k,v])=>Array.isArray(v)?v.includes(pick[k]):pick[k]===v);
  const allowed=o=>(!o.wenn||holds(o.wenn))&&(!o.wenn_nicht||!Object.entries(o.wenn_nicht).some(([k,v])=>v.includes(pick[k])));
  const active=st=>!st.nur_wenn||holds(st.nur_wenn);
  const answered=st=>!active(st)||pick[st.id]!=null;
  // rating for the chosen mission: the matrix (by own id or bewertung_von) first, then the typical lists
  const rating=(st,o)=>{
    if(!pick.mission) return null;
    if(o.typisch_immer) return "T";
    const r=(D.bewertung[pick.mission]||{})[o.bewertung_von||o.id];
    if(r) return r;
    return (o.typisch||[]).includes(pick.mission)?"T":null;
  };
  const reason=o=>{ const k=o.bewertung_von||o.id; return D.gruende[pick.mission+":"+k]||D.gruende["*:"+k]||""; };
  const usable=(st,o)=>allowed(o)&&rating(st,o)!=="N";
  function fixesBox(items){
    const b=el("div","fixes"); b.appendChild(el("div","t","legt fest"));
    if(!items||!items.length){ b.appendChild(el("p","none","Noch nichts gew&auml;hlt.")); return b; }
    const ul=el("ul"); items.forEach(x=>ul.appendChild(el("li",null,esc(x)))); b.appendChild(ul); return b;
  }
  function render(){
    const host=document.getElementById("steps"); host.innerHTML="";
    S.forEach((st,i)=>{
      const prevDone=S.slice(0,i).every(answered);
      const box=el("article","step"+(prevDone&&active(st)?"":" locked"));
      const head=el("div","stephead");
      head.appendChild(el("div","stepno","Frage "+(i+1)+" von "+S.length));
      head.appendChild(el("h2",null,esc(st.frage)));
      head.appendChild(el("p","why",esc(st.warum)));
      box.appendChild(head);
      if(!active(st)){
        const by=S.find(s=>s.id===Object.keys(st.nur_wenn)[0]), o=by&&opt(by,pick[by.id]);
        box.appendChild(el("p","none-step","Entf&auml;llt"+(o?" f&uuml;r "+esc(o.name):"")+"."));
      } else if(st.eingabe){
        const e=st.eingabe, w=el("div","span"), id="span-"+st.id;
        const v=pick[st.id]!=null?pick[st.id]:e.beispiel;
        w.innerHTML=`<label for="${id}">Spannweite in ${e.einheit}</label>
          <div class="row"><input type="range" id="${id}-r" min="${e.min}" max="${e.max}" step="${e.schritt}" value="${v}" ${prevDone?"":"disabled"} aria-label="Spannweite">
          <input type="number" id="${id}" min="${e.min}" max="${e.max}" step="${e.schritt}" value="${v}" ${prevDone?"":"disabled"}><span class="unit">${e.einheit}</span></div>`;
        box.appendChild(w);
        const r=w.querySelector('input[type=range]'), n=w.querySelector('input[type=number]');
        const set=x=>{ x=Math.max(e.min,Math.min(e.max,Number(x)||e.min)); pick[st.id]=x; example=false; r.value=x; n.value=x; renderPath(); renderUr(); };
        r.addEventListener("input",ev=>set(ev.target.value)); n.addEventListener("change",ev=>set(ev.target.value));
        box.appendChild(fixesBox(pick[st.id]!=null?st.legt_fest:null));
      } else {
        const opts=el("div","opts"); let grp=null;
        st.optionen.filter(allowed).forEach(o=>{
          if(o.gruppe&&o.gruppe!==grp){ grp=o.gruppe; opts.appendChild(el("div","grp",esc(grp))); }
          const b=el("button","opt"+(pick[st.id]===o.id?" on":""));
          const r=rating(st,o);
          b.type="button"; b.id="opt-"+st.id+"-"+o.id; b.disabled=!prevDone||r==="N";
          b.setAttribute("aria-pressed",pick[st.id]===o.id?"true":"false");
          const badge=r&&r!=="P"?`<span class="badge ${r}">${esc(D.legende[r])}</span>`:"";
          const why=(r==="U"||r==="N")?`<span class="r">${esc(reason(o))}</span>`:"";
          b.innerHTML=`<span class="top"><span class="n">${esc(o.name)}</span>${badge}</span><span class="k">${esc(o.kurz)}</span>${why}`;
          b.addEventListener("click",()=>choose(st,o.id));
          opts.appendChild(b);
        });
        box.appendChild(opts);
        const sel=opt(st,pick[st.id]);
        box.appendChild(fixesBox(sel?sel.legt_fest:null));
        const an=st.anmerkungen&&pick.mission&&st.anmerkungen[pick.mission];
        if(an) box.appendChild(el("p","stephint note-m",esc(an)));
        if(st.hinweis) box.appendChild(el("p","stephint",esc(st.hinweis)));
      }
      host.appendChild(box);
    });
    renderPath(); renderUr();
  }
  function choose(st,id){
    pick[st.id]=id; example=false;
    // a later answer that no longer fits the earlier ones is cleared
    S.forEach(s=>{
      if(!active(s)){ pick[s.id]=null; return; }
      if(s.optionen&&pick[s.id]!=null){ const o=opt(s,pick[s.id]); if(o&&!usable(s,o)) pick[s.id]=null; }
    });
    // a layout with exactly one tail option takes it directly
    for(const s of S){ const i=S.indexOf(s); if(s.optionen&&active(s)&&pick[s.id]==null&&S.slice(0,i).every(answered)){ const only=s.optionen.filter(o=>usable(s,o)); if(only.length===1) pick[s.id]=only[0].id; } }
    render();
  }
  function renderPath(){
    const p=document.getElementById("path"); p.innerHTML="";
    S.forEach((st,i)=>{
      if(i) p.appendChild(el("span","arrow","&rarr;"));
      let txt=st.frage+": &ndash;";
      if(!active(st)) txt=st.frage+": entf&auml;llt";
      else if(pick[st.id]!=null){ txt = st.eingabe ? `${pick[st.id]} ${st.eingabe.einheit}` : esc(opt(st,pick[st.id]).name); }
      p.appendChild(el("span","seg"+(pick[st.id]!=null||!active(st)?" set":""),txt));
    });
    if(example) p.appendChild(el("span","seg","Beispiel &mdash; w&auml;hle selbst"));
  }
  function renderUr(){
    const done=S.every(answered), motor=pick.motor==="ja";
    const st=document.getElementById("state");
    st.className="state"+(done?" ready":""); st.innerHTML=done?(example?"Urmodell (Beispielpfad)":"Urmodell bereit"):"noch "+S.filter(s=>!answered(s)).length+" Frage(n) offen";
    const tb=document.getElementById("ur"); tb.innerHTML="";
    D.urmodell.forEach(u=>{
      const off=u.nur_motor&&!motor;
      const tr=el("tr",off?"off":null);
      const aus=off?"entf\u00e4llt \u2014 ohne Motor":u.aus;
      tr.innerHTML=`<td class="was">${esc(u.was)}</td><td>${esc(aus)}${u.eintrag&&!off?` <code>${esc(u.eintrag)}</code>`:""}</td><td><span class="tag ${esc(u.art)}">${esc(u.art)}</span></td>`;
      tb.appendChild(tr);
    });
    document.getElementById("hinweis").innerHTML="Stand "+esc(D.stand)+". "+esc(D.hinweis);
  }
  render();
})();
</script>
"""


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=True))
    html.encode("ascii")  # fails loudly if a non-ASCII character slipped into the template
    OUT.write_text(html, encoding="ascii")
    print(f"-> {OUT.relative_to(ROOT)}  ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
