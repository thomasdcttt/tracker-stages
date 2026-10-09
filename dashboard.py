"""Tableau de bord : une page HTML autonome (aucune dépendance externe) + data.json pour les mises à jour.

La page affiche les offres, l'onglet Candidatures (synchronisé et chiffré dans le dépôt GitHub)
et les réglages (synchronisation, entreprises prioritaires).
"""
import json
import os
import pathlib


def file_url(path):
    return pathlib.Path(os.path.abspath(path)).as_uri()


def _js(obj):
    # Empêche toute fermeture de balise </script> via les données
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def _atomic(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)  # écriture atomique : jamais de fichier à moitié écrit


def write(path, payload):
    _atomic(path, PAGE.replace("__DATA__", _js(payload)))
    _atomic(os.path.join(os.path.dirname(path) or ".", "data.json"), json.dumps(payload, ensure_ascii=False))


PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="dark light">
<title>Stages Paris</title>
<style>
:root{
  --bg:#0b0d12;--bg2:#10131a;--card:#141823;--card2:#191e2b;--line:#232a3a;--line2:#2e3649;
  --ink:#eef1f7;--mute:#8c95a8;--mute2:#5f687b;
  --acc:#7c8cff;--acc2:#a78bfa;--ok:#34d399;--warn:#fbbf24;--err:#f87171;--star:#fbbf24;
  --ibd:#b794f6;--pe:#34d399;--vc:#fb923c;--st:#7c8cff;--am:#22d3ee;--co:#facc15;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -12px rgba(0,0,0,.6);
  --r:14px;--ease:cubic-bezier(.2,.8,.2,1);
}
@media (prefers-color-scheme:light){:root{
  --bg:#f5f6fa;--bg2:#eceef4;--card:#ffffff;--card2:#f8f9fc;--line:#e3e6ee;--line2:#d4d8e3;
  --ink:#141824;--mute:#5e6678;--mute2:#8a92a3;--acc:#4f5ff0;--acc2:#7c5cf0;
  --ok:#059669;--warn:#b45309;--err:#dc2626;--star:#d97706;
  --ibd:#7c3aed;--pe:#059669;--vc:#ea580c;--st:#4f5ff0;--am:#0891b2;--co:#a16207;
  --shadow:0 1px 2px rgba(16,24,40,.05),0 8px 24px -14px rgba(16,24,40,.18);
}}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink)}
body{font:14.5px/1.45 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;
  -webkit-font-smoothing:antialiased;min-height:100vh}
body::before{content:"";position:fixed;inset:-20% -10% auto;height:520px;pointer-events:none;z-index:0;
  background:radial-gradient(600px 300px at 15% 20%,color-mix(in srgb,var(--acc) 18%,transparent),transparent 70%),
  radial-gradient(500px 260px at 85% 0%,color-mix(in srgb,var(--acc2) 14%,transparent),transparent 70%)}
a{color:inherit}
button,input,select,textarea{font:inherit;color:inherit}
.num{font-variant-numeric:tabular-nums}
.top{position:sticky;top:0;z-index:20;backdrop-filter:saturate(140%) blur(10px);-webkit-backdrop-filter:saturate(140%) blur(10px);
  background:color-mix(in srgb,var(--bg) 78%,transparent);border-bottom:1px solid var(--line)}
.top-in{max-width:1180px;margin:0 auto;padding:12px 18px 0;display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px}
.brand{display:flex;align-items:center;gap:11px;margin-right:auto}
.logo{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;font-weight:800;font-size:13px;letter-spacing:.02em;
  color:#fff;background:linear-gradient(135deg,var(--acc),var(--acc2));box-shadow:0 6px 18px -6px var(--acc)}
.brand h1{font-size:16px;margin:0;letter-spacing:-.01em}
.live{display:flex;align-items:center;gap:7px;color:var(--mute);font-size:12.5px}
.dot{width:7px;height:7px;border-radius:50%;background:var(--ok);position:relative;flex:none;display:inline-block}
.dot.pulse::after{content:"";position:absolute;inset:0;border-radius:50%;background:inherit;animation:ping 2.4s var(--ease) infinite}
@keyframes ping{0%{transform:scale(1);opacity:.7}80%,100%{transform:scale(3);opacity:0}}
.actions-top{display:flex;align-items:center;gap:8px}
.pill{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);background:var(--card);border-radius:999px;
  padding:6px 11px;font-size:12.5px;color:var(--mute);cursor:pointer;transition:border-color .2s,color .2s}
.pill:hover{border-color:var(--line2);color:var(--ink)}
.iconbtn{width:34px;height:34px;border-radius:10px;border:1px solid var(--line);background:var(--card);display:grid;place-items:center;
  cursor:pointer;transition:transform .3s var(--ease),border-color .2s}
.iconbtn:hover{transform:rotate(45deg);border-color:var(--line2)}
.tabs{flex-basis:100%;display:flex;gap:4px;position:relative}
.tab{appearance:none;border:0;background:none;padding:10px 12px 12px;cursor:pointer;color:var(--mute);font-weight:600;font-size:14px;
  display:flex;align-items:center;gap:8px;transition:color .2s}
.tab[aria-selected=true]{color:var(--ink)}
.tab .cnt{font-size:11.5px;padding:1px 7px;border-radius:999px;background:var(--bg2);color:var(--mute);font-weight:600}
.ink{position:absolute;left:0;bottom:-1px;height:2px;width:0;border-radius:2px;background:linear-gradient(90deg,var(--acc),var(--acc2));
  transition:transform .35s var(--ease),width .35s var(--ease);will-change:transform}
main{position:relative;z-index:1;max-width:1180px;margin:0 auto;padding:20px 18px 80px}
.view{display:none}.view.on{display:block;animation:fadeIn .35s var(--ease)}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:14px 16px;box-shadow:var(--shadow);
  cursor:pointer;transition:transform .25s var(--ease),border-color .25s}
.stat:hover{transform:translateY(-2px);border-color:var(--line2)}
.stat .k{color:var(--mute);font-size:12.5px;display:flex;align-items:center;gap:6px}
.stat .v{font-size:26px;font-weight:750;letter-spacing:-.02em;margin-top:2px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px}
.chips{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px;flex:1 1 100%}
.chips::-webkit-scrollbar{display:none}
.chip{flex:none;border:1px solid var(--line);background:var(--card);color:var(--mute);border-radius:999px;padding:7px 12px;font-size:13px;
  cursor:pointer;display:inline-flex;align-items:center;gap:7px;transition:background .2s,color .2s,border-color .2s;user-select:none}
.chip:hover{color:var(--ink);border-color:var(--line2)}
.chip.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.chip .cd{width:8px;height:8px;border-radius:50%}
.chip .n{opacity:.7;font-size:12px}
.search{flex:1 1 260px;position:relative}
.search input{width:100%;border:1px solid var(--line);background:var(--card);border-radius:12px;padding:10px 12px 10px 36px;outline:none;
  transition:border-color .2s,box-shadow .2s}
