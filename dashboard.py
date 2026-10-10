"""Tableau de bord : une page HTML autonome (aucune dépendance externe) + data.json pour les mises à jour.

La page affiche les offres (onglets France / Suisse / Singapour), l'onglet Candidatures
(synchronisé et chiffré dans le dépôt GitHub) et les réglages (synchronisation, entreprises prioritaires).
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
<meta name="theme-color" content="#07080b" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f2f3f7" media="(prefers-color-scheme: light)">
<title>Tracker de stages</title>
<style>
:root{
  --bg:#07080b;--bg2:#0f1117;--card:#15171f;--card2:#1d2029;--line:rgba(255,255,255,.07);--line2:rgba(255,255,255,.14);
  --ink:#f5f6fa;--ink2:#d5d9e3;--mute:#9298a8;--mute2:#5f6677;
  --acc:#5b7cff;--acc2:#9d6bff;--acc3:#ff5fa2;--ok:#2fd39a;--warn:#ffb547;--err:#ff5c6c;--star:#ffc23d;
  --grad:linear-gradient(120deg,#3f6bff 0%,#8b5cf6 55%,#ec4899 100%);
  --ibd:#a78bfa;--pe:#34d399;--vc:#fb923c;--st:#60a5fa;--am:#22d3ee;--co:#fbbf24;
  --seg:#1b1e27;--segon:#f5f6fa;--segink:#0b0d12;
  --shadow:0 1px 0 rgba(255,255,255,.035) inset,0 2px 4px rgba(0,0,0,.35);
  --r:22px;--ease:cubic-bezier(.2,.8,.2,1);
}
@media (prefers-color-scheme:light){:root{
  --bg:#f2f3f7;--bg2:#e8eaf0;--card:#ffffff;--card2:#f3f4f8;--line:rgba(15,20,40,.08);--line2:rgba(15,20,40,.16);
  --ink:#0d1020;--ink2:#2a2f40;--mute:#5d6477;--mute2:#8b91a2;
  --acc:#3d5cff;--acc2:#7c4dff;--acc3:#e8338a;--ok:#08a06c;--warn:#b86e00;--err:#e3354a;--star:#d98a00;
  --ibd:#7c3aed;--pe:#059669;--vc:#ea580c;--st:#2563eb;--am:#0891b2;--co:#b45309;
  --seg:#e4e6ed;--segon:#ffffff;--segink:#0d1020;
  --shadow:0 1px 2px rgba(16,24,40,.06),0 3px 8px -4px rgba(16,24,40,.12);
}}
*{box-sizing:border-box}
[hidden]{display:none!important}
html{-webkit-text-size-adjust:100%}
html,body{margin:0;background:var(--bg);color:var(--ink)}
body{font:15px/1.45 system-ui,-apple-system,"SF Pro Text","Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  -webkit-font-smoothing:antialiased;min-height:100vh;position:relative;overflow-x:hidden}
.glow{position:absolute;top:0;left:0;right:0;height:460px;pointer-events:none;z-index:0;
  background:radial-gradient(520px 260px at 12% -4%,color-mix(in srgb,var(--acc) 26%,transparent),transparent 72%),
  radial-gradient(460px 240px at 88% -8%,color-mix(in srgb,var(--acc3) 16%,transparent),transparent 72%)}
a{color:inherit}
button,input,select,textarea{font:inherit;color:inherit}
.num{font-variant-numeric:tabular-nums}
.ico{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;flex:none}
.sq{display:grid;place-items:center;flex:none;border-radius:12px;width:36px;height:36px;color:var(--c,var(--acc));
  background:color-mix(in srgb,var(--c,var(--acc)) 16%,transparent)}
/* ---------- en-tête ---------- */
.top{position:sticky;top:0;z-index:20;backdrop-filter:saturate(160%) blur(14px);-webkit-backdrop-filter:saturate(160%) blur(14px);
  background:color-mix(in srgb,var(--bg) 80%,transparent);border-bottom:1px solid var(--line)}
.top-in{max-width:1140px;margin:0 auto;padding:12px 20px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:12px 18px}
.brand{display:flex;align-items:center;gap:12px;min-width:0}
.logo{width:38px;height:38px;border-radius:13px;display:grid;place-items:center;color:#fff;background:var(--grad);flex:none;
  box-shadow:0 8px 20px -8px #8b5cf6}
.logo .ico{width:20px;height:20px;stroke-width:2.4}
.brand h1{font-size:16.5px;margin:0;letter-spacing:-.02em;font-weight:800;white-space:nowrap}
.live{display:flex;align-items:center;gap:7px;color:var(--mute);font-size:12.5px;white-space:nowrap}
.dot{width:7px;height:7px;border-radius:50%;background:var(--ok);position:relative;flex:none;display:inline-block}
.dot.pulse::after{content:"";position:absolute;inset:0;border-radius:50%;background:inherit;animation:ping 2.4s var(--ease) infinite}
@keyframes ping{0%{transform:scale(1);opacity:.7}80%,100%{transform:scale(3);opacity:0}}
.actions-top{display:flex;align-items:center;gap:8px;justify-self:end}
.pill{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);background:var(--card);border-radius:999px;
  padding:8px 13px;font-size:13px;font-weight:600;color:var(--mute);cursor:pointer;transition:color .2s,border-color .2s;white-space:nowrap}
.pill:hover{color:var(--ink);border-color:var(--line2)}
.iconbtn{width:38px;height:38px;border-radius:999px;border:1px solid var(--line);background:var(--card);display:grid;place-items:center;
  cursor:pointer;color:var(--ink2);transition:transform .35s var(--ease)}
.iconbtn:hover{transform:rotate(60deg)}
.tabs{position:relative;display:flex;padding:4px;border-radius:999px;background:var(--seg)}
.tab{position:relative;z-index:1;appearance:none;border:0;background:none;padding:8px 18px;cursor:pointer;color:var(--mute);font-weight:700;font-size:14px;
  display:flex;align-items:center;justify-content:center;gap:8px;border-radius:999px;transition:color .25s;flex:1;white-space:nowrap}
.tab[aria-selected=true]{color:var(--segink)}
.tab .cnt{font-size:11.5px;min-width:22px;padding:1px 7px;border-radius:999px;background:color-mix(in srgb,var(--mute) 18%,transparent);font-weight:700}
.tab[aria-selected=true] .cnt{background:color-mix(in srgb,var(--segink) 10%,transparent)}
.ink{position:absolute;left:0;top:4px;bottom:4px;width:0;border-radius:999px;background:var(--segon);z-index:0;
  box-shadow:0 2px 8px -2px rgba(0,0,0,.35);transition:transform .35s var(--ease),width .35s var(--ease);will-change:transform}
main{position:relative;z-index:1;max-width:1140px;margin:0 auto;padding:22px 20px 90px}
.view{display:none}.view.on{display:block;animation:fadeIn .35s var(--ease)}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
/* ---------- régions ---------- */
.seg{display:flex;gap:4px;padding:5px;border-radius:999px;background:var(--seg);width:max-content;max-width:100%;margin:0 0 16px}
.reg{appearance:none;border:0;background:none;border-radius:999px;padding:9px 16px;font-weight:700;font-size:14.5px;color:var(--mute);cursor:pointer;
  display:inline-flex;align-items:center;gap:8px;transition:color .2s,background-color .2s;white-space:nowrap}
.reg:hover{color:var(--ink)}
.reg .n{font-size:12px;font-weight:700;padding:1px 8px;border-radius:999px;background:color-mix(in srgb,var(--mute) 18%,transparent);min-width:24px;text-align:center}
.reg[aria-pressed=true]{background:var(--grad);color:#fff;box-shadow:0 8px 20px -10px #8b5cf6}
.reg[aria-pressed=true] .n{background:rgba(255,255,255,.22)}
/* ---------- tuiles ---------- */
.stats{display:grid;grid-template-columns:1.7fr 1fr 1fr 1fr;gap:14px;margin-bottom:22px}
.stat{position:relative;background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:16px 18px;box-shadow:var(--shadow);
  cursor:pointer;transition:transform .25s var(--ease);display:flex;flex-direction:column;justify-content:space-between;gap:14px;min-height:132px;overflow:hidden}
.stat:hover{transform:translateY(-2px)}
.stat .k{color:var(--mute);font-size:13px;font-weight:600;line-height:1.25}
.stat .v{font-size:34px;font-weight:800;letter-spacing:-.04em;line-height:1}
.hero{color:#fff;border:0;background:linear-gradient(130deg,#2f5bff 0%,#7b3cf5 58%,#e2489a 120%);min-height:170px;padding:20px 22px}
.hero.r-Suisse{background:linear-gradient(130deg,#1e66ff 0%,#5b4bf0 50%,#ff4d6d 125%)}
.hero.r-Singapour{background:linear-gradient(130deg,#5b3cf5 0%,#c13ad1 60%,#ff8a3d 125%)}
.hero .k{color:rgba(255,255,255,.82);font-size:13.5px}
.hero .rg{font-size:21px;font-weight:800;letter-spacing:-.02em;color:#fff;margin-top:2px}
.hero .v{font-size:52px}
.hero .v{white-space:nowrap}
.hero .v small{font-size:15px;font-weight:650;letter-spacing:0;opacity:.85;margin-left:8px;white-space:nowrap}
.hero .cities{display:flex;align-items:center;gap:6px;font-size:13px;font-weight:600;color:rgba(255,255,255,.85);margin-top:6px;min-width:0}
.hero .cities span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.hero .cities .ico{width:14px;height:14px}
.hero .txt{position:relative;z-index:1;max-width:70%}
.art{position:absolute;right:-4px;bottom:0;width:min(46%,250px);height:100%;pointer-events:none}
.art svg{position:absolute;right:0;bottom:0;width:100%;height:auto;max-height:100%}
/* ---------- filtres ---------- */
.bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:0 0 12px}
.chips{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding:2px 0 4px;flex:1 1 100%;min-width:0}
.chips::-webkit-scrollbar{display:none}
.chip{flex:none;border:1px solid var(--line);background:var(--card);color:var(--ink2);border-radius:999px;padding:7px 13px 7px 8px;font-size:13.5px;font-weight:650;
  cursor:pointer;display:inline-flex;align-items:center;gap:8px;transition:background-color .2s,color .2s,border-color .2s;user-select:none;white-space:nowrap}
.chip:hover{border-color:var(--line2)}
.chip .ci{width:24px;height:24px;border-radius:8px;display:grid;place-items:center;color:var(--c,var(--mute));background:color-mix(in srgb,var(--c,var(--mute)) 18%,transparent)}
.chip .ci .ico{width:14px;height:14px;stroke-width:2.2}
.chip.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.chip.on .ci{background:color-mix(in srgb,var(--c,var(--mute)) 30%,var(--ink))}
.chip .n{opacity:.6;font-size:12.5px}
.toggles .chip{padding:7px 13px;color:var(--mute)}
.toggles .chip.on{color:var(--bg)}
.search{flex:1 1 280px;position:relative;min-width:0}
.search input{width:100%;border:1px solid var(--line);background:var(--card);border-radius:999px;padding:11px 14px 11px 40px;outline:none;
  transition:border-color .2s;font-size:14.5px}
.search input:focus{border-color:var(--acc)}
.search .ico{position:absolute;left:14px;top:50%;transform:translateY(-50%);width:16px;height:16px;color:var(--mute)}
.toggles{display:flex;gap:8px;flex-wrap:wrap;min-width:0}
/* ---------- liste ---------- */
.list{margin-top:8px}
.grp{margin-top:26px}
.gh{display:flex;align-items:center;gap:10px;margin:0 2px 12px;font-size:13px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--mute)}
.gh .gc{font-size:12px;letter-spacing:0;padding:1px 8px;border-radius:999px;background:color-mix(in srgb,var(--mute) 16%,transparent);color:var(--mute)}
.gh::after{content:"";flex:1;height:1px;background:var(--line)}
.gh .ico{width:15px;height:15px}
.g-prio .gh{color:var(--star)}
.g-today .gh{color:var(--ink)}
.g-today .gh .gd{width:8px;height:8px;border-radius:50%;background:var(--grad)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:16px}
.card{position:relative;display:flex;flex-direction:column;background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:18px 18px 16px;
  box-shadow:var(--shadow);transition:transform .25s var(--ease);content-visibility:auto;contain-intrinsic-size:auto 214px;min-width:0}
.card:hover{transform:translateY(-3px)}
.card.enter{animation:rise .5s var(--ease) both;animation-delay:calc(var(--i,0) * 30ms)}
@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.card.prio{border-color:color-mix(in srgb,var(--star) 45%,transparent)}
.card.prio::before{content:"";position:absolute;left:22px;right:22px;top:0;height:3px;border-radius:0 0 3px 3px;background:linear-gradient(90deg,var(--star),var(--acc3))}
.card.closed{opacity:.55}
.ch{display:flex;align-items:center;gap:12px;min-width:0}
.av{width:46px;height:46px;border-radius:15px;display:grid;place-items:center;font-weight:800;font-size:15px;color:#fff;flex:none;letter-spacing:.01em;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.12)}
.who{min-width:0;flex:1}
.co{font-weight:750;font-size:15px;display:flex;gap:6px;align-items:center;min-width:0;letter-spacing:-.01em}
.co span.nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.co .star{flex:none}
.where{display:flex;flex-wrap:wrap;align-items:center;gap:2px 6px;color:var(--mute);font-size:13px;margin-top:2px;min-width:0}
.where span{white-space:nowrap}
.where .ico{width:14px;height:14px;color:var(--acc)}
.where .sep{opacity:.5}
.badge{flex:none;align-self:flex-start;font-size:11px;font-weight:800;letter-spacing:.06em;padding:5px 10px;border-radius:999px;white-space:nowrap}
.new{color:#fff;background:var(--grad)}
.badge.cl{color:var(--err);background:color-mix(in srgb,var(--err) 15%,transparent)}
.ttl{font-weight:750;font-size:17px;line-height:1.32;letter-spacing:-.015em;margin:14px 0 0;overflow-wrap:anywhere}
.meta{display:flex;flex-wrap:wrap;gap:6px 6px;color:var(--mute);font-size:12.5px;margin:12px 0 16px;align-items:center}
.meta a{color:var(--mute);text-decoration:none;padding:3px 9px;border-radius:999px;border:1px solid var(--line)}
.meta a:hover{color:var(--ink);border-color:var(--line2)}
.tag{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:700;padding:3px 10px 3px 4px;border-radius:999px;
  color:var(--c,var(--mute));background:color-mix(in srgb,var(--c,var(--mute)) 14%,transparent)}
.tag .ti{width:20px;height:20px;border-radius:999px;display:grid;place-items:center;background:color-mix(in srgb,var(--c,var(--mute)) 22%,transparent)}
.tag .ti .ico{width:12px;height:12px;stroke-width:2.4}
.tag.plain{padding:3px 10px}
.via{padding:3px 2px}
.cf{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:auto;padding-top:14px;border-top:1px solid var(--line)}
.star{color:var(--star)}
.btn{appearance:none;border:1px solid var(--line);background:var(--card2);border-radius:999px;padding:9px 15px;font-weight:700;font-size:13.5px;
  cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:7px;white-space:nowrap;
  transition:transform .15s var(--ease),border-color .2s,filter .2s;color:var(--ink)}
.btn:hover{border-color:var(--line2)}
.btn:active{transform:scale(.97)}
.btn .ico{width:15px;height:15px;stroke-width:2.4}
.btn .gl{font-weight:800;font-size:14px;line-height:1}
.btn.primary{background:var(--grad);color:#fff;border-color:transparent}
.btn.primary:hover{filter:brightness(1.1)}
.btn.ghost{background:none}
.btn.danger{color:var(--err)}
.status{display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:8px 13px;font-size:13px;font-weight:700;cursor:pointer;
  border:1px solid transparent;background:color-mix(in srgb,currentColor 14%,transparent);transition:transform .15s var(--ease)}
.status:active{transform:scale(.96)}
.status i{width:7px;height:7px;border-radius:50%;background:currentColor}
.empty{padding:40px 20px 44px;text-align:center;color:var(--mute);background:var(--card);border:1px solid var(--line);border-radius:var(--r);margin-top:18px}
.empty svg{width:150px;height:auto;display:block;margin:0 auto 14px}
.empty b{display:block;color:var(--ink);font-size:17px;margin-bottom:4px}
.more{display:flex;justify-content:center;margin-top:22px}
/* ---------- panneaux ---------- */
details.src{margin-top:18px;background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:4px 18px;color:var(--mute);font-size:13.5px}
details.src:first-of-type{margin-top:36px}
details.src summary{cursor:pointer;font-weight:750;color:var(--ink);list-style:none;display:flex;gap:10px;align-items:center;padding:12px 0}
details.src summary::-webkit-details-marker{display:none}
details.src summary::after{content:"";margin-left:auto;width:8px;height:8px;border-right:2px solid var(--mute);border-bottom:2px solid var(--mute);
  transform:rotate(45deg);transition:transform .2s var(--ease)}
details.src[open] summary::after{transform:rotate(225deg)}
details.src[open]{padding-bottom:16px}
.srcgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px 18px;margin-top:4px}
.srcrow{display:flex;gap:9px;align-items:baseline}
.rejlist{display:flex;flex-direction:column;gap:6px;max-height:440px;overflow:auto}
.rejrow{display:flex;gap:10px;align-items:baseline;padding:9px 12px;border-radius:12px;background:var(--bg2);flex-wrap:wrap}
.rejrow .why{margin-left:auto;flex:none;font-size:12px;color:var(--warn)}
.rejrow a{color:var(--ink);text-decoration:none;min-width:0;overflow-wrap:anywhere}.rejrow a:hover{text-decoration:underline}
/* ---------- candidatures ---------- */
.pipe{display:flex;height:10px;border-radius:999px;overflow:hidden;background:var(--bg2);margin:8px 0 18px;gap:2px}
.pipe span{height:100%;transition:width .6s var(--ease)}
.pipe span:empty{min-width:0}
.kanban{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(258px,1fr);gap:14px;overflow-x:auto;padding-bottom:12px;scroll-snap-type:x proximity}
.col{background:var(--bg2);border:1px solid var(--line);border-radius:var(--r);padding:12px;min-height:150px;scroll-snap-align:start;transition:background-color .2s,border-color .2s}
.col.drop{border-color:var(--acc);background:color-mix(in srgb,var(--acc) 10%,var(--bg2))}
.colh{display:flex;align-items:center;gap:9px;font-weight:800;font-size:14px;padding:4px 4px 12px;letter-spacing:-.01em}
.colh .n{margin-left:auto;color:var(--mute);font-weight:700;font-size:12px;padding:1px 8px;border-radius:999px;background:color-mix(in srgb,var(--mute) 15%,transparent)}
.kc{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:13px 14px;margin-bottom:10px;cursor:grab;
  box-shadow:var(--shadow);transition:transform .2s var(--ease),opacity .2s}
.kc:hover{transform:translateY(-2px)}
.kc.drag{opacity:.4}
.kc .t{font-weight:700;font-size:14px;margin-top:3px;line-height:1.3;overflow-wrap:anywhere}
.kc .c{font-size:12.5px;color:var(--mute);font-weight:700;display:flex;align-items:center;gap:8px}
.kc .c .av{width:24px;height:24px;border-radius:8px;font-size:10px}
.kc .m{font-size:12px;color:var(--mute2);margin-top:8px;display:flex;gap:8px;flex-wrap:wrap}
.kc .m a{color:var(--acc);text-decoration:none;font-weight:650}
.kc .note{font-size:12.5px;color:var(--mute);margin-top:8px;white-space:pre-wrap;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
  padding:7px 9px;border-radius:10px;background:var(--bg2)}
.colempty{font-size:12.5px;color:var(--mute2);text-align:center;padding:18px 6px;border:1.5px dashed var(--line2);border-radius:14px}
.banner{display:flex;gap:14px;align-items:center;justify-content:space-between;flex-wrap:wrap;border:1px solid var(--line);
  background:linear-gradient(120deg,color-mix(in srgb,var(--acc) 16%,var(--card)),var(--card) 70%);border-radius:var(--r);padding:14px 16px;margin-bottom:16px}
/* ---------- fenêtres ---------- */
dialog{border:1px solid var(--line2);background:var(--card);color:var(--ink);border-radius:26px;padding:0;width:min(560px,94vw);max-height:92vh;
  box-shadow:0 30px 80px -20px rgba(0,0,0,.6)}
dialog[open]{animation:pop .28s var(--ease)}
@keyframes pop{from{opacity:0;transform:translateY(8px) scale(.97)}to{opacity:1;transform:none}}
dialog::backdrop{background:rgba(4,5,10,.6)}
.dlg{padding:24px 24px 20px}
.dlg h2{margin:0 0 4px;font-size:21px;font-weight:800;letter-spacing:-.02em}
.dlg p.sub{margin:0 0 18px;color:var(--mute);font-size:13.5px}
.field{display:flex;flex-direction:column;gap:6px;margin-bottom:13px}
.field label{font-size:12.5px;color:var(--mute);font-weight:700}
.field input,.field select,.field textarea{border:1px solid var(--line);background:var(--bg2);border-radius:14px;padding:11px 13px;outline:none;
  transition:border-color .2s;width:100%}
.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--acc)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.dlgfoot{display:flex;gap:8px;justify-content:flex-end;padding-top:8px;flex-wrap:wrap}
.dlgfoot .l{margin-right:auto}
.ptags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.ptag{display:inline-flex;align-items:center;gap:6px;background:color-mix(in srgb,var(--star) 15%,transparent);color:var(--star);
  border-radius:999px;padding:6px 7px 6px 12px;font-size:13px;font-weight:700;animation:pop .25s var(--ease)}
.ptag button{border:0;background:none;color:inherit;cursor:pointer;padding:0 4px;font-size:16px;line-height:1}
.hint{font-size:12.5px;color:var(--mute);margin-bottom:12px}
hr.sep{border:0;border-top:1px solid var(--line);margin:18px 0}
.menu{position:fixed;z-index:50;background:var(--card);border:1px solid var(--line2);border-radius:18px;padding:6px;min-width:210px;
  box-shadow:0 24px 60px -18px rgba(0,0,0,.6);animation:pop .18s var(--ease)}
.menu button{display:flex;width:100%;align-items:center;gap:10px;border:0;background:none;padding:9px 11px;border-radius:12px;cursor:pointer;font-size:13.5px;font-weight:600;text-align:left}
.menu button:hover{background:var(--bg2)}
.menu i{width:8px;height:8px;border-radius:50%}
.toasts{position:fixed;left:50%;bottom:calc(22px + env(safe-area-inset-bottom));transform:translateX(-50%);z-index:60;display:flex;flex-direction:column;gap:8px;align-items:center;pointer-events:none;width:max-content;max-width:92vw}
.toast{pointer-events:auto;display:flex;align-items:center;gap:12px;background:var(--ink);color:var(--bg);border-radius:999px;padding:9px 9px 9px 18px;
  font-size:14px;font-weight:600;box-shadow:0 14px 40px -12px rgba(0,0,0,.5);animation:toastIn .35s var(--ease)}
.toast span{padding:2px 0}
.toast.out{animation:toastOut .3s var(--ease) forwards}
.toast button{border:0;background:var(--grad);color:#fff;border-radius:999px;padding:6px 13px;font-weight:750;cursor:pointer}
@keyframes toastIn{from{opacity:0;transform:translateY(12px) scale(.98)}}
@keyframes toastOut{to{opacity:0;transform:translateY(8px)}}
@media (max-width:1000px){
  .stats{grid-template-columns:repeat(3,1fr)}
  .hero{grid-column:1/-1}
}
@media (max-width:900px){ .grid{grid-template-columns:1fr} }
@media (min-width:761px){ #cats{flex-wrap:wrap;overflow:visible} }
@media (max-width:760px){
  .top-in{grid-template-columns:1fr auto;padding:10px 16px;gap:10px}
  .tabs{grid-column:1/-1;grid-row:2}
  .lt{display:none}
  .pill .st{display:none}
  .pill{padding:8px 11px}
  main{padding:18px 16px 90px}
  .seg{width:100%}
  .reg{flex:1;justify-content:center;padding:9px 8px;font-size:14px;gap:6px}
  .reg .n{padding:1px 6px;min-width:20px}
  .stats{gap:10px;margin-bottom:18px}
  .stat{min-height:112px;padding:13px 13px;border-radius:20px;gap:10px}
  .stat .sq{width:32px;height:32px;border-radius:11px}
  .stat .k{font-size:12px}
  .stat .v{font-size:27px}
  .hero{min-height:156px;padding:18px}
  .hero .v{font-size:44px}
  .hero .txt{max-width:64%}
  .art{width:min(46%,190px)}
  .toggles{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;flex:1 1 100%}
  .toggles::-webkit-scrollbar{display:none}
  .card{padding:16px 16px 14px;border-radius:20px}
  .cf .btn.primary{flex:1}
  .ttl{font-size:16.5px}
  .row2{grid-template-columns:1fr}
  .kanban{grid-auto-columns:minmax(80%,1fr)}
  .grid{gap:14px}
}
@media (max-width:380px){ .hero .v small{display:none} }
@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
</style></head>
<body>
<div class="glow"></div>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="i-ibd" viewBox="0 0 24 24"><path d="M3 9.5 12 4l9 5.5"/><path d="M5.5 10.5v7M10 10.5v7M14 10.5v7M18.5 10.5v7"/><path d="M3.5 20h17"/></symbol>
<symbol id="i-pe" viewBox="0 0 24 24"><path d="M11 3.1A9 9 0 1 0 20.9 13H11z"/><path d="M14.5 3.2a9 9 0 0 1 6.3 6.3h-6.3z"/></symbol>
<symbol id="i-vc" viewBox="0 0 24 24"><path d="M9.5 14.5 6 11c1.6-4.3 5-7.7 13-8.5-.8 8-4.2 11.4-8.5 13z"/><path d="M6.5 14.5C5 15.5 4 18 4 20c2 0 4.5-1 5.5-2.5"/><circle cx="14.5" cy="9.5" r="1.7"/></symbol>
<symbol id="i-st" viewBox="0 0 24 24"><path d="M3 17l5.5-5.5 4 4L20 8"/><path d="M14.5 8H20v5.5"/></symbol>
<symbol id="i-am" viewBox="0 0 24 24"><path d="M12 3.5 3 8.5l9 5 9-5z"/><path d="M3 12.5l9 5 9-5"/><path d="M3 16.5l9 5 9-5"/></symbol>
<symbol id="i-co" viewBox="0 0 24 24"><path d="M12 3s6.5 6.6 6.5 11.3a6.5 6.5 0 0 1-13 0C5.5 9.6 12 3 12 3z"/><path d="M9 14.5a3 3 0 0 0 3 3"/></symbol>
<symbol id="i-all" viewBox="0 0 24 24"><rect x="4" y="4" width="6.5" height="6.5" rx="2"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="2"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="2"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="2"/></symbol>
<symbol id="i-pin" viewBox="0 0 24 24"><path d="M12 21s-7-6.1-7-11.4a7 7 0 0 1 14 0C19 14.9 12 21 12 21z"/><circle cx="12" cy="9.6" r="2.4"/></symbol>
<symbol id="i-bolt" viewBox="0 0 24 24"><path d="M13 2.5 4.5 13.5h6.5l-1 8 8.5-11h-6.5z"/></symbol>
<symbol id="i-star" viewBox="0 0 24 24"><path d="m12 3.2 2.7 5.5 6 .9-4.3 4.2 1 6L12 17l-5.4 2.8 1-6-4.3-4.2 6-.9z"/></symbol>
<symbol id="i-bag" viewBox="0 0 24 24"><rect x="3" y="7" width="18" height="13" rx="3"/><path d="M8.5 7V5.6A1.6 1.6 0 0 1 10.1 4h3.8a1.6 1.6 0 0 1 1.6 1.6V7M3 12.5h18"/></symbol>
<symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/></symbol>
<symbol id="i-out" viewBox="0 0 24 24"><path d="M7 17 17 7M8.5 7H17v8.5"/></symbol>
<symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></symbol>
<symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></symbol>
<symbol id="i-lock" viewBox="0 0 24 24"><rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/></symbol>
</defs></svg>
<header class="top"><div class="top-in">
  <div class="brand"><div class="logo"><svg class="ico"><use href="#i-st"/></svg></div><div><h1>Tracker de stages</h1>
    <div class="live"><span class="dot pulse" id="liveDot"></span><span id="upd" class="num"></span></div></div></div>
  <nav class="tabs" role="tablist">
    <button class="tab" role="tab" data-view="offres" aria-selected="true">Offres <span class="cnt num" id="cntOffres">0</span></button>
    <button class="tab" role="tab" data-view="cand" aria-selected="false">Candidatures <span class="cnt num" id="cntCand">0</span></button>
    <span class="ink" id="ink"></span>
  </nav>
  <div class="actions-top">
    <button class="pill" id="syncPill" title="Synchronisation des candidatures"><span class="dot" id="syncDot"></span><span id="syncTxt">Local</span></button>
    <button class="iconbtn" id="openSettings" title="Réglages" aria-label="Réglages">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
    </button>
  </div>
</div></header>

<main>
<section class="view on" id="view-offres">
  <div class="seg" id="regions" role="group" aria-label="Région">
    <button type="button" class="reg" data-region="France" aria-pressed="true">France <span class="n num">0</span></button>
    <button type="button" class="reg" data-region="Suisse" aria-pressed="false">Suisse <span class="n num">0</span></button>
    <button type="button" class="reg" data-region="Singapour" aria-pressed="false">Singapour <span class="n num">0</span></button>
  </div>
  <div class="stats">
    <div class="stat hero" data-go="all" id="hero">
      <div class="txt"><div class="k">Offres actives</div><div class="rg" id="heroReg">France</div></div>
      <div class="txt"><div class="v num"><span id="sAll">0</span><small id="heroNew"></small></div>
        <div class="cities"><svg class="ico"><use href="#i-pin"/></svg><span id="heroCities"></span></div></div>
      <div class="art" id="heroArt"></div>
    </div>
    <div class="stat" data-go="fresh"><span class="sq" style="--c:var(--acc3)"><svg class="ico"><use href="#i-bolt"/></svg></span><div><div class="v num" id="sFresh">0</div><div class="k">Publiées&nbsp;&lt;&nbsp;48&nbsp;h</div></div></div>
    <div class="stat" data-go="prio"><span class="sq" style="--c:var(--star)"><svg class="ico"><use href="#i-star"/></svg></span><div><div class="v num" id="sPrio">0</div><div class="k">Prioritaires</div></div></div>
    <div class="stat" data-go="cand"><span class="sq" style="--c:var(--acc)"><svg class="ico"><use href="#i-bag"/></svg></span><div><div class="v num" id="sCand">0</div><div class="k">Candidatures en cours</div></div></div>
  </div>
  <div class="bar"><div class="chips" id="cats"></div></div>
  <div class="bar">
    <div class="search"><svg class="ico"><use href="#i-search"/></svg>
      <input id="q" type="search" placeholder="Entreprise, poste, ville…" autocomplete="off"></div>
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
  <details class="src" id="rejBox"><summary><span>Offres écartées par le filtre</span><span id="rejSum" style="color:var(--mute);font-weight:500"></span></summary>
    <p class="hint" style="margin:4px 0 12px">Les 72 dernières heures dans la région sélectionnée, hors offres situées en dehors des villes suivies. Si une offre qui t'intéresse apparaît ici, signale-la pour que la règle soit ajustée.</p>
    <div class="search" style="max-width:420px;margin-bottom:12px"><svg class="ico"><use href="#i-search"/></svg>
      <input id="qr" type="search" placeholder="Rechercher dans les offres écartées…" autocomplete="off"></div>
    <div id="rej" class="rejlist"></div></details>
</section>

<section class="view" id="view-cand">
  <div class="banner" id="syncBanner" hidden>
    <div style="display:flex;gap:12px;align-items:center"><span class="sq"><svg class="ico"><use href="#i-lock"/></svg></span>
      <div><b>Synchronisation désactivée.</b> <span style="color:var(--mute)">Tes candidatures ne sont enregistrées que sur cet appareil.</span></div></div>
    <button class="btn primary" id="bannerSetup">Activer</button>
  </div>
  <div class="bar" style="justify-content:space-between">
    <div class="search" style="max-width:420px"><svg class="ico"><use href="#i-search"/></svg>
      <input id="qc" type="search" placeholder="Rechercher une candidature…" autocomplete="off"></div>
    <button class="btn primary" id="addCand"><svg class="ico"><use href="#i-plus"/></svg>Ajouter une candidature</button>
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
const CATS = [["M&A / IBD","--ibd","ibd"],["Private Equity","--pe","pe"],["Venture Capital","--vc","vc"],["Sales & Trading","--st","st"],
              ["Asset Management","--am","am"],["Commodities","--co","co"]];
const CATVAR = Object.fromEntries(CATS.map(c => [c[0], c[1]])), CATICO = Object.fromEntries(CATS.map(c => [c[0], c[2]]));
const STATUSES = [["a_postuler","À postuler","--mute"],["postule","Postulé","--acc"],["test","Test en ligne","--am"],
                  ["entretien","Entretiens","--acc2"],["offre","Offre reçue","--ok"],["refuse","Refusé","--err"],["abandon","Abandonné","--mute2"]];
const ST = Object.fromEntries(STATUSES.map(s => [s[0], {label:s[1], v:s[2]}]));
const IN_PROGRESS = new Set(["postule","test","entretien","offre"]);
const REGIONS = ["France", "Suisse", "Singapour"];
const REGDEF = {France:"Paris · Île-de-France", Suisse:"Genève · Zurich", Singapour:"Singapour"};
const icon = (id, cls) => '<svg class="ico' + (cls ? " " + cls : "") + '"><use href="#i-' + id + '"/></svg>';
const regOf = o => REGIONS.includes(o && o.region) ? o.region : "France";
const cityOf = o => o.city || o.location || "";

const compact = s => String(s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
function pubTs(o){ if (o.posted && /^\d{4}-\d{2}-\d{2}/.test(o.posted)) return Date.parse(o.posted.slice(0,10) + "T12:00:00") / 1000; return o.first_seen; }
const nowS = () => Date.now() / 1000;
const isFresh = o => nowS() - pubTs(o) < 2 * DAY;
const ageDays = o => Math.floor((nowS() - pubTs(o) + DAY / 2) / DAY);
function pubLabel(o){ if (!o.posted) return "";
  const d = ageDays(o);
  if (o.posted_plus) return "Il y a plus de " + Math.max(1, d - 1) + " j";
  return d <= 0 ? "Aujourd'hui" : d === 1 ? "Hier" : "Il y a " + d + " j"; }
const hm = ts => new Date(ts * 1000).toLocaleTimeString("fr-FR", {hour:"2-digit", minute:"2-digit"});
const dshort = ms => new Date(ms).toLocaleDateString("fr-FR", {day:"numeric", month:"short"});
const today = () => { const d = new Date(); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); };
function hueOf(s){ let h = 0; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return h % 360; }
function initials(s){ const w = String(s || "?").replace(/[^A-Za-zÀ-ÿ0-9 ]/g, " ").split(/\s+/).filter(Boolean);
  if (!w.length) return "?"; return (w[0][0] + (w.length > 1 ? w[1][0] : (w[0][1] || ""))).toUpperCase(); }
const avStyle = s => { const h = hueOf(s); return "background:linear-gradient(135deg,hsl(" + h + " 62% 52%),hsl(" + ((h + 45) % 360) + " 66% 38%))"; };
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

/* ---------- illustrations (SVG statiques, faites main) ---------- */
const ART = {
France: '<svg viewBox="0 0 240 150" aria-hidden="true"><circle cx="188" cy="40" r="22" fill="#fff" opacity=".16"/><circle cx="188" cy="40" r="13" fill="#fff" opacity=".18"/>' +
  '<g fill="#fff" opacity=".13"><rect x="72" y="112" width="20" height="38" rx="4"/>' +
  '<rect x="170" y="100" width="26" height="50" rx="4"/><rect x="200" y="86" width="22" height="64" rx="4"/><rect x="225" y="108" width="20" height="42" rx="4"/></g>' +
  '<g fill="#fff"><rect x="129" y="4" width="2" height="12" rx="1"/><path d="M126.5 15h7l3 34h-13z"/><rect x="119" y="48" width="22" height="4.5" rx="1.5"/>' +
  '<path d="M121.5 52.5h17l6.5 31h-30z"/><rect x="108" y="83" width="44" height="5" rx="1.5"/><path d="M111 88h38l18 52h-15q-8-26-22-26t-22 26H93z"/></g>' +
  '<g stroke="#4a3ad8" stroke-opacity=".35" stroke-width="1.2"><path d="M124 56l12 24M136 56l-12 24M115 92l10 18M145 92l-10 18"/></g>' +
  '<path d="M0 142q60-9 120 0t120 0v8H0z" fill="#fff" opacity=".2"/></svg>',
Suisse: '<svg viewBox="0 0 240 150" aria-hidden="true"><circle cx="58" cy="34" r="16" fill="#fff" opacity=".18"/>' +
  '<path d="M0 108 34 72l22 18 34-44 30 36 24-20 36 38 28-30 32 26v24H0z" fill="#fff" opacity=".16"/>' +
  '<path d="M90 46l-10 13 8-2 4 6 6-6 4 3zM144 62l-8 9 6-1 3 4 5-4zM196 66l-8 9 6-1 3 4 5-5z" fill="#fff" opacity=".55"/>' +
  '<rect x="0" y="114" width="240" height="36" fill="#fff" opacity=".14"/>' +
  '<path d="M10 126h40M70 134h50M150 128h44M200 138h30" stroke="#fff" stroke-opacity=".35" stroke-width="2" stroke-linecap="round"/>' +
  '<path d="M150 114c-1.6-30-1.6-64 2.6-98 3 34 3.4 68 2.4 98z" fill="#fff" opacity=".95"/>' +
  '<path d="M152.6 16c9 1 16 10 19 24-5-8-11-13-18-14z" fill="#fff" opacity=".55"/>' +
  '<g fill="#fff" opacity=".5"><circle cx="160" cy="22" r="2.2"/><circle cx="166" cy="30" r="1.8"/><circle cx="171" cy="40" r="1.6"/><circle cx="146" cy="24" r="1.5"/></g>' +
  '<ellipse cx="152" cy="114" rx="14" ry="3.2" fill="#fff" opacity=".6"/>' +
  '<g fill="#fff" opacity=".22"><rect x="196" y="98" width="12" height="16" rx="2"/><rect x="210" y="92" width="14" height="22" rx="2"/><rect x="226" y="100" width="14" height="14" rx="2"/></g></svg>',
Singapour: '<svg viewBox="0 0 240 150" aria-hidden="true"><circle cx="40" cy="36" r="18" fill="#fff" opacity=".18"/>' +
  '<g fill="#fff" opacity=".14"><rect x="4" y="78" width="18" height="50" rx="3"/><rect x="26" y="62" width="16" height="66" rx="3"/><rect x="176" y="70" width="16" height="58" rx="3"/></g>' +
  '<circle cx="215" cy="92" r="22" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="2.2"/>' +
  '<path d="M215 70v44M193 92h44M199.4 76.4l31.2 31.2M230.6 76.4l-31.2 31.2" stroke="#fff" stroke-opacity=".25" stroke-width="1.2"/>' +
  '<path d="M209 128l6-14 6 14" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="2"/>' +
  '<g fill="#fff"><path d="M74 50h18l-2 78H70z"/><path d="M105 50h18l1 78h-20z"/><path d="M136 50h18l4 78h-20z"/>' +
  '<path d="M60 41h108q10 0 14 4l-3 3H64q-4 0-4-3z"/></g>' +
  '<g fill="#4a2ad0" opacity=".22"><rect x="76" y="58" width="12" height="2"/><rect x="76" y="70" width="12" height="2"/><rect x="107" y="58" width="13" height="2"/><rect x="107" y="70" width="13" height="2"/><rect x="138" y="58" width="13" height="2"/><rect x="138" y="70" width="13" height="2"/></g>' +
  '<path d="M44 128c4-8 10-12 14-12s10 4 14 12z" fill="#fff" opacity=".5"/>' +
  '<rect x="0" y="128" width="240" height="22" fill="#fff" opacity=".16"/>' +
  '<g fill="#fff" opacity=".18"><rect x="72" y="131" width="16" height="3" rx="1.5"/><rect x="104" y="136" width="18" height="3" rx="1.5"/><rect x="138" y="132" width="16" height="3" rx="1.5"/></g></svg>'
};
const EMPTY_ART = '<svg viewBox="0 0 160 110" aria-hidden="true"><defs><linearGradient id="eg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3f6bff"/><stop offset=".55" stop-color="#8b5cf6"/><stop offset="1" stop-color="#ec4899"/></linearGradient></defs>' +
  '<rect x="30" y="18" width="88" height="62" rx="14" fill="currentColor" opacity=".06"/><rect x="20" y="28" width="96" height="66" rx="14" fill="var(--card2)" stroke="currentColor" stroke-opacity=".14"/>' +
  '<rect x="32" y="42" width="18" height="18" rx="6" fill="url(#eg)"/><rect x="56" y="44" width="44" height="6" rx="3" fill="currentColor" opacity=".18"/><rect x="56" y="54" width="30" height="5" rx="2.5" fill="currentColor" opacity=".1"/>' +
  '<rect x="32" y="70" width="70" height="6" rx="3" fill="currentColor" opacity=".1"/><circle cx="118" cy="70" r="17" fill="none" stroke="url(#eg)" stroke-width="5"/><path d="m130 82 14 14" stroke="url(#eg)" stroke-width="6" stroke-linecap="round"/></svg>';

/* ---------- état ---------- */
let F = Object.assign({cat:"Toutes", fresh:false, prio:false, hideTracked:false, hideSummer:false, showClosed:false}, LS.get("ts_filters", {}));
F.q = "";
const saveF = () => { const c = Object.assign({}, F); delete c.q; LS.set("ts_filters", c); };
let REGION = LS.get("ts_region", "France"); if (!REGIONS.includes(REGION)) REGION = "France";
let LIMIT = 60;
let PRIO = (LS.get("ts_prio_local", null) || DATA.priority || []).slice();
let PRIOK = [];
const prioKeys = () => { PRIOK = PRIO.map(compact).filter(k => k.length >= 2); };
const isPrio = o => { const c = compact(o.company); if (!c) return false; if (!PRIOK.length && PRIO.length) prioKeys(); return PRIOK.some(k => c.includes(k)); };

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
      if (p.text) { try { const pj = JSON.parse(p.text); if (Array.isArray(pj.companies)) { PRIO = pj.companies.slice(); prioKeys(); LS.set("ts_prio_local", PRIO); } } catch(e){} }
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
const GROUPS = {prio:["Entreprises prioritaires", "star"], today:["Aujourd'hui", ""], yday:["Hier", "clock"], week:["Cette semaine", "clock"],
                old:["Plus ancien", "clock"], closed:["Offres fermées", ""]};
function bucketOf(o, p){ if (o.closed) return "closed"; if (p) return "prio";
  const d = ageDays(o); return d <= 0 ? "today" : d === 1 ? "yday" : d < 7 ? "week" : "old"; }
function filtered(){
  const ql = F.q.trim().toLowerCase();
  const rows = [];
  for (const o of (DATA.offers || [])) {
    if (regOf(o) !== REGION || (F.cat !== "Toutes" && o.category !== F.cat) || (!F.showClosed && o.closed) || (F.fresh && !isFresh(o)) ||
        (F.hideTracked && candFor(o.uid)) || (F.hideSummer && o.summer)) continue;
    if (ql && !(o.title + " " + o.company + " " + cityOf(o) + " " + o.location + " " + o.source).toLowerCase().includes(ql)) continue;
    const p = isPrio(o); if (F.prio && !p) continue;
    rows.push({o, p, t:pubTs(o)});
  }
  rows.sort((a, b) => ((a.o.closed ? 1 : 0) - (b.o.closed ? 1 : 0)) || ((b.p ? 1 : 0) - (a.p ? 1 : 0)) ||
      (b.t - a.t) || (b.o.first_seen - a.o.first_seen));
  return rows;
}
function statusChip(it){ const s = ST[it.status] || ST.a_postuler;
  return '<button type="button" class="status" data-act="status" style="color:var(' + s.v + ')"><i></i>' + esc(s.label) + '</button>'; }
function cardHTML(r, i, animate){
  const o = r.o, prio = r.p, it = candFor(o.uid), link = safeUrl(o.apply_url || o.url), cv = CATVAR[o.category] || "--mute";
  const direct = o.apply_url && o.apply_url !== o.url, city = cityOf(o), pl = o.posted ? pubLabel(o) : "";
  return '<article class="card' + (prio ? " prio" : "") + (o.closed ? " closed" : "") + (animate ? " enter" : "") + '" style="--i:' + i + ';--c:var(' + cv + ')" data-uid="' + esc(o.uid) + '">' +
    '<div class="ch"><div class="av" style="' + avStyle(o.company) + '">' + esc(initials(o.company)) + '</div>' +
    '<div class="who"><div class="co">' + (prio ? '<span class="star" title="Entreprise prioritaire">★</span>' : "") + '<span class="nm">' + esc(o.company || "—") + '</span></div>' +
    '<div class="where">' + (city ? icon("pin") + '<span class="city">' + esc(city) + '</span>' : "") + (pl ? (city ? '<span class="sep">·</span>' : "") + '<span title="Date de publication">' + esc(pl) + '</span>' : "") + '</div></div>' +
    (o.closed ? '<span class="badge cl">Fermée</span>' : isFresh(o) ? '<span class="badge new">NOUVEAU</span>' : "") + '</div>' +
    '<h3 class="ttl">' + esc(o.title) + '</h3><div class="meta">' +
    '<span class="tag"><span class="ti">' + icon(CATICO[o.category] || "all") + '</span>' + esc(o.category) + '</span>' +
    (o.summer ? '<span class="tag plain" style="--c:var(--mute)">Summer</span>' : "") +
    '<span class="via">via ' + esc(o.source) + '</span>' +
    (direct ? '<a href="' + esc(safeUrl(o.url)) + '" target="_blank" rel="noopener">Offre ' + esc(o.source) + '</a>' : "") +
    (o.others || []).map(x => '<a href="' + esc(safeUrl(x.url)) + '" target="_blank" rel="noopener">' + esc(x.source) + '</a>').join("") +
    '</div><div class="cf">' + (it ? statusChip(it) : '<button type="button" class="btn" data-act="track"><span class="gl">＋</span>Suivre</button>') +
    '<a class="btn primary" data-act="apply" href="' + esc(link) + '" target="_blank" rel="noopener">' + (direct ? "Postuler" : "Voir l'offre") + '<span class="gl">↗</span></a></div></article>';
}
let firstPaint = true, artRegion = null;
function renderOffers(){
  const all = DATA.offers || [];
  const regCount = {France:0, Suisse:0, Singapour:0}, open = [];
  for (const o of all) if (!o.closed) { const rg = regOf(o); regCount[rg]++; if (rg === REGION) open.push(o); }
  $$("#regions .reg").forEach(b => { b.setAttribute("aria-pressed", String(b.dataset.region === REGION)); b.querySelector(".n").textContent = regCount[b.dataset.region]; });
  const counts = {Toutes: open.length}; for (const o of open) counts[o.category] = (counts[o.category] || 0) + 1;
  if (F.cat !== "Toutes" && !counts[F.cat]) F.cat = "Toutes";
  $("#cats").innerHTML = [["Toutes", null, "all"]].concat(CATS).filter(c => c[0] === "Toutes" || counts[c[0]])
    .map(c => '<button type="button" class="chip' + (F.cat === c[0] ? " on" : "") + '" data-cat="' + esc(c[0]) + '"' + (c[1] ? ' style="--c:var(' + c[1] + ')"' : "") + '>' +
      '<span class="ci">' + icon(c[2]) + '</span>' + esc(c[0]) + ' <span class="n num">' + (counts[c[0]] || 0) + '</span></button>').join("");
  $$(".toggles .chip").forEach(b => b.classList.toggle("on", !!F[b.dataset.t]));
  const rows = filtered(), L = $("#list");
  if (!rows.length) L.innerHTML = '<div class="empty">' + EMPTY_ART + (all.length ? (open.length ? "<b>Aucune offre avec ces filtres</b>Essaie d'élargir ta recherche ou de retirer un filtre."
      : "<b>Aucune offre en " + esc(REGION) + " pour l'instant</b>Le tracker cherche en continu et te préviendra dès qu'une offre apparaît.")
    : "<b>Aucune offre pour l'instant</b>Le tracker cherche en continu et te préviendra dès qu'une offre apparaît.") + '</div>';
  else {
    const gcount = {}, bk = rows.map(r => { const b = bucketOf(r.o, r.p); gcount[b] = (gcount[b] || 0) + 1; return b; });
    let html = "", cur = null; const n = Math.min(LIMIT, rows.length);
    for (let i = 0; i < n; i++) {
      if (bk[i] !== cur) { if (cur !== null) html += "</div></section>"; cur = bk[i]; const g = GROUPS[cur];
        html += '<section class="grp g-' + cur + '"><h2 class="gh">' + (cur === "today" ? '<span class="gd"></span>' : g[1] ? icon(g[1]) : "") + '<span>' + esc(g[0]) + '</span><span class="gc num">' + gcount[cur] + '</span></h2><div class="grid">'; }
      html += cardHTML(rows[i], i, firstPaint && i < 14);
    }
    L.innerHTML = html + "</div></section>";
  }
  $("#more").innerHTML = rows.length > LIMIT ? '<button type="button" class="btn" id="moreBtn">Afficher ' + Math.min(60, rows.length - LIMIT) +
    ' offres de plus · ' + (rows.length - LIMIT) + ' restantes</button>' : "";
  firstPaint = false;
  const hero = $("#hero");
  if (artRegion !== REGION) { artRegion = REGION; $("#heroArt").innerHTML = ART[REGION]; hero.className = "stat hero r-" + REGION; $("#heroReg").textContent = REGION; }
  const cc = {}; for (const o of open) { const c = cityOf(o); if (c) cc[c] = (cc[c] || 0) + 1; }
  const top = Object.keys(cc).sort((a, b) => cc[b] - cc[a]).slice(0, 2);
  $("#heroCities").textContent = top.length ? top.join(" · ") : REGDEF[REGION];
  const nFresh = open.filter(isFresh).length;
  $("#heroNew").textContent = nFresh ? "dont " + nFresh + " nouvelle" + (nFresh > 1 ? "s" : "") : "";
  countUp($("#sAll"), open.length); countUp($("#sFresh"), nFresh); countUp($("#sPrio"), open.filter(isPrio).length);
  $("#cntOffres").textContent = regCount.France + regCount.Suisse + regCount.Singapour;
}
function renderSources(){
  const S = (DATA.sources || []).slice().sort((a, b) => (b.ok - a.ok) || a.name.localeCompare(b.name));
  $("#srcSum").textContent = S.filter(s => s.ok).length + " / " + S.length + " actives";
  $("#src").innerHTML = S.map(s => '<div class="srcrow"><span class="dot" style="background:var(' + (s.ok ? "--ok" : /Non lisible/.test(s.message) ? "--mute2" : "--err") +
    ')"></span><div><b style="color:var(--ink);font-weight:650">' + esc(s.name) + '</b> · ' + esc(s.message) + ' · ' + esc(hm(s.last_run)) + '</div></div>').join("");
}
function renderHeader(){
  const g = DATA.generated, nx = DATA.next_run;
  $("#upd").innerHTML = 'Mis à jour à ' + hm(g) + (nx && nx * 1000 > Date.now() ? '<span class="lt"> · prochaine recherche vers ' + hm(nx) + '</span>' : "");
  $("#liveDot").style.background = nowS() - g < 40 * 60 ? "var(--ok)" : "var(--warn)";
}

function renderRejected(){
  const R = (DATA.rejected || []).filter(r => regOf(r) === REGION), ql = ($("#qr").value || "").trim().toLowerCase();
  $("#rejSum").textContent = R.length + " offre" + (R.length > 1 ? "s" : "");
  if (!$("#rejBox").open) return;  // rendu seulement quand la section est ouverte
  const rows = R.filter(r => !ql || ((r.company || "") + " " + r.title + " " + r.reason).toLowerCase().includes(ql)).slice(0, 300);
  $("#rej").innerHTML = rows.length ? rows.map(r => '<div class="rejrow"><span style="color:var(--mute);flex:none">' + esc(r.company || "—") + '</span>' +
    '<a href="' + esc(safeUrl(r.url)) + '" target="_blank" rel="noopener">' + esc(r.title) + '</a><span class="why">' + esc(r.reason) + '</span></div>').join("")
    : '<div class="hint">Aucune offre écartée sur la période.</div>';
}

/* ---------- rendu : candidatures (toutes régions) ---------- */
function renderCand(){
  const ql = ($("#qc").value || "").trim().toLowerCase(), all = Object.values(CAND.items);
  const items = all.filter(it => !ql || (it.company + " " + it.title + " " + (it.notes || "")).toLowerCase().includes(ql)).sort((a, b) => (b.u || 0) - (a.u || 0));
  const by = {}; for (const s of STATUSES) by[s[0]] = [];
  for (const it of items) (by[it.status] || by.a_postuler).push(it);
  const cnt = s => all.filter(x => x.status === s).length, total = all.length || 1;
  $("#pipe").innerHTML = STATUSES.filter(s => cnt(s[0])).map(s => '<span style="width:' + (100 * cnt(s[0]) / total).toFixed(2) + '%;background:var(' + s[2] + ')" title="' + esc(s[1]) + '"></span>').join("");
  $("#pipeLegend").innerHTML = all.length ? STATUSES.filter(s => cnt(s[0])).map(s => '<span class="chip" style="cursor:default;padding:7px 13px"><span class="dot" style="background:var(' + s[2] + ')"></span>' +
    esc(s[1]) + ' <span class="n num">' + cnt(s[0]) + '</span></span>').join("") : '<span style="color:var(--mute);font-size:13.5px">Aucune candidature pour l\'instant. Clique sur « Suivre » sur une offre, ou ajoute une candidature à la main.</span>';
  const offerBy = Object.fromEntries((DATA.offers || []).map(o => [o.uid, o]));
  $("#kanban").innerHTML = STATUSES.map(s => '<div class="col" data-st="' + s[0] + '"><div class="colh"><span style="width:9px;height:9px;border-radius:50%;background:var(' + s[2] + ')"></span>' +
    esc(s[1]) + '<span class="n num">' + by[s[0]].length + '</span></div>' +
    (by[s[0]].length ? by[s[0]].map(it => { const o = it.offer && offerBy[it.offer];
      return '<div class="kc" draggable="true" data-id="' + esc(it.id) + '"><div class="c"><span class="av" style="' + avStyle(it.company) + '">' + esc(initials(it.company)) + '</span>' +
        '<span>' + esc(it.company) + (o && o.closed ? ' · <span style="color:var(--err)">offre fermée</span>' : "") + '</span></div><div class="t">' + esc(it.title) + '</div>' +
        '<div class="m">' + (it.applied ? '<span>Envoyée le ' + esc(new Date(it.applied + "T12:00:00").toLocaleDateString("fr-FR", {day:"numeric", month:"short"})) + '</span>' : "") +
        '<span>Màj ' + esc(dshort(it.u || it.created)) + '</span>' + (it.url ? '<a href="' + esc(safeUrl(it.url)) + '" target="_blank" rel="noopener">Offre ↗</a>' : "") + '</div>' +
        (it.notes ? '<div class="note">' + esc(it.notes) + '</div>' : "") + '</div>'; }).join("") : '<div class="colempty">Glisse une carte ici</div>') + '</div>').join("");
  countUp($("#sCand"), all.filter(x => IN_PROGRESS.has(x.status)).length); $("#cntCand").textContent = all.length;
}
function renderAll(){ renderHeader(); renderOffers(); renderCand(); }

/* ---------- navigation ---------- */
function moveInk(){ const b = $('.tab[aria-selected="true"]'), ink = $("#ink"); if (!b) return;
  ink.style.width = b.offsetWidth + "px"; ink.style.transform = "translateX(" + b.offsetLeft + "px)"; }
function go(view){ $$(".tab").forEach(t => t.setAttribute("aria-selected", String(t.dataset.view === view)));
  $$(".view").forEach(v => v.classList.toggle("on", v.id === "view-" + view)); moveInk(); LS.set("ts_view", view); }
$$(".tab").forEach(t => t.onclick = () => go(t.dataset.view));
window.addEventListener("resize", debounce(moveInk, 100));
$("#regions").onclick = e => { const b = e.target.closest("[data-region]"); if (!b || b.dataset.region === REGION) return;
  REGION = b.dataset.region; LS.set("ts_region", REGION); LIMIT = 60; renderOffers(); renderRejected(); };
$$(".stat").forEach(s => s.onclick = () => { const g = s.dataset.go;
  if (g === "cand") return go("cand");
  F.cat = "Toutes"; F.fresh = g === "fresh"; F.prio = g === "prio"; saveF(); LIMIT = 60; renderOffers(); });
$("#cats").onclick = e => { const b = e.target.closest("[data-cat]"); if (!b) return; F.cat = b.dataset.cat; saveF(); LIMIT = 60; renderOffers(); };
$$(".toggles .chip").forEach(b => b.onclick = () => { F[b.dataset.t] = !F[b.dataset.t]; saveF(); LIMIT = 60; renderOffers(); });
$("#q").addEventListener("input", debounce(e => { F.q = e.target.value; LIMIT = 60; renderOffers(); }, 120));
$("#qc").addEventListener("input", debounce(renderCand, 120));
$("#qr").addEventListener("input", debounce(renderRejected, 150));
$("#rejBox").addEventListener("toggle", renderRejected);
$("#more").onclick = e => { if (e.target.id === "moreBtn") { LIMIT += 60; renderOffers(); } };

/* ---------- menu de statut ---------- */
let menuEl = null, menuY = 0;
function closeMenu(){ if (menuEl) { menuEl.remove(); menuEl = null; } }
function statusMenu(anchor, it){
  closeMenu(); if (!it) return; const m = document.createElement("div"); m.className = "menu";
  m.innerHTML = STATUSES.map(s => '<button type="button" data-s="' + s[0] + '"><i style="background:var(' + s[2] + ')"></i>' + esc(s[1]) + (it.status === s[0] ? " ✓" : "") + '</button>').join("") +
    '<button type="button" data-s="__edit" style="border-top:1px solid var(--line);margin-top:4px;padding-top:10px;border-radius:0 0 12px 12px">✎ Notes et détails…</button>';
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
async function commitPrio(){ prioKeys(); renderPrio(); renderOffers();
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
    DATA = d; if (!LS.get("ts_prio_local", null) && Array.isArray(d.priority)) { PRIO = d.priority.slice(); prioKeys(); }
    renderAll(); renderSources(); renderRejected();
    if (fresh.length) toast(fresh.length + (fresh.length > 1 ? " nouvelles offres" : " nouvelle offre"), "Voir", () => {
      const rg = regOf(fresh[0]); if (rg !== REGION && !fresh.some(o => regOf(o) === REGION)) { REGION = rg; LS.set("ts_region", REGION); renderOffers(); renderRejected(); }
      go("offres"); window.scrollTo({top:0, behavior:"smooth"}); });
  } catch(e) {}
}
setInterval(refreshData, 120000);
setInterval(renderHeader, 30000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) { refreshData(); if (Sync.enabled()) Sync.pull().catch(() => {}); } });

/* ---------- démarrage ---------- */
prioKeys();
renderAll(); renderSources(); renderRejected();
go(LS.get("ts_view", "offres") === "cand" ? "cand" : "offres");
requestAnimationFrame(moveInk);
if (document.fonts && document.fonts.ready) document.fonts.ready.then(moveInk);
Sync.show(Sync.enabled() ? "busy" : "off", Sync.enabled() ? "Synchronisation…" : "Local");
if (Sync.enabled()) Sync.pull().catch(() => {});
</script></body></html>"""
