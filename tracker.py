#!/usr/bin/env python3
"""Tracker de stages off-cycle / césure à Paris : IBD (M&A, PE, VC) et Sales & Trading.

Usage :
    python tracker.py              surveillance continue (notifications + tableau de bord)
    python tracker.py --check      diagnostic : teste chaque source sans rien enregistrer
    python tracker.py --test-notif envoie une notification de test
    python tracker.py --once       un seul passage puis arrêt
    python tracker.py --reset      efface la mémoire des offres (repart de zéro)
"""
import argparse
import copy
import json
import os
import random
import sys
import time
import traceback
import webbrowser
from datetime import datetime

# Console Windows / lancement sans console (pythonw) : jamais de plantage sur un affichage
for _name in ("stdout", "stderr"):
    _s = getattr(sys, _name)
    if _s is None:
        setattr(sys, _name, open(os.devnull, "w", encoding="utf-8"))
    else:
        try:
            _s.reconfigure(errors="replace")
        except Exception:
            pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import dashboard  # noqa: E402
import filters  # noqa: E402
import notify  # noqa: E402
import sources  # noqa: E402
from store import Store  # noqa: E402

DATA = os.path.join(HERE, "data")
CONFIG_PATH = os.path.join(HERE, "config.json")
DB_PATH = os.path.join(DATA, "offres.db")
DASH_PATH = os.path.join(DATA, "tableau_de_bord.html")
LOG_PATH = os.path.join(DATA, "tracker.log")

DEFAULT_CONFIG = {
    "interval_minutes": 10,
    "linkedin": {
        "enabled": True,
        "location": "Paris, Île-de-France, France",
        "past_seconds": 604800,
        "pages_per_query": 1,
        "pause_between_queries": [3, 7],
        "detail_limit_per_cycle": 25,
        "queries": [
            "stage M&A",
            "stage fusions acquisitions",
            "stage banque d'affaires",
            "investment banking intern",
            "off-cycle internship",
            "stage private equity",
            "stage capital investissement",
            "stage venture capital",
            "stage sales trading",
            "stage salle des marchés",
            "stage trading",
            "global markets internship",
        ],
    },
    "wttj": {
        "enabled": True,
        "queries": [
            "M&A", "fusions acquisitions", "banque d'affaires", "corporate finance", "private equity",
            "capital investissement", "LBO", "venture capital", "sales trading", "trading", "marchés financiers",
        ],
    },
    "workday": {
        "enabled": True,
        "queries": ["intern Paris", "stage Paris", "off-cycle"],
        "tenants": [
            {"company": "Barclays", "host": "barclays.wd3.myworkdayjobs.com", "tenant": "barclays",
             "site": "External_Career_Site_Barclays", "enabled": True},
            {"company": "Deutsche Bank", "host": "db.wd3.myworkdayjobs.com", "tenant": "db",
             "site": "DBWebsite", "enabled": True},
            {"company": "Citi", "host": "citi.wd5.myworkdayjobs.com", "tenant": "citi",
             "site": "2", "enabled": True},
        ],
    },
    "filters": {
        "max_age_days": 30,
        "extra_include": [],
        "extra_exclude": [],
        "include_summer": True,
    },
    "notifications": {
        "max_individual": 5,
        "open_dashboard_on_start": True,
    },
    "cloud": {
        "ntfy_topic": "",
        "dashboard_url": "",
    },
}

# Fonctions remplacées en mode --cloud (notifications ntfy, lien public du tableau de bord)
SEND = notify.notify


def dash_link():
    return dashboard.file_url(DASH_PATH)


# ----------------------------------------------------------------------------- utilitaires
def log(msg):
    line = "[%s] %s" % (datetime.now().strftime("%d/%m %H:%M:%S"), msg)
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        if os.path.getsize(LOG_PATH) > 2_000_000:  # rotation simple
            os.replace(LOG_PATH, LOG_PATH + ".old")
    except Exception:
        pass


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        return copy.deepcopy(DEFAULT_CONFIG)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        try:
            user = json.load(f)
        except json.JSONDecodeError as e:
            sys.exit("config.json invalide (ligne %d) : %s\nCorrige le fichier ou supprime-le pour le régénérer."
                     % (e.lineno, e.msg))
    return _merge(DEFAULT_CONFIG, user)


def too_old(posted, cfg):
    """Vrai si la date de publication (AAAA-MM-JJ) dépasse filters.max_age_days."""
    if not posted:
        return False
    try:
        d = datetime.strptime(posted[:10], "%Y-%m-%d")
    except ValueError:
        return False
    return (datetime.now() - d).days > int(cfg["filters"].get("max_age_days", 30))