.search input:focus{border-color:var(--acc);box-shadow:0 0 0 4px color-mix(in srgb,var(--acc) 18%,transparent)}
.search svg{position:absolute;left:12px;top:50%;transform:translateY(-50%);opacity:.5}
.toggles{display:flex;gap:6px;flex-wrap:wrap}
.list{display:flex;flex-direction:column;gap:10px}
.card{position:relative;display:grid;grid-template-columns:auto 1fr auto;gap:14px;align-items:center;background:var(--card);
  border:1px solid var(--line);border-radius:var(--r);padding:14px 16px;box-shadow:var(--shadow);
  transition:transform .25s var(--ease),border-color .25s;content-visibility:auto;contain-intrinsic-size:auto 90px}
.card:hover{transform:translateY(-2px);border-color:var(--line2)}
.card.enter{animation:rise .5s var(--ease) both;animation-delay:calc(var(--i,0) * 35ms)}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.card.prio{border:1px solid transparent;
  background:linear-gradient(var(--card),var(--card)) padding-box,linear-gradient(120deg,color-mix(in srgb,var(--star) 75%,transparent),var(--line) 50%) border-box}
.card.closed{opacity:.55}
.av{width:40px;height:40px;border-radius:11px;display:grid;place-items:center;font-weight:750;font-size:14px;color:#fff;flex:none;letter-spacing:.02em}
.ttl{font-weight:650;font-size:15px;line-height:1.3}
.co{color:var(--mute);font-weight:600;font-size:13px;margin-bottom:2px;display:flex;gap:6px;align-items:center}
.meta{display:flex;flex-wrap:wrap;gap:6px 12px;color:var(--mute);font-size:12.5px;margin-top:6px;align-items:center}
.meta a{color:var(--mute)}
.tag{font-size:11.5px;font-weight:650;padding:2px 9px;border-radius:999px;background:color-mix(in srgb,currentColor 13%,transparent)}
.new{color:var(--err);font-weight:750;font-size:11.5px;letter-spacing:.04em}
.star{color:var(--star)}
.right{display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end}
.btn{appearance:none;border:1px solid var(--line);background:var(--card2);border-radius:10px;padding:8px 12px;font-weight:600;font-size:13px;
  cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:6px;white-space:nowrap;
  transition:transform .15s var(--ease),background .2s,border-color .2s,filter .2s}
.btn:hover{border-color:var(--line2)}
.btn:active{transform:scale(.97)}
.btn.primary{background:linear-gradient(135deg,var(--acc),var(--acc2));color:#fff;border-color:transparent;box-shadow:0 6px 16px -8px var(--acc)}
.btn.primary:hover{filter:brightness(1.08)}
.btn.ghost{background:none}
.btn.danger{color:var(--err)}
.status{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:6px 11px;font-size:12.5px;font-weight:650;cursor:pointer;
  border:1px solid transparent;background:color-mix(in srgb,currentColor 13%,transparent);transition:transform .15s var(--ease)}
.status:active{transform:scale(.96)}
.status i{width:7px;height:7px;border-radius:50%;background:currentColor}
.empty{padding:46px 20px;text-align:center;color:var(--mute);border:1px dashed var(--line2);border-radius:var(--r)}
.more{display:flex;justify-content:center;margin-top:14px}
details.src{margin-top:26px;border-top:1px solid var(--line);padding-top:12px;color:var(--mute);font-size:13px}
details.src summary{cursor:pointer;font-weight:650;color:var(--ink);list-style:none;display:flex;gap:8px;align-items:center}
details.src summary::-webkit-details-marker{display:none}
details.src summary::before{content:"▸";transition:transform .2s var(--ease);display:inline-block}
details.src[open] summary::before{transform:rotate(90deg)}
.srcgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:6px 18px;margin-top:10px}
.srcrow{display:flex;gap:8px;align-items:baseline}
.pipe{display:flex;height:10px;border-radius:999px;overflow:hidden;background:var(--bg2);margin:6px 0 16px}
.pipe span{height:100%;transition:width .6s var(--ease)}
.kanban{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(250px,1fr);gap:12px;overflow-x:auto;padding-bottom:10px;scroll-snap-type:x proximity}
.col{background:var(--bg2);border:1px solid var(--line);border-radius:var(--r);padding:10px;min-height:120px;scroll-snap-align:start;
  transition:background .2s,border-color .2s}
.col.drop{border-color:var(--acc);background:color-mix(in srgb,var(--acc) 8%,var(--bg2))}
.colh{display:flex;align-items:center;gap:8px;font-weight:700;font-size:13px;padding:4px 4px 10px}
.colh .n{margin-left:auto;color:var(--mute);font-weight:600}
.kc{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:11px 12px;margin-bottom:8px;cursor:grab;
  box-shadow:var(--shadow);transition:transform .2s var(--ease),border-color .2s,opacity .2s}
.kc:hover{transform:translateY(-2px);border-color:var(--line2)}
.kc.drag{opacity:.4}
.kc .t{font-weight:650;font-size:13.5px;margin-top:2px}
.kc .c{font-size:12.5px;color:var(--mute);font-weight:600}
.kc .m{font-size:12px;color:var(--mute2);margin-top:6px;display:flex;gap:8px;flex-wrap:wrap}
.kc .m a{color:var(--mute)}
.kc .note{font-size:12.5px;color:var(--mute);margin-top:6px;white-space:pre-wrap;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.colempty{font-size:12px;color:var(--mute2);text-align:center;padding:14px 6px;border:1px dashed var(--line);border-radius:10px}
.banner{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap;border:1px solid var(--line);
  background:linear-gradient(120deg,color-mix(in srgb,var(--acc) 12%,var(--card)),var(--card));border-radius:var(--r);padding:12px 14px;margin-bottom:14px}
dialog{border:1px solid var(--line2);background:var(--card);color:var(--ink);border-radius:18px;padding:0;width:min(560px,94vw);
  box-shadow:0 30px 80px -20px rgba(0,0,0,.6)}
dialog[open]{animation:pop .28s var(--ease)}
@keyframes pop{from{opacity:0;transform:translateY(8px) scale(.97)}to{opacity:1;transform:none}}
dialog::backdrop{background:rgba(5,7,12,.55)}
.dlg{padding:20px 22px 18px}
.dlg h2{margin:0 0 4px;font-size:18px}
.dlg p.sub{margin:0 0 14px;color:var(--mute);font-size:13px}
.field{display:flex;flex-direction:column;gap:6px;margin-bottom:12px}
.field label{font-size:12.5px;color:var(--mute);font-weight:600}
.field input,.field select,.field textarea{border:1px solid var(--line);background:var(--bg2);border-radius:10px;padding:9px 11px;outline:none;
  transition:border-color .2s,box-shadow .2s;width:100%}
.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--acc);box-shadow:0 0 0 4px color-mix(in srgb,var(--acc) 16%,transparent)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.dlgfoot{display:flex;gap:8px;justify-content:flex-end;padding-top:6px;flex-wrap:wrap}
.dlgfoot .l{margin-right:auto}
.ptags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}
.ptag{display:inline-flex;align-items:center;gap:6px;background:color-mix(in srgb,var(--star) 14%,transparent);color:var(--star);
  border-radius:999px;padding:5px 6px 5px 11px;font-size:12.5px;font-weight:650;animation:pop .25s var(--ease)}
