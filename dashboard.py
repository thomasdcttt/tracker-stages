"""Génère le tableau de bord HTML local (un seul fichier, aucune dépendance externe)."""
import json
import os
import pathlib
import time
from datetime import datetime


def file_url(path):
    return pathlib.Path(os.path.abspath(path)).as_uri()


PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stages Paris · Tracker</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1c1c1a;--mute:#6b6a65;--line:#e4e2dc;--acc:#1f4fd1;--acc-ink:#fff;
--ibd:#7a3cc4;--pe:#0f7a5c;--vc:#c2570c;--st:#1f4fd1;--am:#0e7490;--co:#a16207;--new:#d11f4f;--ok:#0f7a5c;--err:#b42318}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141413;--card:#1e1e1c;--ink:#ecebe6;
--mute:#9b9a94;--line:#33322f;--acc:#7c9cff;--acc-ink:#0d0d0c;--ibd:#b98cf0;--pe:#4cc79f;--vc:#f29a52;--st:#7c9cff;--am:#5ccfe6;--co:#e8c25a;
--new:#ff6b8f;--ok:#4cc79f;--err:#ff7a6b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:24px 16px 60px}
header{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:8px 24px;margin-bottom:18px}
h1{font-size:22px;margin:0;letter-spacing:-.01em}.sub{color:var(--mute);font-size:13px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:14px 0}
.chip{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:6px 12px;
cursor:pointer;font:inherit;font-size:13px}.chip.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
input[type=search]{flex:1;min-width:180px;border:1px solid var(--line);background:var(--card);color:var(--ink);
border-radius:10px;padding:8px 12px;font:inherit}
.stats{display:flex;gap:18px;flex-wrap:wrap;color:var(--mute);font-size:13px}.stats b{color:var(--ink)}
.list{display:flex;flex-direction:column;gap:8px}
.row{display:grid;grid-template-columns:1fr auto;gap:10px 16px;align-items:center;background:var(--card);
border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.row.applied{opacity:.5}.t{font-weight:600}.co{font-weight:600;color:var(--mute)}
.meta{display:flex;flex-wrap:wrap;gap:6px 12px;color:var(--mute);font-size:12.5px;margin-top:3px}
.tag{font-size:11.5px;font-weight:600;padding:2px 8px;border-radius:999px;border:1px solid currentColor}
.c-ibd{color:var(--ibd)}.c-pe{color:var(--pe)}.c-vc{color:var(--vc)}.c-st{color:var(--st)}.c-am{color:var(--am)}.c-co{color:var(--co)}.c-x{color:var(--mute)}
.new{color:var(--new);font-weight:700}
.act{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
a.btn{background:var(--acc);color:var(--acc-ink);text-decoration:none;padding:7px 14px;border-radius:9px;
font-weight:600;font-size:13px;white-space:nowrap}a.lnk{color:var(--mute);font-size:12.5px}
label.ap{font-size:12.5px;color:var(--mute);display:flex;gap:5px;align-items:center;cursor:pointer}
.src{margin-top:28px;border-top:1px solid var(--line);padding-top:14px;font-size:13px;color:var(--mute)}
.src div{margin:3px 0}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.empty{padding:40px;text-align:center;color:var(--mute);background:var(--card);border-radius:12px;border:1px dashed var(--line)}
@media (max-width:640px){.row{grid-template-columns:1fr}.act{justify-content:flex-start}}
</style></head><body><div class="wrap">
<header><div><h1>Stages Paris · IBD, Marchés, AM &amp; Commodities</h1>
<div class="sub" id="upd"></div></div><div class="stats" id="stats"></div></header>
<div class="bar" id="cats"></div>
<div class="bar"><input type="search" id="q" placeholder="Filtrer (entreprise, poste…)">
<button class="chip" id="f24">Publiées &lt; 48 h</button><button class="chip" id="fap">Masquer postulées</button>
<button class="chip" id="fsum">Masquer summer</button></div>
<div class="list" id="list"></div>
<div class="src" id="src"></div>
</div>
<script>
const OFFERS = __OFFERS__;
const SOURCES = __SOURCES__;
const GEN = __GEN__, NEXT = __NEXT__;
const CATS = {"M&A / IBD":"c-ibd","Private Equity":"c-pe","Venture Capital":"c-vc","Sales & Trading":"c-st","Asset Management":"c-am","Commodities":"c-co"};
function load(k,d){try{return JSON.parse(localStorage.getItem(k))??d}catch(e){return d}}
function save(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
let applied = load("applied",{}), st = load("filters",{cat:"Toutes",q:"",f24:false,fap:false,fsum:false});
const esc = s => String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const DAY=86400;
function pubTs(o){if(o.posted&&/^\d{4}-\d{2}-\d{2}/.test(o.posted)){return Date.parse(o.posted.slice(0,10)+"T12:00:00")/1000}return o.first_seen}
function isFresh(o){return Date.now()/1000-pubTs(o)<2*DAY}
function pubLabel(o){if(!o.posted)return "";const d=Math.floor((Date.now()/1000-pubTs(o)+DAY/2)/DAY);
  if(o.posted_plus)return "Publiée il y a plus de "+(d-1)+" j";
  return d<=0?"Publiée aujourd'hui":d===1?"Publiée hier":"Publiée il y a "+d+" j"}
OFFERS.sort((a,b)=>pubTs(b)-pubTs(a)||b.first_seen-a.first_seen);
const fmt = ts => new Date(ts*1000).toLocaleString("fr-FR",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"});
function ago(ts){const m=Math.round((Date.now()/1000-ts)/60);if(m<60)return "il y a "+m+" min";
const h=Math.round(m/60);if(h<48)return "il y a "+h+" h";return "il y a "+Math.round(h/24)+" j"}
function render(){
  const cats=["Toutes",...Object.keys(CATS)];
  document.getElementById("cats").innerHTML=cats.map(c=>`<button class="chip ${st.cat===c?"on":""}" data-c="${esc(c)}">${esc(c)} (${c==="Toutes"?OFFERS.length:OFFERS.filter(o=>o.category===c).length})</button>`).join("");
  document.querySelectorAll("#cats .chip").forEach(b=>b.onclick=()=>{st.cat=b.dataset.c;save("filters",st);render()});
  ["f24","fap","fsum"].forEach(id=>{const b=document.getElementById(id);b.classList.toggle("on",!!st[id]);
    b.onclick=()=>{st[id]=!st[id];save("filters",st);render()}});
  const q=document.getElementById("q");q.value=st.q;q.oninput=()=>{st.q=q.value;save("filters",st);render()};
  const now=Date.now()/1000, ql=st.q.toLowerCase();
  const rows=OFFERS.filter(o=>(st.cat==="Toutes"||o.category===st.cat)&&(!st.f24||isFresh(o))
    &&(!st.fap||!applied[o.uid])&&(!st.fsum||!o.summer)
    &&(!ql||(o.title+" "+o.company+" "+o.location+" "+o.source).toLowerCase().includes(ql)));
  const L=document.getElementById("list");
  if(!rows.length){L.innerHTML=`<div class="empty">${OFFERS.length?"Aucune offre avec ces filtres.":"Aucune offre pour l'instant. Le tracker cherche en continu, tu seras notifié dès qu'une offre apparaît."}</div>`}
  else L.innerHTML=rows.map(o=>{
    const isNew=isFresh(o), link=o.apply_url||o.url;
    const others=(o.others||[]).map(x=>`<a class="lnk" href="${esc(x.apply_url||x.url)}" target="_blank" rel="noopener">${esc(x.source)}</a>`).join(" ");
    return `<div class="row ${applied[o.uid]?"applied":""}"><div>
      <div><span class="co">${esc(o.company||"—")}</span> · <span class="t">${esc(o.title)}</span></div>
      <div class="meta"><span class="tag ${CATS[o.category]||"c-x"}">${esc(o.category)}</span>
      ${o.summer?'<span class="tag c-x">Summer</span>':""}
      ${isNew?'<span class="new">NOUVEAU</span>':""}<span>${esc(o.location||"Paris")}</span>
      ${o.posted?`<span><b>${pubLabel(o)}</b> (${esc(o.posted.slice(0,10))})</span>`:""}<span>Détectée ${ago(o.first_seen)}</span>
      <span>via ${esc(o.source)}</span></div></div>
      <div class="act"><a class="btn" href="${esc(link)}" target="_blank" rel="noopener">${o.apply_url&&o.apply_url!==o.url?"Postuler (site carrière)":"Voir et postuler"}</a>
      ${o.apply_url&&o.apply_url!==o.url?`<a class="lnk" href="${esc(o.url)}" target="_blank" rel="noopener">Offre ${esc(o.source)}</a>`:""}${others}
      <label class="ap"><input type="checkbox" data-u="${esc(o.uid)}" ${applied[o.uid]?"checked":""}>Postulé</label></div></div>`}).join("");
  L.querySelectorAll("input[type=checkbox]").forEach(c=>c.onchange=()=>{if(c.checked)applied[c.dataset.u]=Date.now();else delete applied[c.dataset.u];save("applied",applied);render()});
  const n24=OFFERS.filter(isFresh).length, nap=OFFERS.filter(o=>applied[o.uid]).length;
  document.getElementById("stats").innerHTML=`<span><b>${OFFERS.length}</b> offres</span><span><b>${n24}</b> publiées depuis 48 h</span><span><b>${nap}</b> postulées</span>`;
  document.getElementById("upd").textContent="Mis à jour "+fmt(GEN)+(NEXT?" · prochaine recherche vers "+new Date(NEXT*1000).toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"}):"")+" · la page se recharge seule";
  document.getElementById("src").innerHTML="<b>Sources</b>"+(SOURCES.length?SOURCES.map(s=>`<div><span class="dot" style="background:var(${s.ok?"--ok":"--err"})"></span>${esc(s.name)} · ${esc(s.message)} · ${fmt(s.last_run)}</div>`).join(""):"<div>Première recherche en cours…</div>");
}
render();
// Recharge sans le cache du navigateur (GitHub Pages garde les pages 10 min en cache)
setTimeout(()=>{location.replace(location.pathname+"?t="+Date.now())},120000);
</script></body></html>"""


def write(path, offers, sources, next_run, interval):
    def js(obj):
        # Empêche toute fermeture de balise </script> via les données
        return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")
    html = (PAGE.replace("__OFFERS__", js(offers)).replace("__SOURCES__", js(sources))
            .replace("__GEN__", js(time.time())).replace("__NEXT__", js(next_run)))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    os.replace(tmp, path)  # écriture atomique : jamais de page à moitié écrite