# ----------------------------------------------------------------------------- collecte
class Tracker:
    def __init__(self, cfg, store):
        self.cfg = cfg
        self.store = store
        self.backoff = {}      # source -> timestamp avant lequel on ne réessaie pas
        self.backoff_len = {}  # source -> durée actuelle du backoff (s)
        for name in ("LinkedIn", "Welcome to the Jungle", "Sites carrières Workday"):
            try:
                self.backoff[name] = float(store.get_meta("backoff:" + name, 0))
                self.backoff_len[name] = float(store.get_meta("backoff_len:" + name, 0)) or None
                if not self.backoff_len[name]:
                    self.backoff_len.pop(name)
            except ValueError:
                pass

    def _save_backoff(self, name):
        self.store.set_meta("backoff:" + name, self.backoff.get(name, 0))
        self.store.set_meta("backoff_len:" + name, self.backoff_len.get(name, 0))
        self.pending = {}      # offres LinkedIn à confirmer (stage ?) en attente de détail

    def _classify(self, j, description="", employment_type=""):
        f = self.cfg["filters"]
        r = filters.classify(j["title"], j.get("location", ""), description,
                             employment_type or j.get("employment_type", ""),
                             f.get("extra_include"), f.get("extra_exclude"))
        if r["ok"] and r["summer"] and not f.get("include_summer", True):
            r["ok"], r["reason"] = False, "summer exclu (config)"
        return r

    def _run_source(self, name, fn):
        now = time.time()
        if self.backoff.get(name, 0) > now:
            mins = int((self.backoff[name] - now) / 60) + 1
            self.store.set_source(name, False, "En pause %d min (limitation du site)" % mins)
            return []
        try:
            res = fn()
            errs = []
            if isinstance(res, tuple):
                res, errs = res
            if self.backoff_len.pop(name, None):
                self._save_backoff(name)
            msg = "OK : %d offres analysées" % len(res)
            if errs:
                msg += " · erreurs : " + "; ".join(errs)
            self.store.set_source(name, not (errs and not res), msg, len(res))
            return res
        except sources.RateLimited as e:
            d = min(max(self.backoff_len.get(name, 600) * 2, 900), 7200)
            self.backoff_len[name] = d
            self.backoff[name] = now + d
            self._save_backoff(name)
            log("%s : limité par le site (%s), pause de %d min" % (name, e, d // 60))
            self.store.set_source(name, False, "Limité par le site, pause %d min" % (d // 60))
        except Exception as e:
            log("%s : ERREUR %s" % (name, e))
            self.store.set_source(name, False, "Erreur : %s" % str(e)[:200])
        return []

    def collect(self):
        c = self.cfg
        batches = []
        if c["linkedin"]["enabled"]:
            batches.append(("LinkedIn", self._run_source("LinkedIn", lambda: sources.collect_linkedin(c, log))))
        if c["wttj"]["enabled"]:
            batches.append(("Welcome to the Jungle",
                            self._run_source("Welcome to the Jungle", lambda: sources.collect_wttj(c, log))))
        if c["workday"]["enabled"] and c["workday"]["tenants"]:
            batches.append(("Sites carrières Workday",
                            self._run_source("Sites carrières Workday", lambda: sources.collect_workday(c, log))))
        return batches

    def _accept(self, j, r, seed, new_list):
        seed = seed or self.store.in_seed(j["uid"])
        j["category"], j["summer"] = r["category"], r["summer"]
        j["dedup_key"] = filters.dedup_key(j.get("company"), j["title"])
        dup = self.store.find_duplicate(j["dedup_key"])
        notified = not seed and dup is None
        self.store.add_offer(j, notified=notified, duplicate_of=dup)
        if dup is None:
            log("  ✔ %s · %s · %s" % (j.get("company"), j["title"], j["category"]))
            if notified:
                new_list.append(j)

    def cycle(self):
        new_list, seeded_now = [], []
        details_budget = self.cfg["linkedin"]["detail_limit_per_cycle"]
        detail_queue = []
        for name, jobs in self.collect():
            seed = self.store.get_meta("seeded:" + name) is None
            for j in jobs:
                j["uid"] = "%s:%s" % (j["source"], j["ext_id"])
                if self.store.known(j["uid"]):
                    continue
                if too_old(j.get("posted"), self.cfg):
                    self.store.add_rejected(j["uid"], "publiée il y a trop longtemps")
                    continue
                r = self._classify(j)
                if j["source"] == "LinkedIn" and (r["ok"] or r["intern"] == "unknown"):
                    # On va chercher le lien carrière (et confirmer le stage si besoin)
                    detail_queue.append((0 if r["ok"] else 1, j, r, seed))
                elif r["ok"]:
                    self._accept(j, r, seed, new_list)
                else:
                    self.store.add_rejected(j["uid"], r["reason"] or "?")
            if seed and jobs:
                seeded_now.append(name)

        # Offres LinkedIn retenues d'abord, puis celles à confirmer
        detail_queue.sort(key=lambda x: x[0])
        for i, (prio, j, r, seed) in enumerate(detail_queue):
            if details_budget <= 0 or self.backoff.get("LinkedIn", 0) > time.time():
                if prio == 0:  # stage certain : on notifie avec le lien LinkedIn, sans attendre
                    self._accept(j, r, seed, new_list)
                elif seed:
                    self.store.mark_seed(j["uid"])  # existait déjà au 1er passage : pas de notification
                continue  # "à confirmer" : sera retenté au prochain passage
            details_budget -= 1
            try:
                d = sources.linkedin_detail(j["ext_id"])
                j["apply_url"] = d["apply_url"]
                r2 = self._classify(j, d["description"], d["employment_type"])
                if prio == 0 and r2["intern"] == "no" and filters.INTERN_TITLE.search(filters.normalize(j["title"])):
                    r2 = r  # le titre dit "stage" : on garde la décision initiale
                if r2["ok"]:
                    self._accept(j, r2, seed, new_list)
                else:
                    self.store.add_rejected(j["uid"], r2["reason"] or "?")
            except sources.RateLimited as e:
                self.backoff["LinkedIn"] = time.time() + 900
                self._save_backoff("LinkedIn")
                log("LinkedIn (détails) : limité (%s), reprise dans 15 min" % e)
                if prio == 0:
                    self._accept(j, r, seed, new_list)
                elif seed:
                    self.store.mark_seed(j["uid"])
            except Exception as e:
                log("LinkedIn détail %s : %s" % (j["ext_id"], e))
                if prio == 0:
                    self._accept(j, r, seed, new_list)
                elif seed:
                    self.store.mark_seed(j["uid"])
            if i < len(detail_queue) - 1:
                time.sleep(random.uniform(1.5, 3.5))

        for name in seeded_now:
            self.store.set_meta("seeded:" + name, "1")
        self.store.prune()
        return new_list, seeded_now

    def notify_new(self, new_list):
        mx = self.cfg["notifications"]["max_individual"]
        if not new_list:
            return
        if len(new_list) <= mx:
            for j in new_list:
                SEND(
                    "%s · %s" % (j.get("company") or "Nouvelle offre", j["category"]),
                    "%s\n%s · %s" % (j["title"], j.get("location") or "Paris", j["source"]),
                    j.get("apply_url") or j["url"])
                time.sleep(1)
        else:
            SEND("%d nouvelles offres de stage à Paris" % len(new_list),
                 ", ".join(sorted({j.get("company") or "?" for j in new_list}))[:200],
                 dash_link(), button="Voir le tableau")


# ----------------------------------------------------------------------------- modes
def write_dashboard(store, cfg, next_run=None):
    offers = []
    for o in store.offers():
        if too_old(o.get("posted"), cfg) or not filters.is_paris(o.get("location"), o["title"]):
            continue
        cat, _ = filters.categorize(o["title"])  # applique aussi les corrections de filtre aux offres déjà vues
        if cat is None and o["category"] != "Autre (mot-clé perso)":
            continue
        o["category"] = cat or o["category"]
        offers.append(o)
    for o in offers:
        o["others"] = store.other_links(o["uid"])
    dashboard.write(DASH_PATH, offers, store.sources(), next_run, cfg["interval_minutes"])


def run_check(cfg):
    print("Diagnostic des sources (rien n'est enregistré)\n")
    print("Notifications : %s\n" % notify.backend_name())
    t = Tracker(cfg, Store(":memory:"))
    tests = []
    if cfg["linkedin"]["enabled"]:
        c2 = copy.deepcopy(cfg)
        c2["linkedin"]["queries"] = cfg["linkedin"]["queries"][:2]
        tests.append(("LinkedIn (2 requêtes)", lambda: sources.collect_linkedin(c2, log)))
    if cfg["wttj"]["enabled"]:
        c3 = copy.deepcopy(cfg)
        c3["wttj"]["queries"] = cfg["wttj"]["queries"][:2]
        tests.append(("Welcome to the Jungle (2 requêtes)", lambda: sources.collect_wttj(c3, log)))
    if cfg["workday"]["enabled"]:
        tests.append(("Workday", lambda: sources.collect_workday(cfg, log)))
    all_ok = True
    for name, fn in tests:
        try:
            res = fn()
            errs = []
            if isinstance(res, tuple):
                res, errs = res
            kept = [j for j in res if t._classify(j)["ok"]]
            maybe = [j for j in res if j["source"] == "LinkedIn" and not t._classify(j)["ok"]
                     and t._classify(j)["intern"] == "unknown"]
            print("%s %s : %d offres reçues, %d retenues%s"
                  % ("❌" if errs and not res else ("⚠️ " if errs else "✅"), name, len(res), len(kept),
                     (", %d à confirmer via la description" % len(maybe)) if maybe else ""))
            for e in errs:
                all_ok = False
                print("   ⚠️  %s" % e)
            for j in kept[:5]:
                print("     · %s | %s | %s" % (j.get("company"), j["title"], j.get("location")))
            if res and res[0]["source"] == "LinkedIn":
                try:
                    d = sources.linkedin_detail(res[0]["ext_id"])
                    print("   Lien carrière extrait : %s" % (d["apply_url"] or "aucun (candidature via LinkedIn)"))
                except Exception as e:
                    print("   ⚠️  détail LinkedIn : %s" % e)
        except Exception as e:
            all_ok = False
            print("❌ %s : %s" % (name, e))
        print()
    print("Résultat : %s" % ("tout fonctionne." if all_ok else
                             "au moins une source a un problème (le tracker continue avec les autres)."))


def main():
    ap = argparse.ArgumentParser(description="Tracker de stages Paris (IBD / S&T)")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--test-notif", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--cloud", action="store_true", help="un passage, notifications ntfy, tableau dans docs/")
    args = ap.parse_args()

    os.makedirs(DATA, exist_ok=True)
    cfg = load_config()

    if args.cloud:
        global SEND, DASH_PATH, dash_link
        topic = os.environ.get("NTFY_TOPIC") or cfg["cloud"]["ntfy_topic"]
        if not topic:
            sys.exit("Mode --cloud : renseigne cloud.ntfy_topic dans config.json")
        notify.NTFY_TOPIC = topic
        SEND = notify.ntfy
        os.makedirs(os.path.join(HERE, "docs"), exist_ok=True)
        # Publie la page telle quelle sur GitHub Pages, sans passer par Jekyll
        open(os.path.join(HERE, "docs", ".nojekyll"), "a").close()
        DASH_PATH = os.path.join(HERE, "docs", "index.html")
        url = cfg["cloud"]["dashboard_url"]
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        if not url and "/" in repo:
            owner, name = repo.split("/", 1)
            url = "https://%s.github.io/%s/" % (owner.lower(), name)
        dash_link = (lambda: url) if url else (lambda: None)
        args.once, args.no_browser = True, True

    if args.test_notif:
        shown = SEND("Rothschild & Co · M&A / IBD", "Stage M&A (test)\nParis · LinkedIn",
                              "https://www.linkedin.com/jobs/")
        print("Notification système : %s (%s)" % ("affichée" if shown else "non disponible", notify.backend_name()))
        return
    if args.check:
        run_check(cfg)
        return
    if args.reset and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Mémoire effacée.")

    # Une seule instance : si le tracker tourne déjà, on ouvre simplement le tableau de bord
    lock = os.path.join(DATA, "tracker.pid")
    try:
        if args.cloud:
            raise OSError
        pid = int(open(lock).read().strip())
        if os.name == "nt":
            raise OSError  # os.kill(pid, 0) n'est pas un test sans effet sous Windows
        os.kill(pid, 0)
        if pid != os.getpid():
            print("Le tracker tourne déjà. Ouverture du tableau de bord.")
            webbrowser.open(dashboard.file_url(DASH_PATH))
            return
    except Exception:
        pass
    if not args.cloud:
        with open(lock, "w") as f:
            f.write(str(os.getpid()))

    store = Store(DB_PATH)
    tracker = Tracker(cfg, store)
    write_dashboard(store, cfg)
    log("Tracker démarré · notifications : %s · tableau de bord : %s" % (notify.backend_name(), DASH_PATH))
    if cfg["notifications"]["open_dashboard_on_start"] and not args.no_browser and not args.once:
        webbrowser.open(dashboard.file_url(DASH_PATH))

    while True:
        start = time.time()
        log("Recherche en cours…")
        try:
            new_list, seeded = tracker.cycle()
            if seeded:
                n = len(store.offers())
                log("Premier passage pour %s : offres existantes ajoutées sans notification (%d au total)."
                    % (", ".join(seeded), n))
                SEND("Tracker prêt", "%d offres déjà en ligne sont dans le tableau de bord. "
                     "Tu seras notifié de chaque nouvelle offre." % n, dash_link(), button="Voir le tableau")
            tracker.notify_new(new_list)
            log("Passage terminé : %d nouvelle(s) offre(s) en %ds." % (len(new_list), time.time() - start))
        except KeyboardInterrupt:
            raise
        except Exception:
            log("Erreur inattendue :\n" + traceback.format_exc())
        interval = max(3, cfg["interval_minutes"]) * 60
        sleep_for = interval + random.uniform(-60, 60)
        write_dashboard(store, cfg, next_run=time.time() + sleep_for)
        if args.once:
            break
        try:
            time.sleep(max(60, sleep_for))
        except KeyboardInterrupt:
            log("Arrêt demandé.")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArrêt.")