.ptag button{border:0;background:none;color:inherit;cursor:pointer;padding:0 4px;font-size:15px;line-height:1}
.hint{font-size:12px;color:var(--mute);margin-bottom:12px}
hr.sep{border:0;border-top:1px solid var(--line);margin:16px 0}
.menu{position:fixed;z-index:50;background:var(--card);border:1px solid var(--line2);border-radius:12px;padding:6px;min-width:200px;
  box-shadow:0 20px 50px -15px rgba(0,0,0,.55);animation:pop .18s var(--ease)}
.menu button{display:flex;width:100%;align-items:center;gap:9px;border:0;background:none;padding:8px 10px;border-radius:8px;cursor:pointer;font-size:13px;text-align:left}
.menu button:hover{background:var(--bg2)}
.menu i{width:8px;height:8px;border-radius:50%}
.toasts{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:60;display:flex;flex-direction:column;gap:8px;align-items:center;pointer-events:none;width:max-content;max-width:92vw}
.toast{pointer-events:auto;display:flex;align-items:center;gap:12px;background:var(--ink);color:var(--bg);border-radius:12px;padding:10px 12px 10px 14px;
  font-size:13.5px;box-shadow:0 14px 40px -12px rgba(0,0,0,.5);animation:toastIn .35s var(--ease)}
.toast.out{animation:toastOut .3s var(--ease) forwards}
.toast button{border:0;background:color-mix(in srgb,var(--bg) 18%,transparent);color:inherit;border-radius:8px;padding:5px 9px;font-weight:650;cursor:pointer}
@keyframes toastIn{from{opacity:0;transform:translateY(12px) scale(.98)}}
@keyframes toastOut{to{opacity:0;transform:translateY(8px)}}
@media (max-width:760px){
  .stats{grid-template-columns:repeat(2,1fr)}
  .card{grid-template-columns:auto 1fr;padding:13px}
  .right{grid-column:1/-1;justify-content:flex-start}
  .lt{display:none}
  .toggles{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;flex:1 1 100%}
  .toggles::-webkit-scrollbar{display:none}
  .row2{grid-template-columns:1fr}
  .top-in{padding:10px 14px 0}
  main{padding:16px 14px 80px}
}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
</style></head>
<body>
<header class="top"><div class="top-in">
  <div class="brand"><div class="logo">TS</div><div><h1>Stages Paris</h1>
    <div class="live"><span class="dot pulse" id="liveDot"></span><span id="upd" class="num"></span></div></div></div>
  <div class="actions-top">
    <button class="pill" id="syncPill" title="Synchronisation des candidatures"><span class="dot" id="syncDot"></span><span id="syncTxt">Local</span></button>
    <button class="iconbtn" id="openSettings" title="Réglages" aria-label="Réglages">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
    </button>
  </div>
  <nav class="tabs" role="tablist">
    <button class="tab" role="tab" data-view="offres" aria-selected="true">Offres <span class="cnt num" id="cntOffres">0</span></button>
    <button class="tab" role="tab" data-view="cand" aria-selected="false">Candidatures <span class="cnt num" id="cntCand">0</span></button>
    <span class="ink" id="ink"></span>
  </nav>
</div></header>

<main>
<section class="view on" id="view-offres">
  <div class="stats">
    <div class="stat" data-go="all"><div class="k">Offres actives</div><div class="v num" id="sAll">0</div></div>
    <div class="stat" data-go="fresh"><div class="k"><span class="dot" style="background:var(--err)"></span>Publiées &lt; 48 h</div><div class="v num" id="sFresh">0</div></div>
    <div class="stat" data-go="prio"><div class="k"><span class="star">★</span>Prioritaires</div><div class="v num" id="sPrio">0</div></div>
    <div class="stat" data-go="cand"><div class="k">Candidatures en cours</div><div class="v num" id="sCand">0</div></div>
  </div>
  <div class="bar"><div class="chips" id="cats"></div></div>
  <div class="bar">
    <div class="search"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input id="q" type="search" placeholder="Rechercher une entreprise, un poste…" autocomplete="off"></div>
    <div class="toggles">
      <button class="chip" data-t="fresh">Publiées &lt; 48 h</button>
      <button class="chip" data-t="prio">★ Prioritaires</button>
      <button class="chip" data-t="hideTracked">Masquer suivies</button>
      <button class="chip" data-t="hideSummer">Masquer summer</button>
      <button class="chip" data-t="showClosed">Afficher fermées</button>
    </div>
  </div>
  <div class="list" id="list"></div>
  <div class="more" id="more"></div>
  <details class="src" id="srcBox"><summary><span>Sources</span><span id="srcSum" style="color:var(--mute);font-weight:500"></span></summary><div class="srcgrid" id="src"></div></details>
</section>

<section class="view" id="view-cand">
  <div class="banner" id="syncBanner" hidden>
    <div><b>Synchronisation désactivée.</b> <span style="color:var(--mute)">Tes candidatures ne sont enregistrées que sur cet appareil.</span></div>
    <button class="btn primary" id="bannerSetup">Activer</button>
  </div>
  <div class="bar" style="justify-content:space-between">
    <div class="search" style="max-width:420px"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input id="qc" type="search" placeholder="Rechercher une candidature…" autocomplete="off"></div>
    <button class="btn primary" id="addCand">＋ Ajouter une candidature</button>
  </div>
  <div class="chips" id="pipeLegend" style="margin-bottom:4px"></div>
  <div class="pipe" id="pipe"></div>
  <div class="kanban" id="kanban"></div>
</section>
</main>

<dialog id="dlgCand"><form class="dlg" method="dialog" id="formCand">
  <h2 id="dcTitle">Candidature</h2><p class="sub" id="dcSub">Suis l'avancement de cette candidature.</p>
  <div class="row2"><div class="field"><label for="fCompany">Entreprise</label><input id="fCompany" name="company" required></div>
  <div class="field"><label for="fTitle">Poste</label><input id="fTitle" name="title" required></div></div>
  <div class="row2"><div class="field"><label for="dcStatus">Statut</label><select name="status" id="dcStatus"></select></div>
  <div class="field"><label for="fApplied">Date de candidature</label><input id="fApplied" name="applied" type="date"></div></div>
  <div class="field"><label for="fUrl">Lien de l'offre</label><input id="fUrl" name="url" type="url" placeholder="https://…"></div>
  <div class="field"><label for="fNotes">Notes</label><textarea id="fNotes" name="notes" rows="3" placeholder="Contact, prochaine étape, date d'entretien…"></textarea></div>
  <div class="dlgfoot"><button type="button" class="btn ghost danger l" id="dcDelete">Supprimer</button>
    <button type="button" class="btn ghost" id="dcCancel">Annuler</button><button type="submit" class="btn primary" value="ok">Enregistrer</button></div>
</form></dialog>

