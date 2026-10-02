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
    --good:#2E7D4F; --sk-fill:#E3E6EB; --warn:#9A6200; --bad:#B23A3A;
  --sans:"Geist",ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"SFMono-Regular",Menlo,monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#111317; --panel:#1A1D22; --ink:#E8EAEE; --muted:#9AA1AC; --line:#2B3038;
    --accent:#FF8F1F; --accent-ink:#FFB066; --chosen:#2A1D0F; --dim:#555B66;
    --tag-rech:#7FB3DA; --tag-top:#B4A8E6; --tag-aus:#8CC79A; --tag-kan:#FFB066;
    --good:#7CCB97; --sk-fill:#2A2F37; --warn:#E5B45C; --bad:#F08A8A;
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#111317; --panel:#1A1D22; --ink:#E8EAEE; --muted:#9AA1AC; --line:#2B3038;
  --accent:#FF8F1F; --accent-ink:#FFB066; --chosen:#2A1D0F; --dim:#555B66;
  --tag-rech:#7FB3DA; --tag-top:#B4A8E6; --tag-aus:#8CC79A; --tag-kan:#FFB066;
    --good:#7CCB97; --sk-fill:#2A2F37; --warn:#E5B45C; --bad:#F08A8A;
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
.sketch{display:grid;grid-template-columns:1.1fr 1fr 1fr;gap:10px 18px;align-items:start;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px 16px}
.sketch figure{margin:0;display:grid;gap:4px}
.sketch figcaption{font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.sketch svg{width:100%;height:auto;display:block}
.sketch .note{grid-column:1/-1}
.cs-chip{display:inline-block;width:14px;height:8px;background:var(--accent);vertical-align:middle;border-radius:1px}
.sk{fill:var(--sk-fill);stroke:var(--ink);stroke-width:1.1;stroke-linejoin:round}
.sk.dash{fill:none;stroke-dasharray:4 3}
.cs{fill:var(--accent);stroke:none}
.skl{stroke:var(--ink);stroke-width:1.1;fill:none}
.skw{stroke:var(--ink);stroke-width:2.6;fill:none;stroke-linecap:round;stroke-linejoin:round}
.skd{stroke:var(--muted);stroke-width:1;fill:none}
.skt{fill:var(--muted);font-family:var(--mono);font-size:11px}
.prop{stroke:var(--muted);stroke-width:1.4;fill:none;stroke-dasharray:3 3}
@media (max-width:760px){.sketch{grid-template-columns:1fr}}
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
  <section class="sketch" aria-label="Skizze">
    <figure><div id="sk-top"></div><figcaption>Draufsicht</figcaption></figure>
    <figure><div id="sk-side"></div><figcaption>Seitenansicht</figcaption></figure>
    <figure><div id="sk-front"></div><figcaption>Vorderansicht</figcaption></figure>
    <p class="note">Schematisch, nicht ma&szlig;st&auml;blich: Proportionen nur zur Anschauung, kein Band. <span class="cs-chip"></span> Ruder &middot; gestrichelt: verdeckt oder an der Fl&uuml;gelspitze &middot; Strichkreis: Propeller</p>
  </section>
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
  // schematic three-view of the current answers; proportions are illustrative only
  function drawSketch(){
    const b=240, cx=150, y0=16, Lf=176;
    const ar=((D.skizze||{}).streckung||{})[pick.mission]||7, c=b/ar;
    const lw=pick.leitwerk, ax=pick.steuerung, trag=pick.trag||"eindecker", lage=pick.lage;
    const NF=["nf_mitte","nf_winglet","nf_ohne"], AFT=["normal","t","kreuz","v","dach","h"];
    const nf=NF.includes(lw), ente=!!lw&&lw.indexOf("ente")===0, aft=AFT.includes(lw);
    const fus=!(trag==="eindecker"&&lage==="ohne_rumpf");
    const ail=["hq","hsq","hsqk"].includes(ax), flap=ax==="hsqk", elevon=!!ax&&ax.indexOf("elevon")===0;
    const rud=["hs","hsq","hsqk","elevon_s"].includes(ax), elev=!!ax&&!elevon;
    const f1=v=>v.toFixed(1), P=pts=>pts.map(p=>f1(p[0])+","+f1(p[1])).join(" ");
    const poly=(pts,cl)=>`<polygon class="${cl||"sk"}" points="${P(pts)}"/>`;
    const L=(x1,y1,x2,y2,cl)=>`<line class="${cl||"skl"}" x1="${f1(x1)}" y1="${f1(y1)}" x2="${f1(x2)}" y2="${f1(y2)}"/>`;
    const R=(x,y,w,h,cl)=>`<rect class="${cl||"sk"}" x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}"/>`;
    const tan=d=>Math.tan(d*Math.PI/180);
    const mainCS=[].concat(ail?[[0.55,0.95]]:[],flap?[[0.08,0.5]]:[],elevon?[[0.3,0.95]]:[]);
    function wing(yr,span,cr,taper,sw,cs,cl){
      let s=""; const h=span/2, ct=cr*taper;
      for(const sg of [1,-1]){
        const X=f=>cx+sg*h*f, LE=f=>yr+sw*f, CH=f=>cr+(ct-cr)*f;
        s+=poly([[X(0),LE(0)],[X(1),LE(1)],[X(1),LE(1)+CH(1)],[X(0),LE(0)+CH(0)]],cl);
        if(!cl) for(const [a,e] of cs) s+=poly([[X(a),LE(a)+CH(a)*0.72],[X(e),LE(e)+CH(e)*0.72],[X(e),LE(e)+CH(e)],[X(a),LE(a)+CH(a)]],"cs");
      }
      return s;
    }
    const finTop=(y,len)=>R(cx-1.5,y,3,len);
    const k=250/Lf, xs=y=>22+(y-y0)*k;
    const prof=(x,y,ch)=>`<ellipse class="sk" cx="${f1(x+ch/2)}" cy="${f1(y)}" rx="${f1(ch/2)}" ry="2.6"/>`;
    const finSide=(xe,cw,base,top,cl)=>poly([[xe-cw*1.25,base],[xe-cw*0.45,top],[xe,top],[xe,base]],cl)+(rud&&!cl?R(xe-cw*0.3,top+2,cw*0.3,base-top-3,"cs"):"");
    const fw=(y,half,deg,cl)=>{ const d=tan(deg)*half; return `<polyline class="${cl||"skw"}" points="${P([[cx-half,y-d],[cx,y],[cx+half,y-d]])}"/>`; };
    const WY={hochdecker:[83,85],schulterdecker:[87,88],mitteldecker:[95,95],tiefdecker:[105,104],ohne_rumpf:[95,95]};
    const wy=WY[lage]||[95,95];
    const dih=ax==="hs"?7:nf?1.5:["kunstflug","3d"].includes(pick.mission)?0:2.5;
    let T="", Sd="", Fb="", F="", pusher=null;
    const lenF=nf?0.5*b:Lf;
    if(fus){
      T+=`<rect class="sk" x="${cx-7}" y="${y0}" width="14" height="${f1(lenF)}" rx="7"/>`;
      const xe=xs(y0+lenF), xm=22+0.45*(xe-22);
      Sd+=`<path class="sk" d="M22,95 C22,83 32,83 46,83 L${f1(xm)},84 L${f1(xe)},91 L${f1(xe)},99 L${f1(xm)},106 L46,107 C32,107 22,107 22,95 Z"/>`;
    }
    function aftTail(){
      const ct=0.62*c, yt=y0+Lf-ct, span=(lw==="v"||lw==="dach")?0.3*b:0.36*b, xe=xs(y0+Lf), cw=ct*k, hs=span/2*0.9;
      T+=wing(yt,span,ct,0.8,0,elev?[[0.05,0.98]]:[]);
      if(["normal","t","kreuz"].includes(lw)) T+=finTop(yt-ct*0.3,ct*1.3);
      if(lw==="h") for(const sg of [1,-1]) T+=R(cx+sg*span/2-1.5,yt-ct*0.2,3,ct*1.2);
      if(lw==="v"){ Sd+=poly([[xe-cw*1.1,90],[xe-cw*0.35,70],[xe,70],[xe,90]])+(elev?R(xe-cw*0.3,72,cw*0.3,17,"cs"):""); Fb+=L(cx,90,cx-30,66,"skw")+L(cx,90,cx+30,66,"skw"); }
      else if(lw==="dach"){ Sd+=poly([[xe-cw*1.1,99],[xe-cw*0.35,118],[xe,118],[xe,99]])+(elev?R(xe-cw*0.3,100,cw*0.3,17,"cs"):""); Fb+=L(cx,100,cx-30,122,"skw")+L(cx,100,cx+30,122,"skw"); }
      else {
        const sy={normal:91,h:91,kreuz:74,t:58}[lw];
        Sd+=finSide(xe,cw,91,58)+`<ellipse class="sk" cx="${f1(xe-cw/2)}" cy="${sy}" rx="${f1(cw/2)}" ry="2"/>`;
        if(lw==="h") Fb+=L(cx-hs,93,cx+hs,93,"skw")+L(cx-hs,78,cx-hs,104,"skw")+L(cx+hs,78,cx+hs,104,"skw");
        else { const fy={normal:93,kreuz:76,t:60}[lw]; Fb+=L(cx,93,cx,60,"skw")+L(cx-hs,fy,cx+hs,fy,"skw"); }
      }
    }
    if(trag==="eindecker"||trag==="doppeldecker"){
      if(nf){
        const sw=lw==="nf_mitte"?0.05*b:0.26*b, cr=1.35*c, ctip=cr*0.55, yW=y0+(fus?0.14*b:0.06*b), tipLE=yW+sw;
        T+=wing(yW,b,cr,0.55,sw,mainCS);
        if(lw==="nf_mitte") T+=finTop(yW+cr*0.55,cr*0.5);
        if(lw==="nf_winglet") for(const sg of [1,-1]) T+=R(cx+sg*b/2-1.5,tipLE,3,ctip);
        Sd+=prof(xs(yW),wy[0],cr*k);
        if(lw==="nf_mitte"){ const xt=xs(yW)+cr*k; Sd+=finSide(xt,cr*k*0.35,wy[0],wy[0]-24); Fb+=L(cx,wy[1],cx,wy[1]-24,"skw"); }
        if(lw==="nf_winglet"){ const xt=xs(tipLE)+ctip*k; Sd+=finSide(xt,ctip*k*0.8,wy[0],wy[0]-18,"sk dash"); const d=tan(dih)*120; F+=L(cx-120,wy[1]-d,cx-120,wy[1]-d-18,"skw")+L(cx+120,wy[1]-d,cx+120,wy[1]-d-18,"skw"); }
        F+=fw(wy[1],120,dih);
        if(!fus) pusher=yW+cr;
      } else {
        const yW=y0+(ente?0.55:0.2)*Lf, bi=trag==="doppeldecker";
        if(bi) T+=wing(yW+0.4*c,b,c,0.95,0,[],"sk dash");
        T+=wing(yW,b,c,bi?0.95:0.7,0,mainCS);
        if(bi){
          const xu=xs(yW)+c*k*0.5, xl=xs(yW+0.4*c)+c*k*0.5, ls=106-tan(dih)*80;
          Sd+=prof(xs(yW),66,c*k)+prof(xs(yW+0.4*c),106,c*k)+L(xu,68,xl,104);
          F+=fw(68,120,0)+fw(106,115,dih)+L(cx-80,68,cx-80,ls)+L(cx+80,68,cx+80,ls);
        } else { Sd+=prof(xs(yW),wy[0],c*k); F+=fw(wy[1],120,dih); }
        if(aft) aftTail();
        if(ente){
          const cf=0.55*c, yf=y0+0.05*Lf;
          T+=wing(yf,0.32*b,cf,0.85,0,elev?[[0.08,0.98]]:[]);
          Sd+=prof(xs(yf),93,cf*k); F+=L(cx-38,93,cx+38,93,"skw");
          if(lw==="ente_flosse"){ T+=finTop(y0+Lf-0.6*c,0.6*c); Sd+=finSide(xs(y0+Lf),0.6*c*k,91,60); Fb+=L(cx,93,cx,62,"skw"); }
          if(lw==="ente_winglet"){
            for(const sg of [1,-1]) T+=R(cx+sg*b/2-1.5,yW,3,0.7*c);
            Sd+=finSide(xs(yW)+c*k*0.85,c*k*0.6,wy[0],wy[0]-18,"sk dash");
            const d=tan(dih)*120; F+=L(cx-120,wy[1]-d,cx-120,wy[1]-d-18,"skw")+L(cx+120,wy[1]-d,cx+120,wy[1]-d-18,"skw");
          }
        }
      }
    } else if(trag==="tandem"){
      const yF=y0+0.14*Lf, yR=y0+0.72*Lf;
      T+=wing(yF,b,c,0.75,0,mainCS)+wing(yR,0.9*b,c,0.75,0,elev?[[0.1,0.9]]:[])+finTop(y0+Lf-0.55*c,0.55*c);
      Sd+=prof(xs(yF),104,c*k)+prof(xs(yR),82,c*k)+finSide(xs(y0+Lf),0.55*c*k,91,60);
      F+=fw(104,120,2)+fw(80,108,dih); Fb+=L(cx,93,cx,62,"skw");
    } else if(trag==="kasten"){
      const sw=0.09*b, yF=y0+0.16*Lf, yR=y0+0.86*Lf-c;
      T+=wing(yF,b,c,0.7,sw,mainCS)+wing(yR,b,c,0.7,-sw,elev?[[0.1,0.6]]:[]);
      for(const sg of [1,-1]) T+=R(cx+sg*b/2-1.5,yF+sw,3,(yR-sw+0.7*c)-(yF+sw));
      Sd+=poly([[xs(yF+sw),106],[xs(yF+sw)+0.7*c*k,106],[xs(yR-sw)+0.7*c*k,60],[xs(yR-sw),60]],"sk dash")+prof(xs(yF),106,c*k)+prof(xs(yR),60,c*k);
      const yf=104-tan(1.5)*120, yr=64+tan(1.5)*120;
      F+=fw(104,120,1.5)+fw(64,120,-1.5)+L(cx-120,yr,cx-120,yf,"skw")+L(cx+120,yr,cx+120,yf,"skw");
    }
    if(pick.motor==="ja"){
      if(pusher==null){ T+=L(cx-24,y0-4,cx+24,y0-4,"prop"); Sd+=L(18,70,18,120,"prop"); F+=`<circle class="prop" cx="${cx}" cy="95" r="30"/>`; }
      else { T+=L(cx-22,pusher+5,cx+22,pusher+5,"prop"); const xp=xs(pusher)+4; Sd+=L(xp,wy[0]-24,xp,wy[0]+24,"prop"); F+=`<circle class="prop" cx="${cx}" cy="${wy[1]}" r="26"/>`; }
    }
    T+=L(cx-b/2,214,cx+b/2,214,"skd")+L(cx-b/2,209,cx-b/2,219,"skd")+L(cx+b/2,209,cx+b/2,219,"skd")
      +`<text class="skt" x="${cx}" y="229" text-anchor="middle">b = ${pick.spannweite!=null?pick.spannweite:"\u2013"} mm</text>`;
    const front=Fb+(fus?`<circle class="sk" cx="${cx}" cy="95" r="11"/>`:"")+F;
    const svg=(vb,body,lab)=>`<svg viewBox="${vb}" role="img" aria-label="${lab}">${body}</svg>`;
    document.getElementById("sk-top").innerHTML=svg("0 0 300 234",T,"Draufsicht");
    document.getElementById("sk-side").innerHTML=svg("0 45 300 90",Sd,"Seitenansicht");
    document.getElementById("sk-front").innerHTML=svg("0 50 300 80",front,"Vorderansicht");
  }
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
    drawSketch();
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