<dialog id="dlgSet"><div class="dlg">
  <h2>Réglages</h2><p class="sub">La clé et le code restent sur cet appareil. La liste des entreprises prioritaires est partagée avec le tracker.</p>
  <div class="field"><label>Entreprises prioritaires</label></div>
  <div class="ptags" id="ptags"></div>
  <div class="row2" style="grid-template-columns:1fr auto;align-items:center"><div class="field" style="margin:0"><input id="pnew" placeholder="Ajouter une entreprise (ex. Evercore)"></div>
    <button type="button" class="btn" id="padd">Ajouter</button></div>
  <div class="hint" style="margin-top:8px">Leurs offres passent en tête, avec une notification prioritaire sur ton téléphone.</div>
  <hr class="sep">
  <div class="field"><label>Synchronisation des candidatures</label>
    <div class="hint" style="margin:0">Une clé GitHub avec l'accès « Contents » en lecture et écriture sur ton dépôt, et un code secret de ton choix qui chiffre tes candidatures. Mets la même clé et le même code sur ton Mac et ton téléphone.</div></div>
  <div class="field"><label for="tok">Clé GitHub</label><input id="tok" type="password" autocomplete="off" placeholder="github_pat_…"></div>
  <div class="field"><label for="pass">Code secret</label><input id="pass" type="password" autocomplete="off" placeholder="Au moins 6 caractères"></div>
  <div class="hint" id="setMsg"></div>
  <div class="dlgfoot"><button type="button" class="btn ghost l" id="setOff">Désactiver la synchro</button>
    <button type="button" class="btn ghost" id="setCancel">Fermer</button><button type="button" class="btn primary" id="setSave">Enregistrer et tester</button></div>
</div></dialog>

<div class="toasts" id="toasts"></div>

<script>
"use strict";
let DATA = __DATA__;
const $ = s => document.querySelector(s), $$ = s => Array.from(document.querySelectorAll(s));
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const safeUrl = u => /^https?:\/\//i.test(String(u || "")) ? String(u) : "#";
const LS = {
  get(k, d){ try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch(e){ return d; } },
  set(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); } catch(e){} },
  del(k){ try { localStorage.removeItem(k); } catch(e){} }
};
const DAY = 86400;
const CATS = [["M&A / IBD","--ibd"],["Private Equity","--pe"],["Venture Capital","--vc"],["Sales & Trading","--st"],
              ["Asset Management","--am"],["Commodities","--co"]];
const CATVAR = Object.fromEntries(CATS);
const STATUSES = [["a_postuler","À postuler","--mute"],["postule","Postulé","--acc"],["test","Test en ligne","--am"],
                  ["entretien","Entretiens","--acc2"],["offre","Offre reçue","--ok"],["refuse","Refusé","--err"],["abandon","Abandonné","--mute2"]];
const ST = Object.fromEntries(STATUSES.map(s => [s[0], {label:s[1], v:s[2]}]));
const IN_PROGRESS = new Set(["postule","test","entretien","offre"]);

const compact = s => String(s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
function pubTs(o){ if (o.posted && /^\d{4}-\d{2}-\d{2}/.test(o.posted)) return Date.parse(o.posted.slice(0,10) + "T12:00:00") / 1000; return o.first_seen; }
const nowS = () => Date.now() / 1000;
const isFresh = o => nowS() - pubTs(o) < 2 * DAY;
function pubLabel(o){ if (!o.posted) return "";
  const d = Math.floor((nowS() - pubTs(o) + DAY / 2) / DAY);
  if (o.posted_plus) return "Publiée il y a plus de " + Math.max(1, d - 1) + " j";
  return d <= 0 ? "Publiée aujourd'hui" : d === 1 ? "Publiée hier" : "Publiée il y a " + d + " j"; }
const hm = ts => new Date(ts * 1000).toLocaleTimeString("fr-FR", {hour:"2-digit", minute:"2-digit"});
const dshort = ms => new Date(ms).toLocaleDateString("fr-FR", {day:"numeric", month:"short"});
const today = () => { const d = new Date(); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); };
function hueOf(s){ let h = 0; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return h % 360; }
function initials(s){ const w = String(s || "?").replace(/[^A-Za-zÀ-ÿ0-9 ]/g, " ").split(/\s+/).filter(Boolean);
  if (!w.length) return "?"; return (w[0][0] + (w.length > 1 ? w[1][0] : (w[0][1] || ""))).toUpperCase(); }
function debounce(fn, ms){ let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
function countUp(el, to){ const from = +(el.dataset.v || 0); el.dataset.v = to; if (from === to){ el.textContent = to; return; }
  const t0 = performance.now(), dur = 650;
  const step = t => { const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(from + (to - from) * e); if (p < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step); }
function toast(msg, action, fn, ms){
  const el = document.createElement("div"); el.className = "toast";
  el.innerHTML = "<span>" + esc(msg) + "</span>" + (action ? "<button type='button'>" + esc(action) + "</button>" : "");
  const close = () => { if (el.classList.contains("out")) return; el.classList.add("out"); setTimeout(() => el.remove(), 300); };
  if (action) el.querySelector("button").onclick = () => { close(); fn(); };
  $("#toasts").appendChild(el);
  while ($("#toasts").children.length > 3) $("#toasts").firstChild.remove();
  setTimeout(close, ms || (action ? 7000 : 3000));
}

/* ---------- état ---------- */
let F = Object.assign({cat:"Toutes", fresh:false, prio:false, hideTracked:false, hideSummer:false, showClosed:false}, LS.get("ts_filters", {}));
F.q = "";
const saveF = () => { const c = Object.assign({}, F); delete c.q; LS.set("ts_filters", c); };
let LIMIT = 60;
let PRIO = (LS.get("ts_prio_local", null) || DATA.priority || []).slice();
const isPrio = o => { const c = compact(o.company); return !!c && PRIO.some(p => { const k = compact(p); return k.length >= 2 && c.includes(k); }); };

/* ---------- candidatures ---------- */
let CAND = LS.get("ts_cands", null);
if (!CAND || typeof CAND.items !== "object" || !CAND.items) CAND = {v:1, items:{}, del:{}};
if (!CAND.del) CAND.del = {};
(function migrateOld(){ // anciennes cases « Postulé » de la version précédente du site
  if (LS.get("ts_migrated", false)) return;
  const old = LS.get("applied", null); LS.set("ts_migrated", true); if (!old) return;
  const byUid = Object.fromEntries((DATA.offers || []).map(o => [o.uid, o]));
  for (const [uid, ts] of Object.entries(old)) { const o = byUid[uid], id = "o:" + uid; if (!o || CAND.items[id]) continue;
    CAND.items[id] = {id, offer:uid, company:o.company, title:o.title, url:o.apply_url || o.url, status:"postule",
      applied:new Date(ts).toISOString().slice(0,10), notes:"", created:ts, u:ts, hist:[["postule", ts]]}; }
  LS.set("ts_cands", CAND);
})();
function merge(a, b){
  const out = {v:1, items:{}, del:Object.assign({}, a.del || {})};
  for (const [k, t] of Object.entries(b.del || {})) out.del[k] = Math.max(out.del[k] || 0, t);
  for (const src of [a.items || {}, b.items || {}]) for (const [k, it] of Object.entries(src)) {
    if (!out.items[k] || (it.u || 0) > (out.items[k].u || 0)) out.items[k] = it; }
  for (const [k, t] of Object.entries(out.del)) if (out.items[k] && (out.items[k].u || 0) <= t) delete out.items[k];
  return out;
}
const candFor = uid => CAND.items["o:" + uid];
function saveCand(it){ it.u = Date.now(); CAND.items[it.id] = it; delete CAND.del[it.id]; LS.set("ts_cands", CAND); Sync.schedule(); renderAll(); }
function deleteCand(id){ delete CAND.items[id]; CAND.del[id] = Date.now(); LS.set("ts_cands", CAND); Sync.schedule(); renderAll(); }
function setStatus(it, st){ if (!it || it.status === st) return; it = Object.assign({}, it); it.status = st;
  it.hist = (it.hist || []).concat([[st, Date.now()]]); if (st === "postule" && !it.applied) it.applied = today(); saveCand(it); }
function trackOffer(o, st){ const id = "o:" + o.uid, it = CAND.items[id];
  if (it) { setStatus(it, st); return; }
  saveCand({id, offer:o.uid, company:o.company || "", title:o.title, url:o.apply_url || o.url, status:st,
            applied:st === "postule" ? today() : "", notes:"", created:Date.now(), hist:[[st, Date.now()]]}); }

/* ---------- synchronisation chiffrée via l'API GitHub ---------- */
const Sync = (() => {
  const REPO = DATA.repo || (location.hostname.endsWith(".github.io") && location.pathname.split("/")[1]
    ? location.hostname.split(".")[0] + "/" + location.pathname.split("/")[1] : null);
  const FILE = "data/candidatures.json", PFILE = "data/prioritaires.json";
  let sha = null, psha = null, busy = false, again = false, keyCache = {};
  const tok = () => LS.get("ts_token", ""), pass = () => LS.get("ts_pass", "");
  const enabled = () => !!(REPO && tok() && pass() && window.crypto && crypto.subtle);
  const enc = new TextEncoder(), dec = new TextDecoder();
  const b64 = u8 => { let s = ""; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); };
  const unb64 = s => Uint8Array.from(atob(String(s).replace(/\s/g, "")), c => c.charCodeAt(0));
  async function key(p, salt){ const id = p + "|" + b64(salt); if (keyCache[id]) return keyCache[id];
    const base = await crypto.subtle.importKey("raw", enc.encode(p), "PBKDF2", false, ["deriveKey"]);
    return keyCache[id] = await crypto.subtle.deriveKey({name:"PBKDF2", salt, iterations:150000, hash:"SHA-256"}, base,
      {name:"AES-GCM", length:256}, false, ["encrypt","decrypt"]); }
  async function encrypt(obj){ const salt = crypto.getRandomValues(new Uint8Array(16)), iv = crypto.getRandomValues(new Uint8Array(12));
    const ct = new Uint8Array(await crypto.subtle.encrypt({name:"AES-GCM", iv}, await key(pass(), salt), enc.encode(JSON.stringify(obj))));
    return JSON.stringify({v:1, alg:"AES-GCM", kdf:"PBKDF2-SHA256", it:150000, salt:b64(salt), iv:b64(iv), ct:b64(ct)}); }
  async function decrypt(text){ const o = JSON.parse(text);
    const pt = await crypto.subtle.decrypt({name:"AES-GCM", iv:unb64(o.iv)}, await key(pass(), unb64(o.salt)), unb64(o.ct));
    return JSON.parse(dec.decode(pt)); }
  function api(path, opt){ opt = opt || {};
    return fetch("https://api.github.com/repos/" + REPO + "/contents/" + path, Object.assign({cache:"no-store"}, opt,
      {headers:Object.assign({"Accept":"application/vnd.github+json", "Authorization":"Bearer " + tok()}, opt.headers || {})})); }
  async function getFile(path){ const r = await api(path + "?t=" + Date.now());
    if (r.status === 404) return {text:null, sha:null};
    if (!r.ok) throw new Error("GitHub " + r.status);
    const j = await r.json(); return {text:dec.decode(unb64(j.content || "")), sha:j.sha}; }
  function putFile(path, text, s, msg){
    return api(path, {method:"PUT", headers:{"Content-Type":"application/json"},
      body:JSON.stringify(Object.assign({message:msg, content:b64(enc.encode(text))}, s ? {sha:s} : {}))}); }
  function show(st, txt){ const dot = $("#syncDot");
    dot.style.background = st === "ok" ? "var(--ok)" : st === "busy" ? "var(--warn)" : st === "err" ? "var(--err)" : "var(--mute2)";
    $("#syncTxt").textContent = txt; $("#syncBanner").hidden = enabled(); }
  async function pull(){ if (!enabled()) { show("off", "Local"); return; }
    show("busy", "Synchronisation…");
    try {
      const f = await getFile(FILE); sha = f.sha;
      if (f.text) { let remote; try { remote = await decrypt(f.text); } catch(e){ const er = new Error("decrypt"); throw er; }
        CAND = merge(CAND, remote); LS.set("ts_cands", CAND); }
      const p = await getFile(PFILE); psha = p.sha;
      if (p.text) { try { const pj = JSON.parse(p.text); if (Array.isArray(pj.companies)) { PRIO = pj.companies.slice(); LS.set("ts_prio_local", PRIO); } } catch(e){} }
      show("ok", "Synchronisé"); renderAll();
      if (f.text === null && Object.keys(CAND.items).length) schedule();
    } catch(e) { show("err", e.message === "decrypt" ? "Code secret incorrect" : "Erreur de synchro"); throw e; }
  }
  async function push(){ if (!enabled()) return; if (busy) { again = true; return; }
    busy = true; show("busy", "Enregistrement…");
    try {
      let done = false;
      for (let attempt = 0; attempt < 4 && !done; attempt++) {
        const r = await putFile(FILE, await encrypt(CAND), sha, "Candidatures : mise à jour");
        if (r.ok) { sha = (await r.json()).content.sha; done = true; break; }
        if (r.status === 409 || r.status === 422) { // modifié ailleurs entre-temps : fusion puis nouvel essai
          const f = await getFile(FILE); sha = f.sha; if (f.text) { CAND = merge(CAND, await decrypt(f.text)); LS.set("ts_cands", CAND); } continue; }
        throw new Error("GitHub " + r.status);
      }
      if (!done) throw new Error("conflit");
      show("ok", "Synchronisé");
    } catch(e) { show("err", "Erreur de synchro"); toast("Synchronisation impossible pour l'instant. Tes changements restent sur cet appareil."); }
    busy = false; if (again) { again = false; push(); } else renderAll();
  }
  const schedule = debounce(() => { push(); }, 1200);
  async function savePrio(list){ LS.set("ts_prio_local", list); if (!enabled()) return false;
    for (let attempt = 0; attempt < 3; attempt++) {
      const r = await putFile(PFILE, JSON.stringify({companies:list}, null, 2), psha, "Entreprises prioritaires : mise à jour");
      if (r.ok) { psha = (await r.json()).content.sha; return true; }
      if (r.status === 409 || r.status === 422) { psha = (await getFile(PFILE)).sha; continue; }
      throw new Error("GitHub " + r.status); }
    return false; }
  return {pull, schedule, savePrio, enabled, show, repo:() => REPO, reset(){ sha = null; psha = null; keyCache = {}; }};
})();

/* ---------- rendu : offres ---------- */
function filtered(){
  const ql = F.q.trim().toLowerCase();
  return (DATA.offers || []).filter(o =>
      (F.cat === "Toutes" || o.category === F.cat) && (F.showClosed || !o.closed) && (!F.fresh || isFresh(o)) &&
      (!F.prio || isPrio(o)) && (!F.hideTracked || !candFor(o.uid)) && (!F.hideSummer || !o.summer) &&
      (!ql || (o.title + " " + o.company + " " + o.location + " " + o.source).toLowerCase().includes(ql)))
    .sort((a, b) => ((a.closed ? 1 : 0) - (b.closed ? 1 : 0)) || ((isPrio(b) ? 1 : 0) - (isPrio(a) ? 1 : 0)) ||
      (pubTs(b) - pubTs(a)) || (b.first_seen - a.first_seen));
}
function statusChip(it){ const s = ST[it.status] || ST.a_postuler;
  return '<button type="button" class="status" data-act="status" style="color:var(' + s.v + ')"><i></i>' + esc(s.label) + '</button>'; }
function cardHTML(o, i, animate){
  const prio = isPrio(o), it = candFor(o.uid), link = safeUrl(o.apply_url || o.url), h = hueOf(o.company);
  const direct = o.apply_url && o.apply_url !== o.url;
  return '<article class="card' + (prio ? " prio" : "") + (o.closed ? " closed" : "") + (animate ? " enter" : "") + '" style="--i:' + i + '" data-uid="' + esc(o.uid) + '">' +
    '<div class="av" style="background:linear-gradient(135deg,hsl(' + h + ' 55% 46%),hsl(' + ((h + 40) % 360) + ' 60% 36%))">' + esc(initials(o.company)) + '</div>' +
    '<div style="min-width:0"><div class="co">' + (prio ? '<span class="star" title="Entreprise prioritaire">★</span>' : "") + esc(o.company || "—") + '</div>' +
    '<div class="ttl">' + esc(o.title) + '</div><div class="meta">' +
    '<span class="tag" style="color:var(' + (CATVAR[o.category] || "--mute") + ')">' + esc(o.category) + '</span>' +
    (o.closed ? '<span class="tag" style="color:var(--err)">Fermée</span>' : isFresh(o) ? '<span class="new">NOUVEAU</span>' : "") +
    (o.summer ? '<span class="tag" style="color:var(--mute)">Summer</span>' : "") +
    '<span>' + esc(o.location || "Paris") + '</span>' + (o.posted ? '<span><b>' + esc(pubLabel(o)) + '</b></span>' : "") +
    '<span>via ' + esc(o.source) + '</span>' +
    (direct ? '<a href="' + esc(safeUrl(o.url)) + '" target="_blank" rel="noopener">Offre ' + esc(o.source) + '</a>' : "") +
    (o.others || []).map(x => '<a href="' + esc(safeUrl(x.url)) + '" target="_blank" rel="noopener">' + esc(x.source) + '</a>').join("") +
    '</div></div><div class="right">' + (it ? statusChip(it) : '<button type="button" class="btn ghost" data-act="track">＋ Suivre</button>') +
    '<a class="btn primary" data-act="apply" href="' + esc(link) + '" target="_blank" rel="noopener">' + (direct ? "Postuler ↗" : "Voir l'offre ↗") + '</a></div></article>';
}
let firstPaint = true;
function renderOffers(){
  const rows = filtered(), open = (DATA.offers || []).filter(o => !o.closed);
  const counts = {Toutes: open.length}; for (const o of open) counts[o.category] = (counts[o.category] || 0) + 1;
  if (F.cat !== "Toutes" && !counts[F.cat]) F.cat = "Toutes";
  $("#cats").innerHTML = [["Toutes", null]].concat(CATS).filter(c => c[0] === "Toutes" || counts[c[0]])
    .map(c => '<button type="button" class="chip' + (F.cat === c[0] ? " on" : "") + '" data-cat="' + esc(c[0]) + '">' +
      (c[1] ? '<span class="cd" style="background:var(' + c[1] + ')"></span>' : "") + esc(c[0]) + ' <span class="n num">' + (counts[c[0]] || 0) + '</span></button>').join("");
  $$(".toggles .chip").forEach(b => b.classList.toggle("on", !!F[b.dataset.t]));
  const L = $("#list");
  if (!rows.length) L.innerHTML = '<div class="empty">' + ((DATA.offers || []).length ? "Aucune offre avec ces filtres." :
    "Aucune offre pour l'instant. Le tracker cherche en continu et te préviendra dès qu'une offre apparaît.") + '</div>';
  else L.innerHTML = rows.slice(0, LIMIT).map((o, i) => cardHTML(o, i, firstPaint && i < 14)).join("");
  $("#more").innerHTML = rows.length > LIMIT ? '<button type="button" class="btn" id="moreBtn">Afficher ' + Math.min(60, rows.length - LIMIT) +
    ' offres de plus · ' + (rows.length - LIMIT) + ' restantes</button>' : "";
  firstPaint = false;
  countUp($("#sAll"), open.length); countUp($("#sFresh"), open.filter(isFresh).length); countUp($("#sPrio"), open.filter(isPrio).length);
  $("#cntOffres").textContent = open.length;
}
function renderSources(){
  const S = (DATA.sources || []).slice().sort((a, b) => (b.ok - a.ok) || a.name.localeCompare(b.name));
  $("#srcSum").textContent = S.filter(s => s.ok).length + " / " + S.length + " actives";
  $("#src").innerHTML = S.map(s => '<div class="srcrow"><span class="dot" style="background:var(' + (s.ok ? "--ok" : /Non lisible/.test(s.message) ? "--mute2" : "--err") +
    ')"></span><div><b style="color:var(--ink);font-weight:600">' + esc(s.name) + '</b> · ' + esc(s.message) + ' · ' + esc(hm(s.last_run)) + '</div></div>').join("");
}
function renderHeader(){
  const g = DATA.generated, nx = DATA.next_run;
  $("#upd").innerHTML = 'Mis à jour à ' + hm(g) + (nx && nx * 1000 > Date.now() ? '<span class="lt"> · prochaine recherche vers ' + hm(nx) + '</span>' : "");
  $("#liveDot").style.background = nowS() - g < 40 * 60 ? "var(--ok)" : "var(--warn)";
}

/* ---------- rendu : candidatures ---------- */
function renderCand(){
  const ql = ($("#qc").value || "").trim().toLowerCase(), all = Object.values(CAND.items);
  const items = all.filter(it => !ql || (it.company + " " + it.title + " " + (it.notes || "")).toLowerCase().includes(ql)).sort((a, b) => (b.u || 0) - (a.u || 0));
  const by = {}; for (const s of STATUSES) by[s[0]] = [];
  for (const it of items) (by[it.status] || by.a_postuler).push(it);
  const cnt = s => all.filter(x => x.status === s).length, total = all.length || 1;
  $("#pipe").innerHTML = STATUSES.map(s => '<span style="width:' + (100 * cnt(s[0]) / total).toFixed(2) + '%;background:var(' + s[2] + ')" title="' + esc(s[1]) + '"></span>').join("");
  $("#pipeLegend").innerHTML = all.length ? STATUSES.filter(s => cnt(s[0])).map(s => '<span class="chip" style="cursor:default"><span class="cd" style="background:var(' + s[2] + ')"></span>' +
    esc(s[1]) + ' <span class="n num">' + cnt(s[0]) + '</span></span>').join("") : '<span style="color:var(--mute);font-size:13px">Aucune candidature pour l\'instant. Clique sur « ＋ Suivre » sur une offre, ou ajoute une candidature à la main.</span>';
  const offerBy = Object.fromEntries((DATA.offers || []).map(o => [o.uid, o]));
  $("#kanban").innerHTML = STATUSES.map(s => '<div class="col" data-st="' + s[0] + '"><div class="colh"><span style="width:9px;height:9px;border-radius:50%;background:var(' + s[2] + ')"></span>' +
    esc(s[1]) + '<span class="n num">' + by[s[0]].length + '</span></div>' +
    (by[s[0]].length ? by[s[0]].map(it => { const o = it.offer && offerBy[it.offer];
      return '<div class="kc" draggable="true" data-id="' + esc(it.id) + '"><div class="c">' + esc(it.company) + (o && o.closed ? ' · <span style="color:var(--err)">offre fermée</span>' : "") + '</div><div class="t">' + esc(it.title) + '</div>' +
        '<div class="m">' + (it.applied ? '<span>Envoyée le ' + esc(new Date(it.applied + "T12:00:00").toLocaleDateString("fr-FR", {day:"numeric", month:"short"})) + '</span>' : "") +
        '<span>Màj ' + esc(dshort(it.u || it.created)) + '</span>' + (it.url ? '<a href="' + esc(safeUrl(it.url)) + '" target="_blank" rel="noopener">Offre ↗</a>' : "") + '</div>' +
        (it.notes ? '<div class="note">' + esc(it.notes) + '</div>' : "") + '</div>'; }).join("") : '<div class="colempty">Glisse une carte ici</div>') + '</div>').join("");
  countUp($("#sCand"), all.filter(x => IN_PROGRESS.has(x.status)).length); $("#cntCand").textContent = all.length;
}
function renderAll(){ renderHeader(); renderOffers(); renderCand(); }

/* ---------- navigation ---------- */
function moveInk(){ const b = $('.tab[aria-selected="true"]'), ink = $("#ink"); if (!b) return;
  ink.style.width = (b.offsetWidth - 16) + "px"; ink.style.transform = "translateX(" + (b.offsetLeft + 8) + "px)"; }
function go(view){ $$(".tab").forEach(t => t.setAttribute("aria-selected", String(t.dataset.view === view)));
  $$(".view").forEach(v => v.classList.toggle("on", v.id === "view-" + view)); moveInk(); LS.set("ts_view", view); }
$$(".tab").forEach(t => t.onclick = () => go(t.dataset.view));
window.addEventListener("resize", debounce(moveInk, 100));
$$(".stat").forEach(s => s.onclick = () => { const g = s.dataset.go;
  if (g === "cand") return go("cand");
  F.cat = "Toutes"; F.fresh = g === "fresh"; F.prio = g === "prio"; saveF(); LIMIT = 60; renderOffers(); });
$("#cats").onclick = e => { const b = e.target.closest("[data-cat]"); if (!b) return; F.cat = b.dataset.cat; saveF(); LIMIT = 60; renderOffers(); };
$$(".toggles .chip").forEach(b => b.onclick = () => { F[b.dataset.t] = !F[b.dataset.t]; saveF(); LIMIT = 60; renderOffers(); });
$("#q").addEventListener("input", debounce(e => { F.q = e.target.value; LIMIT = 60; renderOffers(); }, 120));
$("#qc").addEventListener("input", debounce(renderCand, 120));
$("#more").onclick = e => { if (e.target.id === "moreBtn") { LIMIT += 60; renderOffers(); } };

/* ---------- menu de statut ---------- */
let menuEl = null, menuY = 0;
function closeMenu(){ if (menuEl) { menuEl.remove(); menuEl = null; } }
function statusMenu(anchor, it){
  closeMenu(); if (!it) return; const m = document.createElement("div"); m.className = "menu";
  m.innerHTML = STATUSES.map(s => '<button type="button" data-s="' + s[0] + '"><i style="background:var(' + s[2] + ')"></i>' + esc(s[1]) + (it.status === s[0] ? " ✓" : "") + '</button>').join("") +
    '<button type="button" data-s="__edit" style="border-top:1px solid var(--line);margin-top:4px;padding-top:9px">✎ Notes et détails…</button>';
  document.body.appendChild(m); const r = anchor.getBoundingClientRect();
  m.style.left = Math.max(8, Math.min(r.left, innerWidth - m.offsetWidth - 8)) + "px";
  m.style.top = (r.bottom + m.offsetHeight + 8 > innerHeight ? Math.max(8, r.top - m.offsetHeight - 6) : r.bottom + 6) + "px";
  m.onclick = e => { const b = e.target.closest("button"); if (!b) return; closeMenu();
    if (b.dataset.s === "__edit") openCand(CAND.items[it.id]); else { setStatus(CAND.items[it.id], b.dataset.s); toast("Statut : " + ST[b.dataset.s].label); } };
  menuEl = m; menuY = window.scrollY;
}
document.addEventListener("click", e => { if (menuEl && !menuEl.contains(e.target) && !e.target.closest('[data-act="status"]')) closeMenu(); });
document.addEventListener("keydown", e => { if (e.key === "Escape") closeMenu(); });
window.addEventListener("scroll", () => { if (menuEl && Math.abs(window.scrollY - menuY) > 40) closeMenu(); }, {passive:true});
$("#list").onclick = e => {
  const act = e.target.closest("[data-act]"), card = e.target.closest(".card"); if (!act || !card) return;
  const o = (DATA.offers || []).find(x => x.uid === card.dataset.uid); if (!o) return;
  if (act.dataset.act === "track") { trackOffer(o, "a_postuler"); toast("Ajoutée à tes candidatures", "Voir", () => go("cand")); }
  else if (act.dataset.act === "status") { e.preventDefault(); statusMenu(act, candFor(o.uid)); }
  else if (act.dataset.act === "apply") { const it = candFor(o.uid);
    if (!it || it.status === "a_postuler") setTimeout(() => toast("Tu as postulé chez " + (o.company || "cette entreprise") + " ?", "Marquer postulé",
      () => { trackOffer(o, "postule"); toast("Candidature enregistrée"); }, 9000), 500); }
};

/* ---------- glisser-déposer ---------- */
let dragId = null;
const K = $("#kanban");
K.addEventListener("dragstart", e => { const k = e.target.closest(".kc"); if (!k) return; dragId = k.dataset.id; k.classList.add("drag");
  e.dataTransfer.effectAllowed = "move"; try { e.dataTransfer.setData("text/plain", dragId); } catch(_){} });
K.addEventListener("dragend", e => { const k = e.target.closest(".kc"); if (k) k.classList.remove("drag"); $$(".col").forEach(c => c.classList.remove("drop")); });
K.addEventListener("dragover", e => { const c = e.target.closest(".col"); if (!c || !dragId) return; e.preventDefault();
  $$(".col").forEach(x => x.classList.toggle("drop", x === c)); });
K.addEventListener("drop", e => { const c = e.target.closest(".col"); if (!c || !dragId) return; e.preventDefault();
  const it = CAND.items[dragId]; dragId = null; $$(".col").forEach(x => x.classList.remove("drop"));
  if (it && it.status !== c.dataset.st) { setStatus(it, c.dataset.st); toast("Statut : " + ST[c.dataset.st].label); } });
K.addEventListener("click", e => { const k = e.target.closest(".kc"); if (k && !e.target.closest("a")) openCand(CAND.items[k.dataset.id]); });

/* ---------- fenêtre candidature ---------- */
$("#dcStatus").innerHTML = STATUSES.map(s => '<option value="' + s[0] + '">' + esc(s[1]) + '</option>').join("");
let editing = null;
function openCand(it){
  editing = it || null; const f = $("#formCand");
  $("#dcTitle").textContent = it ? (it.company || "Candidature") : "Nouvelle candidature";
  $("#dcSub").textContent = it ? "Mets à jour le statut, la date et tes notes." : "Ajoute une candidature envoyée en dehors du tracker.";
  f.company.value = it ? it.company : ""; f.title.value = it ? it.title : ""; f.status.value = it ? it.status : "postule";
  f.applied.value = it ? (it.applied || "") : today(); f.url.value = it ? (it.url || "") : ""; f.notes.value = it ? (it.notes || "") : "";
  $("#dcDelete").style.visibility = it ? "visible" : "hidden"; $("#dlgCand").showModal();
}
$("#addCand").onclick = () => openCand(null);
$("#dcCancel").onclick = () => $("#dlgCand").close();
$("#dcDelete").onclick = () => { if (editing && confirm("Supprimer cette candidature ?")) { deleteCand(editing.id); $("#dlgCand").close(); toast("Candidature supprimée"); } };
$("#formCand").addEventListener("submit", e => {
  e.preventDefault(); const f = e.target, now = Date.now();
  const it = editing ? Object.assign({}, editing) : {id:"m:" + now.toString(36) + Math.random().toString(36).slice(2, 6), offer:null, created:now, hist:[]};
  const st = f.status.value;
  if (it.status !== st) it.hist = (it.hist || []).concat([[st, now]]);
  Object.assign(it, {company:f.company.value.trim(), title:f.title.value.trim(), status:st, applied:f.applied.value, url:f.url.value.trim(), notes:f.notes.value});
  $("#dlgCand").close(); saveCand(it); toast(editing ? "Candidature mise à jour" : "Candidature ajoutée");
});

/* ---------- réglages ---------- */
function renderPrio(){ $("#ptags").innerHTML = PRIO.map((p, i) => '<span class="ptag">★ ' + esc(p) + '<button type="button" data-i="' + i + '" aria-label="Retirer">×</button></span>').join("") ||
  '<span class="hint" style="margin:0">Aucune entreprise prioritaire.</span>'; }
async function commitPrio(){ renderPrio(); renderOffers();
  try { const ok = await Sync.savePrio(PRIO.slice()); toast(ok ? "Entreprises prioritaires enregistrées" : "Enregistré sur cet appareil. Active la synchro pour les notifications prioritaires."); }
  catch(e){ toast("Impossible d'enregistrer la liste sur GitHub."); } }
$("#ptags").onclick = e => { const b = e.target.closest("button[data-i]"); if (!b) return; PRIO.splice(+b.dataset.i, 1); commitPrio(); };
function addPrio(){ const v = $("#pnew").value.trim(); if (!v) return; $("#pnew").value = "";
  if (!PRIO.some(p => compact(p) === compact(v))) { PRIO.push(v); commitPrio(); } }
$("#padd").onclick = addPrio;
$("#pnew").addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); addPrio(); } });
function openSettings(){ $("#tok").value = LS.get("ts_token", ""); $("#pass").value = LS.get("ts_pass", "");
  $("#setMsg").textContent = Sync.repo() ? "Dépôt : " + Sync.repo() : "La synchronisation n'est disponible que sur la version en ligne du site.";
  renderPrio(); $("#dlgSet").showModal(); }
$("#openSettings").onclick = openSettings; $("#syncPill").onclick = openSettings; $("#bannerSetup").onclick = openSettings;
$("#setCancel").onclick = () => $("#dlgSet").close();
$("#setOff").onclick = () => { LS.del("ts_token"); LS.del("ts_pass"); Sync.reset(); Sync.show("off", "Local"); $("#tok").value = ""; $("#pass").value = "";
  $("#setMsg").textContent = "Synchronisation désactivée sur cet appareil."; };
$("#setSave").onclick = async () => {
  const t = $("#tok").value.trim(), p = $("#pass").value;
  if (!Sync.repo()) { $("#setMsg").textContent = "La synchronisation n'est disponible que sur la version en ligne du site."; return; }
  if (!t || p.length < 6) { $("#setMsg").textContent = "Renseigne la clé GitHub et un code secret d'au moins 6 caractères."; return; }
  LS.set("ts_token", t); LS.set("ts_pass", p); Sync.reset(); $("#setMsg").textContent = "Test en cours…";
  try { await Sync.pull(); $("#setMsg").textContent = "✓ Connecté. Tes candidatures sont synchronisées et chiffrées.";
    try { await Sync.savePrio(PRIO.slice()); } catch(e){} Sync.schedule(); }
  catch(e){ $("#setMsg").textContent = e.message === "decrypt" ? "Ce code secret ne correspond pas à celui déjà utilisé sur ton autre appareil."
    : "Échec. Vérifie la clé (accès Contents en lecture et écriture sur " + Sync.repo() + ")."; }
};

/* ---------- mises à jour sans rechargement ---------- */
async function refreshData(){
  if (document.hidden || location.protocol === "file:") return;
  try {
    const r = await fetch("data.json?t=" + Date.now(), {cache:"no-store"}); if (!r.ok) return;
    const d = await r.json(); if (!d || !Array.isArray(d.offers) || d.generated === DATA.generated) return;
    const known = new Set((DATA.offers || []).map(o => o.uid));
    const fresh = d.offers.filter(o => !known.has(o.uid) && !o.closed);
    DATA = d; if (!LS.get("ts_prio_local", null) && Array.isArray(d.priority)) PRIO = d.priority.slice();
    renderAll(); renderSources();
    if (fresh.length) toast(fresh.length + (fresh.length > 1 ? " nouvelles offres" : " nouvelle offre"), "Voir", () => { go("offres"); window.scrollTo({top:0, behavior:"smooth"}); });
  } catch(e) {}
}
setInterval(refreshData, 120000);
setInterval(renderHeader, 30000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) { refreshData(); if (Sync.enabled()) Sync.pull().catch(() => {}); } });

/* ---------- démarrage ---------- */
renderAll(); renderSources();
go(LS.get("ts_view", "offres") === "cand" ? "cand" : "offres");
requestAnimationFrame(moveInk);
if (document.fonts && document.fonts.ready) document.fonts.ready.then(moveInk);
Sync.show(Sync.enabled() ? "busy" : "off", Sync.enabled() ? "Synchronisation…" : "Local");
if (Sync.enabled()) Sync.pull().catch(() => {});
</script></body></html>"""
