"""Collecteurs d'offres. Chaque collecteur renvoie une liste de dicts "offre brute".

Uniquement la bibliothèque standard (urllib) pour que l'installation soit triviale.
"""
import base64
import gzip
import html
import json
import os
import random
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import threading
import zlib

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")


class RateLimited(Exception):
    pass


class SourceError(Exception):
    pass


class Unavailable(SourceError):
    """Panne passagère (maintenance hebdomadaire Workday, page d'erreur, 5xx) : ne compte pas comme un échec durable."""
    pass


# Respect de robots.txt : lu une fois par hôte et par passage, avant toute lecture d'un site carrière
_robots_cache, _robots_lock = {}, threading.Lock()


def robots_allowed(url):
    p = urllib.parse.urlparse(url)
    host = p.netloc
    with _robots_lock:
        rp = _robots_cache.get(host)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        try:
            status, txt = http("https://%s/robots.txt" % host, headers={"Accept": "text/plain"}, timeout=15)
            lines = txt.splitlines() if status == 200 and isinstance(txt, str) else []
        except Exception:  # noqa: BLE001  robots.txt illisible : pas de règle connue
            lines = []
        rp.parse(lines)
        with _robots_lock:
            _robots_cache[host] = rp
    return rp.can_fetch(UA, url) and rp.can_fetch("*", url)


def _json_or_unavailable(status, txt, host):
    if status >= 500:
        raise Unavailable("%s : HTTP %d (maintenance probable)" % (host, status))
    try:
        return json.loads(txt)
    except ValueError:
        raise Unavailable("%s : réponse illisible (maintenance probable)" % host)


def _ssl_context():
    try:
        import certifi  # présent si "pip install certifi" (recommandé sur Mac)
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


_CTX = _ssl_context()


def http(url, method="GET", data=None, headers=None, timeout=25):
    """Renvoie (status, texte). Lève RateLimited sur 429/999, SourceError sur erreur réseau."""
    h = {
        "User-Agent": UA,
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "*/*",
    }
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8") if not isinstance(data, (bytes, str)) else (
            data.encode("utf-8") if isinstance(data, str) else data)
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            raw = r.read()
            enc = (r.headers.get("Content-Encoding") or "").lower()
            status = r.status
    except urllib.error.HTTPError as e:
        if e.code in (429, 999):
            raise RateLimited("HTTP %d sur %s" % (e.code, urllib.parse.urlparse(url).netloc))
        try:
            raw = e.read()
            enc = (e.headers.get("Content-Encoding") or "").lower()
        except Exception:
            raw, enc = b"", ""
        status = e.code
    except Exception as e:  # DNS, timeout, SSL...
        raise SourceError("%s : %s" % (urllib.parse.urlparse(url).netloc, e))
    if enc == "gzip" or raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
    elif enc == "deflate":
        try:
            raw = zlib.decompress(raw)
        except Exception:
            try:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            except Exception:
                pass
    return status, raw.decode("utf-8", errors="replace")


def _text(fragment):
    if fragment is None:
        return ""
    t = re.sub(r"<!--.*?-->", " ", fragment, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    for _ in range(3):  # certains sites échappent deux fois (&amp;amp;)
        u = html.unescape(t)
        if u == t:
            break
        t = u
    return re.sub(r"\s+", " ", t).strip()


def _first(pattern, s, flags=re.S):
    m = re.search(pattern, s, flags)
    return m.group(1) if m else None


def norm_posted(value, today=None):
    """Convertit une date de publication (ISO, "Posted 3 Days Ago", "Il y a 2 jours"...) en AAAA-MM-JJ."""
    import datetime as _dt
    today = today or _dt.date.today()
    v = (value or "").strip()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", v)
    if m:
        return m.group(1)
    low = v.lower()
    if re.search(r"today|aujourd|just|heure|hour|minute", low):
        return today.isoformat()
    if re.search(r"yesterday|hier", low):
        return (today - _dt.timedelta(days=1)).isoformat()
    m = re.search(r"(\d+)\s*\+?\s*(day|jour|week|semaine|month|mois)", low)
    if m:
        n = int(m.group(1)) + (1 if "+" in low else 0)
        unit = m.group(2)
        days = n * (7 if unit in ("week", "semaine") else 30 if unit in ("month", "mois") else 1)
        return (today - _dt.timedelta(days=days)).isoformat()
    return ""


def _pause(a, b):
    time.sleep(random.uniform(a, b))


# =====================================================================
# LinkedIn (offres publiques, sans connexion)
# =====================================================================
LI_SEARCH = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
LI_DETAIL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/%s"


def parse_linkedin_search(page):
    jobs = []
    # Un bloc par carte. On découpe sur <li pour rester robuste aux variantes de classes.
    for chunk in re.split(r"<li[\s>]", page)[1:]:
        jid = _first(r'urn:li:jobPosting:(\d+)', chunk) or _first(r'/jobs/view/[^"?]*?-(\d{6,})(?:[/?"])', chunk) \
            or _first(r'/jobs/view/(\d{6,})', chunk)
        if not jid:
            continue
        title = _text(_first(r'class="[^"]*base-search-card__title[^"]*"[^>]*>(.*?)</h3>', chunk)) \
            or _text(_first(r'<span class="sr-only">(.*?)</span>', chunk))
        company = _text(_first(r'class="[^"]*base-search-card__subtitle[^"]*"[^>]*>(.*?)</h4>', chunk))
        location = _text(_first(r'class="[^"]*job-search-card__location[^"]*"[^>]*>(.*?)</span>', chunk))
        posted = norm_posted(_first(r'<time[^>]*datetime="([^"]+)"', chunk) or "")
        href = _first(r'class="[^"]*base-card__full-link[^"]*"[^>]*href="([^"]+)"', chunk) \
            or _first(r'href="(https://[a-z]{0,3}\.?linkedin\.com/jobs/view/[^"]+)"', chunk)
        url = "https://www.linkedin.com/jobs/view/%s/" % jid
        if not title:
            continue
        jobs.append(dict(source="LinkedIn", ext_id=jid, title=title, company=company,
                         location=location, url=url, apply_url=None, posted=posted,
                         raw_href=html.unescape(href) if href else None))
    return jobs


def parse_linkedin_detail(page):
    """Renvoie dict(apply_url, description, employment_type)."""
    apply_url = None
    raw = _first(r'id="applyUrl"[^>]*>\s*<!--\s*"(.*?)"\s*-->', page)
    if raw:
        raw = html.unescape(raw)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
        if q.get("url"):
            apply_url = q["url"][0]
        elif raw.startswith("http"):
            apply_url = raw
    desc = _text(_first(r'class="[^"]*show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>', page)) \
        or _text(_first(r'class="[^"]*description__text[^"]*"[^>]*>(.*?)</section>', page))
    crit = re.findall(r'class="[^"]*description__job-criteria-text[^"]*"[^>]*>(.*?)</span>', page, re.S)
    employment = " | ".join(_text(c) for c in crit)
    return dict(apply_url=apply_url, description=desc, employment_type=employment)


def linkedin_search(query, location, past_seconds=604800, start=0, job_type=None):
    params = {
        "keywords": query,
        "location": location,
        "f_TPR": "r%d" % past_seconds,
        "sortBy": "DD",
        "start": str(start),
    }
    if job_type:
        params["f_JT"] = job_type  # "I" = stage
    url = LI_SEARCH + "?" + urllib.parse.urlencode(params)
    status, page = http(url, headers={"Accept": "text/html"})
    if status in (400, 404) and start > 0:
        return []  # plus de pages
    if status != 200:
        raise SourceError("LinkedIn HTTP %d" % status)
    return parse_linkedin_search(page)


def linkedin_detail(job_id):
    status, page = http(LI_DETAIL % job_id, headers={"Accept": "text/html"})
    if status != 200:
        raise SourceError("LinkedIn détail HTTP %d" % status)
    return parse_linkedin_detail(page)


def linkedin_tasks(cfg):
    """Liste des recherches LinkedIn, chacune avec son lieu. Les balayages de tous les stages (un par zone) passent
    toujours en premier ; les recherches par mot-clé de toutes les zones se partagent la rotation."""
    li = cfg["linkedin"]
    regions = li.get("regions") or {}
    fr = regions.get("France") or {}
    first, rest = [], []
    if fr.get("enabled", True):
        loc = fr.get("location") or li["location"]
        if li.get("sweep_all", True):
            first.append(dict(q="", past=li.get("sweep_all_seconds", 7200), jt="I", pages=li.get("sweep_all_pages", 6),
                              label="tous les stages de Paris", loc=loc, region="France"))
        rest += [dict(q=k, past=li.get("sweep_seconds", 86400), jt="I", pages=li.get("sweep_pages", 2), label=k,
                      loc=loc, region="France") for k in li.get("sweeps", [])]
        rest += [dict(q=k, past=li["past_seconds"], jt=None, pages=li.get("pages_per_query", 1), label=k, loc=loc,
                      region="France") for k in li["queries"]]
        rest += _backfill_tasks(li, fr, loc, "France", 40)
    for name, r in regions.items():
        if name == "France" or not isinstance(r, dict) or not r.get("enabled", True) or not r.get("location"):
            continue
        loc = r["location"]
        if r.get("sweep_all", True):
            first.append(dict(q="", past=r.get("sweep_all_seconds", 7200), jt="I", pages=r.get("sweep_all_pages", 4),
                              label="tous les stages · %s" % name, loc=loc, region=name))
        rest += [dict(q=k, past=r.get("sweep_seconds", li.get("sweep_seconds", 86400)), jt="I",
                      pages=r.get("sweep_pages", li.get("sweep_pages", 2)), label="%s · %s" % (k, name), loc=loc,
                      region=name) for k in r.get("sweeps", [])]
        rest += [dict(q=k, past=r.get("past_seconds", li["past_seconds"]), jt=None,
                      pages=r.get("pages_per_query", li.get("pages_per_query", 1)), label="%s · %s" % (k, name),
                      loc=loc, region=name) for k in r.get("queries", [])]
        rest += _backfill_tasks(li, r, loc, name, 20)
    return first, rest


def _backfill_tasks(li, region_cfg, loc, name, default_pages):
    """Rattrapage : tous les stages publiés dans la zone depuis 30 jours, une page de résultats par recherche,
    répartis dans la rotation (les offres plus anciennes que la fenêtre de balayage ne sont pas perdues)."""
    pages = int(region_cfg.get("backfill_pages", li.get("backfill_pages", {}).get(name, default_pages)
                               if isinstance(li.get("backfill_pages"), dict) else default_pages))
    past = int(region_cfg.get("backfill_seconds", li.get("backfill_seconds", 2592000)))
    return [dict(q="", past=past, jt="I", pages=1, start=k * 25, label="rattrapage 30 j · %s · page %d" % (name, k + 1),
                 loc=loc, region=name) for k in range(pages)]


def collect_linkedin(cfg, log, state=None):
    """Recherches LinkedIn dans la limite de max_search_requests par passage. Les recherches qui ne tiennent pas
    dans un passage sont faites au suivant (rotation), le balayage complet des stages est fait à chaque passage."""
    state = state if state is not None else {}
    li = cfg["linkedin"]
    budget = int(li.get("max_search_requests", 70))
    first, rest = linkedin_tasks(cfg)
    # LinkedIn coupe vite (429) depuis les serveurs de GitHub : la 1re page de chaque zone passe avant les suivantes
    heads = [dict(t, pages=1) for t in first]
    tails = [dict(t, pages=t["pages"] - 1, cont=t["label"], label=t["label"] + " (suite)") for t in first if t["pages"] > 1]
    first = heads + tails
    n = len(rest)
    offset = int(state.get("offset", 0)) % n if n else 0
    order = first + [rest[(offset + i) % n] for i in range(n)]
    out, errors, used, done_rest, fails_in_row = {}, [], 0, 0, 0
    known = state.get("known_ids") or set()
    resume = {}
    for idx, task in enumerate(order):
        if used >= budget:
            break
        start, seen_task, page_len = int(task.get("start", 0)), set(), 0
        if task.get("cont"):  # suite d'un balayage : reprend là où la 1re page s'est arrêtée (si elle était pleine)
            if task["cont"] not in resume:
                continue
            start, page_len = resume[task["cont"]]
        try:
            for _ in range(task["pages"]):
                if used >= budget:
                    break
                res = linkedin_search(task["q"], task.get("loc") or li["location"], task["past"], start=start,
                                      job_type=task["jt"])
                used += 1
                fresh = [j for j in res if j["ext_id"] not in seen_task]
                for j in res:
                    seen_task.add(j["ext_id"])
                    # Le filtre « Stage » de LinkedIn laisse passer des offres sponsorisées en CDI : ce n'est pas une
                    # preuve. Le type de contrat est lu sur la page de l'offre (détail) quand le titre ne le dit pas.
                    prev = out.get(j["ext_id"])
                    if prev and prev.get("employment_type") and not j.get("employment_type"):
                        j["employment_type"] = prev["employment_type"]
                    out[j["ext_id"]] = j
                page_len = page_len or len(res)
                resume.pop(task["label"], None)
                if not res or not fresh or len(res) < page_len:
                    break  # page vide, déjà vue, ou incomplète (= dernière page)
                if task["q"] == "" and task["past"] <= 86400 and known and all(j["ext_id"] in known for j in res):
                    break  # balayage trié par date : toute la page est déjà connue, la suite aussi
                start += len(res)  # pagination par nombre de résultats reçus (taille de page variable)
                resume[task["label"]] = (start, page_len)
                _pause(*li.get("pause_between_pages", [1.5, 3]))
        except RateLimited:
            if out:  # on garde ce qui a déjà été trouvé, la pause sera gérée au passage suivant
                log("LinkedIn : limitation atteinte après %d requêtes, résultats partiels conservés" % used)
                state["rate_limited"] = True
                break
            raise
        except SourceError as e:
            errors.append("« %s » : %s" % (task["label"], e))
            used += 1  # une requête en erreur compte aussi dans le budget
            fails_in_row += 1
            if fails_in_row >= 5:  # LinkedIn injoignable : inutile d'insister pendant ce passage
                break
        else:
            fails_in_row = 0
        if idx >= len(first):
            done_rest += 1
        if idx < len(order) - 1 and used < budget:
            _pause(*li["pause_between_queries"])
    state["offset"] = (offset + done_rest) % n if n else 0
    state["requests"] = used
    if errors and not out:
        raise SourceError("; ".join(errors[:3]))
    if errors:
        log("LinkedIn : %d recherche(s) en erreur : %s" % (len(errors), "; ".join(errors[:2])))
    return list(out.values())


# =====================================================================
# Welcome to the Jungle (Algolia public utilisé par leur site)
# =====================================================================
WTTJ_HOME = "https://www.welcometothejungle.com/fr/jobs"
# Clé publique de recherche (lecture seule) utilisée par le site ; réextraite de la page si elle change.
WTTJ_DEFAULT_APP = "CSEKHVMS53"
WTTJ_DEFAULT_KEY = "4bd8f6215d0cc52b26430765769e65a0"
WTTJ_INDEXES = ["wk_cms_jobs_production", "wttj_jobs_production_fr", "wttj_jobs_production"]
_wttj_state = {}


def wttj_keys_from_page():
    """Essaie de lire la clé courante dans la page du site. Renvoie dict ou None."""
    try:
        status, page = http(WTTJ_HOME, headers={"Accept": "text/html"})
    except (SourceError, RateLimited):
        return None
    if status != 200:
        return None
    app = _first(r'ALGOLIA_APPLICATION_ID\\?"?\s*[:=]\s*\\?"([A-Z0-9]{6,})', page)
    key = _first(r'ALGOLIA_API_KEY(?:_CLIENT)?\\?"?\s*[:=]\s*\\?"([a-f0-9]{24,})', page)
    if not key:
        return None
    return dict(app=app or WTTJ_DEFAULT_APP, key=key)


def _wttj_office(h):
    offices = h.get("offices")
    if not offices and isinstance(h.get("office"), dict):
        offices = [h["office"]]
    return offices or []


def parse_wttj_hits(hits):
    jobs = []
    for h in hits:
        org = h.get("organization") or {}
        slug, org_slug = h.get("slug"), org.get("slug")
        if not slug or not org_slug:
            continue
        offices = _wttj_office(h)
        loc = ", ".join(sorted({(o.get("city") or "") for o in offices if o.get("city")})) or ""
        country = {(o.get("country_code") or "").upper() for o in offices if o.get("country_code")}
        if country and "FR" not in country:
            loc = loc + " (hors France)"
        ct = h.get("contract_type") or ""
        names = h.get("contract_type_names") or {}
        if isinstance(names, dict):
            ct = " ".join(x for x in [ct, names.get("fr") or "", names.get("en") or ""] if x)
        jobs.append(dict(
            source="Welcome to the Jungle", ext_id=str(h.get("reference") or h.get("objectID") or slug),
            title=h.get("name") or "", company=org.get("name") or "", location=loc,
            url="https://www.welcometothejungle.com/fr/companies/%s/jobs/%s" % (org_slug, slug),
            apply_url=None, posted=str(h.get("published_at") or "")[:10],
            employment_type=ct.replace("_", " "),
        ))
    return jobs


WTTJ_ATTRS = ["name", "slug", "reference", "objectID", "organization", "offices", "office", "published_at",
              "contract_type", "contract_type_names"]


def wttj_query(query, app, key, index, filters, page=0, hits=50, numeric=None, attrs=None):
    params = {"query": query, "hitsPerPage": str(hits), "page": str(page)}
    if filters:
        params["filters"] = filters
    if numeric:
        params["numericFilters"] = numeric
    if attrs:
        params["attributesToRetrieve"] = json.dumps(attrs)
    url = "https://%s-dsn.algolia.net/1/indexes/*/queries" % app.lower()
    body = json.dumps({"requests": [{"indexName": index, "params": urllib.parse.urlencode(params)}]})
    return http(url, method="POST", data=body, headers={
        "X-Algolia-Application-Id": app, "X-Algolia-API-Key": key,
        "Referer": "https://www.welcometothejungle.com/", "Origin": "https://www.welcometothejungle.com",
        "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})


FILTER_CHOICES = [
    "website.reference:wttj_fr AND contract_type:internship",
    "contract_type:internship",
    "website.reference:wttj_fr",
    "",
]


def _wttj_configs():
    keys = [dict(app=WTTJ_DEFAULT_APP, key=WTTJ_DEFAULT_KEY)]
    page_keys = wttj_keys_from_page()
    if page_keys and page_keys["key"] != WTTJ_DEFAULT_KEY:
        keys.insert(0, page_keys)
    for k in keys:
        for idx in WTTJ_INDEXES:
            for flt in FILTER_CHOICES:
                yield k["app"], k["key"], idx, flt


def _wttj_find_config(probe_query):
    """Trouve une combinaison clé/index/filtre qui répond et renvoie des offres."""
    last = "aucune réponse"
    fallback = None
    for app, key, idx, flt in _wttj_configs():
        status, txt = wttj_query(probe_query, app, key, idx, flt)
        if status != 200:
            last = "HTTP %d sur %s (%s)" % (status, idx, txt[:80].replace("\n", " "))
            continue
        hits = (json.loads(txt).get("results") or [{}])[0].get("hits", [])
        if hits and parse_wttj_hits(hits):
            return dict(app=app, key=key, index=idx, filters=flt)
        if fallback is None:
            fallback = dict(app=app, key=key, index=idx, filters=flt)
    if fallback:
        return fallback
    raise SourceError("recherche WTTJ inaccessible : " + last)


def _wttj_result(txt):
    res = (json.loads(txt).get("results") or [{}])[0]
    return res.get("hits", []) or [], int(res.get("nbPages", 1) or 1)


def _wttj_options(cfg):
    """Options avancées (résultats récents, champs réduits) : abandonnées une à une si le site les refuse."""
    w = cfg["wttj"]
    days = int(w.get("recent_days", 0) or 0)
    numeric = "published_at_timestamp>%d" % (time.time() - days * 86400) if days else None
    return [(numeric, WTTJ_ATTRS), (None, WTTJ_ATTRS), (numeric, None), (None, None)]


def _wttj_pick_option(probe, opts, hits_pp):
    """Garde la première combinaison d'options qui renvoie réellement des offres lisibles."""
    s = _wttj_state
    for k, (numeric, attrs) in enumerate(opts):
        status, txt = wttj_query(probe, s["app"], s["key"], s["index"], s["filters"], 0, hits_pp, numeric, attrs)
        if status == 200 and parse_wttj_hits(_wttj_result(txt)[0]):
            s["opt"] = k
            return
    s["opt"] = len(opts) - 1  # rien de concluant : requête la plus simple


def collect_wttj(cfg, log):
    w = cfg["wttj"]
    queries = list(w["queries"]) + [c for c in w.get("companies", []) if c not in w["queries"]]
    hits_pp, max_pages = int(w.get("hits_per_page", 100)), int(w.get("max_pages", 3))
    if not _wttj_state:
        _wttj_state.update(_wttj_find_config(queries[0] if queries else "stage"))
    out, errors = {}, []
    opts = _wttj_options(cfg)
    if "opt" not in _wttj_state:
        _wttj_pick_option(w.get("probe_query", "stage"), opts, hits_pp)
    for i, q in enumerate(queries):
        page = 0
        while page < max_pages:
            s = _wttj_state
            numeric, attrs = opts[s.get("opt", 0)]
            status, txt = wttj_query(q, s["app"], s["key"], s["index"], s["filters"], page, hits_pp, numeric, attrs)
            if status == 400 and s.get("opt", 0) < len(opts) - 1:
                s["opt"] = s.get("opt", 0) + 1  # option refusée : on réessaie sans
                continue
            if status in (400, 401, 403, 404):
                opt = s.get("opt", 0)
                _wttj_state.clear()
                _wttj_state.update(_wttj_find_config(q))  # clé ou index changés : on recherche à nouveau
                _wttj_state["opt"] = opt
                s = _wttj_state
                status, txt = wttj_query(q, s["app"], s["key"], s["index"], s["filters"], page, hits_pp,
                                         *opts[opt])
            if status != 200:
                errors.append("« %s » : HTTP %d" % (q, status))
                break
            hits, nb_pages = _wttj_result(txt)
            for j in parse_wttj_hits(hits):
                out[j["ext_id"]] = j
            page += 1
            if page >= nb_pages or len(hits) < hits_pp:
                break
            _pause(0.2, 0.6)
        if i < len(queries) - 1:
            _pause(0.2, 0.6)
    if errors and not out:
        raise SourceError("WTTJ : " + "; ".join(errors[:3]))
    if errors:
        log("WTTJ : %d recherche(s) en erreur : %s" % (len(errors), "; ".join(errors[:2])))
    return list(out.values())


# =====================================================================
# Workday (API JSON publique utilisée par les sites carrières Workday)
# =====================================================================
def parse_workday(data, host, site):
    jobs = []
    for p in data.get("jobPostings", []) or []:
        path = p.get("externalPath")
        if not path:
            continue
        ref = (p.get("bulletFields") or [path])[0]
        jobs.append(dict(
            source="Site carrière", ext_id="%s:%s" % (host.split(".")[0], ref),
            title=p.get("title") or "", company=None, location=p.get("locationsText") or "",
            url="https://%s/%s%s" % (host, site, path), apply_url="https://%s/%s%s" % (host, site, path),
            posted=norm_posted(p.get("postedOn")), wd_path=path,
        ))
    return jobs


def workday_detail_locations(host, tenant, site, path):
    status, txt = http("https://%s/wday/cxs/%s/%s%s" % (host, tenant, site, path),
                       headers={"Accept": "application/json"})
    if status != 200:
        return ""
    info = json.loads(txt).get("jobPostingInfo", {})
    locs = [info.get("location") or ""] + list(info.get("additionalLocations") or [])
    return ", ".join(l for l in locs if l)


def collect_workday(cfg, log):
    out, errors = [], []
    for t in cfg["workday"]["tenants"]:
        if not t.get("enabled", True):
            continue
        host, tenant, site, company = t["host"], t["tenant"], t["site"], t["company"]
        try:
            seen = {}
            for q in cfg["workday"]["queries"]:
                status, txt = _wd_search(host, tenant, site, q)
                if status != 200 and status < 500:
                    raise SourceError("HTTP %d" % status)
                first = _json_or_unavailable(status, txt, host)
                for data in [first] + _wd_more_pages(host, tenant, site, q, first):
                    for j in parse_workday(data, host, site):
                        j["company"] = company
                        seen[j["ext_id"]] = j
                _pause(0.5, 1.5)
            for j in seen.values():
                # "3 Locations" : on va chercher la liste exacte
                if re.search(r"\d+\s+(locations|sites|lieux)", j["location"], re.I):
                    try:
                        j["location"] = workday_detail_locations(host, tenant, site, j["wd_path"]) or j["location"]
                    except Exception:
                        pass
                out.append(j)
        except RateLimited:
            errors.append("%s : limité (429)" % company)
        except (SourceError, ValueError) as e:
            errors.append("%s : %s" % (company, e))
    if errors:
        log("Workday : " + "; ".join(errors))
    return out, errors


# =====================================================================
# Sites carrières supplémentaires (un collecteur par type de site)
# =====================================================================
def _job(company, ext, title, location, url, posted=""):
    return dict(source="Site carrière", ext_id="%s:%s" % (company, ext), title=title, company=company,
                location=location or "", url=url, apply_url=url, posted=norm_posted(posted))


def _wd_search(host, tenant, site, q, offset=0):
    return http("https://%s/wday/cxs/%s/%s/jobs" % (host, tenant, site), method="POST",
                data={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": q},
                headers={"Accept": "application/json"})


WD_MAX_RESULTS = 100  # par recherche : 5 pages de 20 (Workday ne renvoie que 20 offres par page)


def _wd_more_pages(host, tenant, site, q, first_data):
    """Pages suivantes d'une recherche Workday (la 1re page ne contient que 20 offres)."""
    total = int(first_data.get("total") or 0)
    offset, pages = 20, []
    while offset < min(total, WD_MAX_RESULTS):
        _pause(0.3, 0.8)
        status, txt = _wd_search(host, tenant, site, q, offset)
        if status != 200:
            break
        try:
            data = json.loads(txt)
        except ValueError:
            break
        if not data.get("jobPostings"):
            break
        pages.append(data)
        offset += 20
    return pages


def _wd_discover(s):
    """Le nom du site Workday ou le serveur (wd1, wd3...) a changé : on essaie les variantes usuelles."""
    tenant = s["tenant"]
    base = s["host"].split(".")[0]
    hosts = [s["host"]] + ["%s.%s.myworkdayjobs.com" % (base, w) for w in ("wd1", "wd3", "wd5", "wd103", "wd12")
                           if "%s.%s.myworkdayjobs.com" % (base, w) != s["host"]]
    cap = tenant[:1].upper() + tenant[1:]
    sites = [s["site"]] + [x for x in (
        "External", "Careers", "External_Careers", "ExternalCareers", "careers", cap, tenant.upper(),
        cap + "_Careers", cap + "Careers", tenant.upper() + "_Careers", cap + "_External", "Campus",
        "EarlyCareers", "Early_Careers", "Students", "University") if x != s["site"]]
    tried = 0
    if "-" in tenant and not s.get("_tenant_variant"):
        alt = dict(s, tenant=tenant.replace("-", "_"), _tenant_variant=True)
        try:
            st, _ = _wd_search(s["host"], alt["tenant"], s["site"], "intern")
            if st == 200:
                s["tenant"] = alt["tenant"]
                return s["host"], s["site"]
        except SourceError:
            pass
    for host in hosts:
        for site in sites:
            tried += 1
            try:
                status, _ = _wd_search(host, tenant, site, "intern")
            except SourceError:
                break  # serveur inexistant : on passe au suivant
            if status == 200:
                return host, site
            if status == 404 and site == sites[0]:
                break  # ce serveur ne connaît pas l'entreprise
    raise SourceError("site Workday introuvable (%d variantes testées)" % tried)


# Recherches par défaut des sites carrières : Paris, puis Genève, Zurich et Singapour
# Recherches génériques d'abord (le moteur de recherche des sites ne fait pas toujours le lien entre "intern" et
# "internship", ni entre "London" et "Greater London") ; le lieu et le métier sont ensuite triés par le filtre.
SITE_QUERIES = ["internship", "intern", "summer internship", "summer analyst", "off-cycle", "off cycle", "placement",
                "stage", "stagiaire", "praktikum", "internship London", "internship Paris", "internship Singapore",
                "internship Geneva", "internship Zurich", "internship Dublin"]
ORACLE_QUERIES = ["internship", "intern", "summer internship", "summer analyst", "off-cycle", "placement", "stage",
                  "internship London", "internship Paris", "internship Singapore", "internship Geneva",
                  "internship Zurich", "internship Dublin"]
EIGHTFOLD_LOCATIONS = ["Paris", "Geneva", "Zurich", "Singapore", "London", "Dublin"]
EIGHTFOLD_QUERIES = ["intern", "internship", "stage", "off-cycle"]


def collect_workday_site(s):
    """Un site Workday isolé. Si l'adresse configurée ne répond pas, la bonne est recherchée et mémorisée."""
    host, tenant, site = s.get("_host") or s["host"], s["tenant"], s.get("_site") or s["site"]
    for u in ("https://%s/%s/" % (host, site), "https://%s/wday/cxs/%s/%s/jobs" % (host, tenant, site)):
        if not robots_allowed(u):
            raise SourceError("robots.txt du site interdit la lecture automatique (%s)" % urllib.parse.urlparse(u).path)
    seen = {}
    for q in s.get("queries", SITE_QUERIES):
        status, txt = _wd_search(host, tenant, site, q)
        if status in (404, 422) and not s.get("_discovered"):
            host, site = _wd_discover(s)
            tenant = s["tenant"]  # la découverte peut corriger le tenant (osv-cci -> osv_cci)
            s["_host"], s["_site"], s["_discovered"] = host, site, True
            status, txt = _wd_search(host, tenant, site, q)
        if status != 200 and status < 500:
            raise SourceError("HTTP %d" % status)
        first = _json_or_unavailable(status, txt, host)
        for data in [first] + _wd_more_pages(host, tenant, site, q, first):
            for j in parse_workday(data, host, site):
                if j["ext_id"] in seen:
                    continue
                if re.search(r"\d+\s+(locations|sites|lieux)", j["location"], re.I):
                    try:
                        j["location"] = workday_detail_locations(host, tenant, site, j["wd_path"]) or j["location"]
                    except Exception:
                        pass
                seen[j["ext_id"]] = _job(s["company"], j["ext_id"], j["title"], j["location"], j["url"], j["posted"])
        _pause(0.5, 1.5)
    return list(seen.values())


def parse_oracle(data, host, site_url):
    jobs = []
    for item in data.get("items", []) or []:
        for r in item.get("requisitionList", []) or []:
            rid = r.get("Id")
            if not rid:
                continue
            locs = [r.get("PrimaryLocation") or ""] + [
                (x.get("Name") or "") for x in (r.get("secondaryLocations") or []) if isinstance(x, dict)]
            jobs.append(dict(id=str(rid), title=r.get("Title") or "", location=", ".join(l for l in locs if l),
                             posted=r.get("PostedDate") or "",
                             url="https://%s/hcmUI/CandidateExperience/en/sites/%s/job/%s" % (host, site_url, rid)))
    return jobs


def _oracle_query(host, site_number, keyword, offset=0):
    finder = "findReqs;siteNumber=%s,keyword=\"%s\",limit=25,sortBy=POSTING_DATES_DESC" % (site_number, keyword)
    if offset:
        finder += ",offset=%d" % offset
    url = ("https://%s/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true"
           "&expand=requisitionList.secondaryLocations&finder=%s" % (host, urllib.parse.quote(finder, safe=";=,")))
    return http(url, headers={"Accept": "application/json"})


_oracle_site_numbers = {}


def collect_oracle_site(s):
    """Oracle Recruiting Cloud (JP Morgan, Lazard...)."""
    host, site_url = s["host"], s["site"]
    site_number = _oracle_site_numbers.get(host) or s.get("site_number") or site_url
    out = {}
    for q in s.get("queries", ORACLE_QUERIES):
        status, txt = _oracle_query(host, site_number, q)
        if status in (400, 404) and host not in _oracle_site_numbers:
            # Le numéro de site interne (CX_xxx) diffère du nom dans l'URL : on le lit dans la page
            st, page = http("https://%s/hcmUI/CandidateExperience/en/sites/%s/" % (host, site_url),
                            headers={"Accept": "text/html"})
            found = _first(r'siteNumber\W{0,6}(CX_\d+)', page) if st == 200 else None
            if not found:
                raise SourceError("HTTP %d (numéro de site introuvable)" % status)
            _oracle_site_numbers[host] = site_number = found
            status, txt = _oracle_query(host, site_number, q)
        if status != 200:
            raise SourceError("HTTP %d" % status)
        data = json.loads(txt)
        total = max([int((it or {}).get("TotalJobsCount") or 0) for it in data.get("items") or [{}]] or [0])
        pages, offset = [data], 25
        while offset < min(total, 100):  # 4 pages de 25 au plus par recherche
            _pause(0.3, 0.8)
            st2, txt2 = _oracle_query(host, site_number, q, offset)
            if st2 != 200:
                break
            pages.append(json.loads(txt2))
            offset += 25
        for d in pages:
            for j in parse_oracle(d, host, site_url):
                out[j["id"]] = _job(s["company"], j["id"], j["title"], j["location"], j["url"], j["posted"])
        _pause(0.5, 1.5)
    return list(out.values())


def parse_eightfold(data, host, domain):
    jobs = []
    for p in data.get("positions", []) or []:
        pid = p.get("id")
        if pid is None:
            continue
        locs = p.get("locations") or [p.get("location") or ""]
        ts = p.get("t_create") or p.get("t_update")
        posted = ""
        if isinstance(ts, (int, float)) and ts > 0:
            import datetime as _dt
            posted = _dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
        url = p.get("canonicalPositionUrl") or "https://%s/careers?pid=%s&domain=%s" % (host, pid, domain)
        jobs.append(dict(id=str(pid), title=p.get("name") or "", location=", ".join(l for l in locs if l),
                         posted=posted, url=url))
    return jobs


def collect_eightfold_site(s):
    """Eightfold (HSBC, Morgan Stanley...). Une série de recherches par lieu (Paris, Genève, Zurich, Singapour)."""
    host, domain = s["host"], s["domain"]
    out = {}
    for loc in s.get("locations", EIGHTFOLD_LOCATIONS):
        for q in s.get("queries", EIGHTFOLD_QUERIES):
            if q == "stage" and loc not in ("Paris", "Geneva"):
                continue  # mot français : inutile à Zurich ou Singapour
            params = {"domain": domain, "start": "0", "num": "50", "location": loc, "query": q,
                      "sort_by": "timestamp"}
            status, txt = http("https://%s/api/apply/v2/jobs?%s" % (host, urllib.parse.urlencode(params)),
                               headers={"Accept": "application/json"})
            if status != 200:
                raise SourceError("HTTP %d" % status)
            for j in parse_eightfold(json.loads(txt), host, domain):
                out[j["id"]] = _job(s["company"], j["id"], j["title"], j["location"], j["url"], j["posted"])
            _pause(0.5, 1.5)
    return list(out.values())


# Lieux reconnus dans les pages d'offres (France / Suisse / Singapour)
LOCATION_HINT = re.compile(
    r"(?<![A-Za-zÀ-ÿ])(Paris|La D[ée]fense|Puteaux|Courbevoie|Neuilly|Levallois|Boulogne|Montrouge|Saint-Denis|"
    r"Nanterre|[ÎI]le-de-France|Gen[eè]ve|Geneva|Genf|Z[uü]rich|Lausanne|Zug|Zoug|Baar|Basel|B[âa]le|Lugano|Bern|"
    r"Berne|Nyon|Lucerne|Luzern|Switzerland|Suisse|Schweiz|Singapore|Singapour|London|Londres|Canary Wharf|Dublin)"
    r"(?![A-Za-zÀ-ÿ])", re.I)
PARIS_HINT = LOCATION_HINT  # ancien nom


def parse_html_listing(page, base_url, link_regex):
    """Lit une page d'offres classique : liens d'offres + lieu indiqué dans le bloc de chaque offre.

    Le bloc d'une offre va de son premier lien jusqu'au premier lien suivant qui pointe ailleurs
    (autre offre, pagination, filtre...), pour ne pas attribuer à une offre le lieu de sa voisine.
    """
    rx = re.compile(link_regex)
    all_links = []
    for m in re.finditer(r'<a\b[^>]*?href="([^"]+)"[^>]*>(.*?)</a>', page, re.S | re.I):
        raw = html.unescape(m.group(1))
        all_links.append((m.start(), urllib.parse.urljoin(base_url, raw), _text(m.group(2)), bool(rx.search(raw))))
    texts, firsts = {}, []
    for pos, href, txt, is_job in all_links:
        if not is_job:
            continue
        if href not in texts:
            firsts.append((pos, href))
            texts[href] = txt
        elif len(txt) > len(texts[href]):
            texts[href] = txt
    jobs = []
    prev_end = 0
    for pos, href in firsts:
        end = pos + 1500
        for p2, h2, _, _ in all_links:
            if p2 > pos and h2 != href:
                end = min(end, p2)
                break
        title = texts[href]
        slug_text = re.sub(r"[-_/+]+", " ", urllib.parse.unquote(urllib.parse.urlparse(href).path))
        if len(title) < 6 or GENERIC_LINK_TEXT.fullmatch(title.strip()):
            # Lien sans texte (image) ou texte générique ("Learn more", "En savoir plus") : titre tiré de l'adresse,
            # et le bloc de l'offre est ce qui PRÉCÈDE le lien (le bouton est en bas de la carte)
            before = page[max(prev_end, pos - 1500):pos]
            heads = [_text(h) for h in re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>|<[^>]+class="[^"]*title[^"]*"[^>]*>(.*?)</',
                                                    before, re.S | re.I) for h in h if h]
            heads = [h for h in heads if len(h) >= 6 and not GENERIC_LINK_TEXT.fullmatch(h)]
            if heads:
                title = heads[-1]
            else:
                slug = urllib.parse.urlparse(href).path.rstrip("/").split("/")[-1]
                title = re.sub(r"\s+", " ", re.sub(r"[-_]+", " ", re.sub(r"\.(aspx|html?)$", "", slug))).strip()
                title = title[:1].upper() + title[1:]
            block = _text(before)[-600:]
            m = LOCATION_HINT.search(slug_text) or LOCATION_HINT.search(block)
        else:
            block = _text(page[pos:end])
            m = LOCATION_HINT.search(block)
            if not m:  # lieu souvent présent dans l'adresse de l'offre (/job/geneva/..., /job/Singapore-...)
                m = LOCATION_HINT.search(slug_text)
        prev_end = pos
        jobs.append(dict(href=href, title=title, location=m.group(1) if m else "", block=block[:400]))
    return jobs


GENERIC_LINK_TEXT = re.compile(
    r"(?i)(?:learn|read|find out|see|view|show)(?: more)?(?: details?)?|more(?: info(?:rmation)?| details)?|details?|"
    r"apply(?: now| here)?|view (?:job|role|position|opportunity|offer)|en savoir plus|voir (?:l[’'])?(?:offre|plus|le poste)|"
    r"postuler|candidater|d[ée]couvrir|plus d[’']infos?|mehr(?: erfahren)?|details anzeigen|>|→|»|\+")


def stable_job_key(href):
    """Identifiant stable d'une offre : certaines adresses contiennent un jeton de session qui change à chaque visite
    (tal.net : /xf-3615c5833f75/, ;jsessionid=...), ce qui ferait réapparaître la même offre à chaque passage."""
    m = re.search(r"\.tal\.net/.*?/opp/(\d+)", href)
    if m:
        return "%s:opp:%s" % (urllib.parse.urlparse(href).netloc, m.group(1))
    h = re.sub(r";jsessionid=[^/?#]*", "", href, flags=re.I)
    h = re.sub(r"/xf-[0-9a-f]{8,}(?=/)", "", h)
    u = urllib.parse.urlparse(h)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(u.query, keep_blank_values=True)
         if k.lower() not in ("sid", "session", "sessionid", "token", "utm_source", "utm_medium", "utm_campaign", "src",
                              "source", "ref", "codes")]
    return urllib.parse.urlunparse(u._replace(query=urllib.parse.urlencode(q), fragment=""))


def collect_html_site(s):
    """Page d'offres HTML. Options : link_regex (adresse des offres) ou text_regex (texte du lien),
    default_location (lieu supposé si le bloc n'en indique pas, pour les entreprises basées à Paris)."""
    out, errors = {}, []
    urls = list(s["urls"] if "urls" in s else [s["url"]])
    max_pages = int(s.get("max_pages", 12))
    done, extra = set(), 0
    while urls:
        u = urls.pop(0)
        if u in done:
            continue
        done.add(u)
        if not robots_allowed(u):
            errors.append("robots.txt interdit %s" % urllib.parse.urlparse(u).path)
            continue
        try:
            status, page = http(u, headers={"Accept": "text/html"})
        except SourceError as e:
            errors.append(str(e))
            continue
        if status != 200:
            errors.append("HTTP %d" % status)
            continue
        if s.get("link_regex"):
            found = parse_html_listing(page, u, s["link_regex"])
        else:
            trx = re.compile(s.get("text_regex", r"(?i)\b(stage|stagiaire|intern|internship|off.?cycle)\b"))
            found = [j for j in parse_html_listing(page, u, r".") if trx.search(j["title"])]
        n_before = len(out)
        for j in found:
            loc = j["location"] or s.get("default_location", "")
            key = stable_job_key(j["href"])
            out[key] = _job(s["company"], key, j["title"], loc, j["href"])
        # Pages suivantes de la même liste (SuccessFactors : startrow=, autres : page=), si la page a apporté du neuf
        if len(out) > n_before and extra < max_pages - 1 and s.get("paginate", True):
            for nxt in _next_pages(page, u):
                if nxt not in done and nxt not in urls and extra < max_pages - 1:
                    urls.append(nxt)
                    extra += 1
        _pause(0.5, 1.5)
    if not out:
        raise SourceError("aucune offre lisible (%s)" % ("; ".join(errors[:2]) or "page chargée en JavaScript ou modifiée"))
    return list(out.values())


def _next_pages(page, base):
    """Liens de pagination d'une page liste, sur la même adresse (paramètre startrow= ou page= qui augmente)."""
    b = urllib.parse.urlparse(base)
    cur = urllib.parse.parse_qs(b.query)
    out = []
    for href in re.findall(r'href="([^"]+)"', page):
        href = html.unescape(href)
        if "startrow=" not in href and not re.search(r"[?&](?:page|pg)=\d+", href):
            continue
        full = urllib.parse.urljoin(base, href)
        p = urllib.parse.urlparse(full)
        if p.netloc != b.netloc or p.path.rstrip("/") != b.path.rstrip("/"):
            continue
        q = urllib.parse.parse_qs(p.query)
        if any(q.get(k) != cur.get(k) for k in set(q) | set(cur) if k not in ("startrow", "page", "pg")):
            continue  # autre filtre ou autre tri : ce n'est pas la suite de cette liste
        for k in ("startrow", "page", "pg"):
            if k in q and int((q[k] or ["0"])[0] or 0) > int((cur.get(k) or ["0"])[0] or 0):
                out.append(full)
                break
    return list(dict.fromkeys(out))


# ---------------------------------------------------------------- SmartRecruiters (API publique des offres)
SR_COUNTRIES = {"ch": "Switzerland", "sg": "Singapore", "fr": "France"}


def parse_smartrecruiters(data, company_id, company_name):
    jobs = []
    for p in data.get("content", []) or []:
        pid = p.get("id")
        if not pid:
            continue
        loc = p.get("location") or {}
        country = SR_COUNTRIES.get(str(loc.get("country") or "").lower(), str(loc.get("country") or ""))
        place = ", ".join(x for x in [loc.get("city") or "", country] if x) or loc.get("fullLocation") or ""
        emp = " ".join(x for x in [(p.get("typeOfEmployment") or {}).get("label") or "",
                                   (p.get("experienceLevel") or {}).get("label") or ""] if x)
        j = _job(company_name, pid, p.get("name") or "", place,
                 "https://jobs.smartrecruiters.com/%s/%s" % (company_id, pid), p.get("releasedDate") or "")
        j["employment_type"] = emp
        jobs.append(j)
    return jobs


def collect_smartrecruiters_site(s):
    cid, out, offset = s["company_id"], {}, 0
    for _ in range(int(s.get("max_pages", 6))):
        status, txt = http("https://api.smartrecruiters.com/v1/companies/%s/postings?limit=100&offset=%d"
                           % (urllib.parse.quote(cid), offset), headers={"Accept": "application/json"})
        if status != 200:
            raise SourceError("HTTP %d" % status)
        data = json.loads(txt)
        for j in parse_smartrecruiters(data, cid, s["company"]):
            out[j["ext_id"]] = j
        offset += 100
        if offset >= int(data.get("totalFound") or 0):
            break
        _pause(0.3, 0.8)
    return list(out.values())


# ---------------------------------------------------------------- MyCareersFuture (portail public de Singapour)
MCF_INTERN = re.compile(r"(?i)(?<![a-z])(?:interns?|internships?|attachments?|trainees?)(?![a-z])")


def parse_mcf(data):
    items = data.get("results")
    if items is None:
        items = data.get("data") or []
    jobs = []
    for r in items:
        if not isinstance(r, dict):
            continue
        uid = r.get("uuid") or r.get("id")
        meta = r.get("metadata") or {}
        url = meta.get("jobDetailsUrl") or (("https://www.mycareersfuture.gov.sg/job/%s" % uid) if uid else "")
        if not uid or not url or not r.get("title"):
            continue
        comp = (r.get("hiringCompany") or {}).get("name") or (r.get("postedCompany") or {}).get("name") or ""
        addr = r.get("address") or {}
        dist = ((addr.get("districts") or [{}])[0] or {}).get("location") or ""
        place = "Singapore" + (", %s" % dist if dist else "")
        if addr.get("isOverseas"):
            place = "Overseas"
        emp = " ".join(str((e or {}).get("employmentType") or "") for e in (r.get("employmentTypes") or []))
        j = dict(source="MyCareersFuture", ext_id=str(uid), title=r["title"], company=comp, location=place,
                 url=url, apply_url=url, posted=norm_posted(meta.get("newPostingDate") or meta.get("originalPostingDate")),
                 employment_type=emp)
        jobs.append(j)
    return jobs


def collect_mcf(cfg, log):
    """Offres de stage (« Internship/Attachment ») du portail MyCareersFuture, par mots-clés."""
    m = cfg["mcf"]
    out, got_any, errors = {}, False, []
    for i, q in enumerate(m["queries"]):
        for page in range(int(m.get("max_pages", 2))):
            status, txt = http("https://api.mycareersfuture.gov.sg/v2/jobs?%s" % urllib.parse.urlencode(
                {"search": q, "limit": m.get("limit", 100), "page": page}), headers={"Accept": "application/json"})
            if status != 200:
                errors.append("« %s » : HTTP %d" % (q, status))
                break
            data = json.loads(txt)
            jobs = parse_mcf(data)
            if jobs:
                got_any = True
            elif int(data.get("total") or 0) > 0 and page == 0:
                raise SourceError("format de réponse inattendu (offres présentes mais illisibles)")
            for j in jobs:
                if MCF_INTERN.search(j["employment_type"]) or MCF_INTERN.search(j["title"]):
                    j["employment_type"] = j["employment_type"] or "Internship"
                    out[j["ext_id"]] = j
            if len(jobs) < int(m.get("limit", 100)):
                break
            _pause(0.3, 0.8)
        if i < len(m["queries"]) - 1:
            _pause(0.3, 0.8)
    if errors and not got_any:
        raise SourceError("; ".join(errors[:3]))
    if errors:
        log("MyCareersFuture : %d recherche(s) en erreur" % len(errors))
    return list(out.values())


# ---------------------------------------------------------------- Greenhouse et Lever (API publiques des offres)
def parse_greenhouse(data, company):
    jobs = []
    for p in data.get("jobs", []) or []:
        if not p.get("id") or not p.get("absolute_url"):
            continue
        j = _job(company, p["id"], p.get("title") or "", (p.get("location") or {}).get("name") or "",
                 p["absolute_url"], (p.get("first_published") or p.get("updated_at") or "")[:10])
        j["gh"] = "%s" % p["id"]
        jobs.append(j)
    return jobs


def collect_greenhouse_site(s):
    if s.get("eu"):
        # Boards hébergés en Europe : pas d'API publique, la page job-boards.eu.greenhouse.io est rendue côté serveur
        board = urllib.parse.quote(s["board"])
        return collect_html_site(dict(company=s["company"], url="https://job-boards.eu.greenhouse.io/%s" % board,
                                      link_regex=r"/%s/jobs/\d+" % re.escape(board)))
    status, txt = http("https://boards-api.greenhouse.io/v1/boards/%s/jobs" % urllib.parse.quote(s["board"]),
                       headers={"Accept": "application/json"})
    if status != 200:
        raise SourceError("HTTP %d" % status)
    return parse_greenhouse(json.loads(txt), s["company"])


def parse_lever(data, company):
    import datetime as _dt
    jobs = []
    for p in data if isinstance(data, list) else []:
        if not p.get("id") or not p.get("hostedUrl"):
            continue
        cat = p.get("categories") or {}
        locs = [cat.get("location") or ""] + list(cat.get("allLocations") or [])
        ts = p.get("createdAt")
        posted = _dt.datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d") if isinstance(ts, (int, float)) else ""
        j = _job(company, p["id"], p.get("text") or "", ", ".join(dict.fromkeys(l for l in locs if l)),
                 p["hostedUrl"], posted)
        j["employment_type"] = cat.get("commitment") or ""
        jobs.append(j)
    return jobs


def collect_lever_site(s):
    status, txt = http("https://api.lever.co/v0/postings/%s?mode=json" % urllib.parse.quote(s["account"]),
                       headers={"Accept": "application/json"})
    if status != 200:
        raise SourceError("HTTP %d" % status)
    return parse_lever(json.loads(txt), s["company"])


# ---------------------------------------------------------------- Ashby (API publique des offres, très utilisée par les fonds)
def parse_ashby(data, company):
    jobs = []
    for p in (data or {}).get("jobs", []) or []:
        if not p.get("id") or not (p.get("jobUrl") or p.get("applyUrl")) or p.get("isListed") is False:
            continue
        locs = [p.get("location") or ""] + [(x.get("location") or "") for x in (p.get("secondaryLocations") or [])
                                            if isinstance(x, dict)]
        j = _job(company, p["id"], p.get("title") or "", ", ".join(dict.fromkeys(l for l in locs if l)),
                 p.get("jobUrl") or p.get("applyUrl"), (p.get("publishedAt") or "")[:10])
        j["employment_type"] = p.get("employmentType") or ""
        jobs.append(j)
    return jobs


def collect_ashby_site(s):
    status, txt = http("https://api.ashbyhq.com/posting-api/job-board/%s" % urllib.parse.quote(s["board"]),
                       headers={"Accept": "application/json"})
    if status != 200:
        raise SourceError("HTTP %d" % status)
    return parse_ashby(json.loads(txt), s["company"])


# ---------------------------------------------------------------- Workable (widget public des offres)
def parse_workable(data, company):
    jobs = []
    for p in (data or {}).get("jobs", []) or []:
        url = p.get("url") or p.get("shortlink") or ""
        key = p.get("shortcode") or p.get("id") or url
        if not url or not key:
            continue
        loc = ", ".join(x for x in [p.get("city") or "", p.get("state") or "", p.get("country") or ""] if x)
        locs = [", ".join(x for x in [(l or {}).get("city") or "", (l or {}).get("country") or ""] if x)
                for l in (p.get("locations") or []) if isinstance(l, dict)]
        loc = "; ".join(dict.fromkeys([loc] + locs if loc else locs))
        j = _job(company, key, p.get("title") or "", loc, url, p.get("published_on") or p.get("created_at") or "")
        j["employment_type"] = p.get("employment_type") or ""
        jobs.append(j)
    return jobs


def collect_workable_site(s):
    status, txt = http("https://apply.workable.com/api/v1/widget/accounts/%s" % urllib.parse.quote(s["account"]),
                       headers={"Accept": "application/json"})
    if status != 200:
        raise SourceError("HTTP %d" % status)
    return parse_workable(json.loads(txt), s["company"])


# =====================================================================
# API officielles d'agrégateurs d'offres (The Muse, Adzuna, Reed)
# =====================================================================
MUSE_LOCATIONS = ["London, United Kingdom", "Paris, France", "Zurich, Switzerland", "Geneva, Switzerland",
                  "Singapore, Singapore", "Dublin, Ireland"]


def parse_muse(data):
    jobs = []
    for r in (data or {}).get("results", []) or []:
        url = ((r.get("refs") or {}).get("landing_page") or "")
        if not r.get("id") or not url:
            continue
        locs = "; ".join(l.get("name") or "" for l in (r.get("locations") or []) if isinstance(l, dict))
        levels = " ".join(l.get("name") or "" for l in (r.get("levels") or []) if isinstance(l, dict))
        jobs.append(dict(source="The Muse", ext_id=str(r["id"]), title=r.get("name") or "",
                         company=(r.get("company") or {}).get("name") or "", location=locs, url=url, apply_url=url,
                         posted=norm_posted(r.get("publication_date") or ""), employment_type=levels))
    return jobs


def collect_muse(cfg, log):
    """The Muse : API publique, filtre « Internship » par ville (clé facultative MUSE_API_KEY)."""
    m = cfg.get("muse") or {}
    key = os.environ.get("MUSE_API_KEY", "")
    out, errors = {}, []
    for loc in m.get("locations", MUSE_LOCATIONS):
        for page in range(int(m.get("max_pages", 15))):
            params = [("page", page), ("level", "Internship"), ("location", loc)]
            if key:
                params.append(("api_key", key))
            status, txt = http("https://www.themuse.com/api/public/jobs?" + urllib.parse.urlencode(params),
                               headers={"Accept": "application/json"})
            if status != 200:
                errors.append("%s : HTTP %d" % (loc, status))
                break
            data = json.loads(txt)
            for j in parse_muse(data):
                out[j["ext_id"]] = j
            if page + 1 >= int(data.get("page_count") or 0):
                break
            _pause(0.3, 0.8)
    if errors and not out:
        raise SourceError("; ".join(errors[:3]))
    return list(out.values()), errors


ADZUNA_PLAN = [  # (pays, lieu, pages) : 12 appels par passage, un passage toutes les 4 h (quota gratuit 2 500/mois)
    ("gb", "London", 5), ("fr", "Ile-de-France", 3), ("ch", "", 2), ("sg", "", 2)]


def parse_adzuna(data, country):
    jobs = []
    for r in (data or {}).get("results", []) or []:
        if not r.get("id") or not r.get("redirect_url"):
            continue
        loc = (r.get("location") or {}).get("display_name") or ""
        area = [x for x in ((r.get("location") or {}).get("area") or []) if x]
        # "Central" seul ne dit rien : on ajoute la hiérarchie Adzuna (pays, région, ville) pour situer l'offre
        extra = ", ".join(reversed([x for x in area if x.lower() not in loc.lower()]))
        loc = ", ".join(x for x in [loc, extra] if x)
        jobs.append(dict(source="Adzuna", ext_id="%s:%s" % (country, r["id"]), title=_text(r.get("title") or ""),
                         company=(r.get("company") or {}).get("display_name") or "", location=loc,
                         url=r["redirect_url"], apply_url=r["redirect_url"], posted=norm_posted(r.get("created") or ""),
                         employment_type=" ".join(x for x in [r.get("contract_type") or "", r.get("contract_time") or ""] if x)))
    return jobs


def collect_adzuna(cfg, log):
    """Adzuna : API officielle (clés ADZUNA_APP_ID / ADZUNA_APP_KEY). Stages récents, triés par date."""
    app_id, app_key = os.environ.get("ADZUNA_APP_ID", ""), os.environ.get("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        raise SourceError("clés Adzuna absentes (secrets ADZUNA_APP_ID et ADZUNA_APP_KEY)")
    a = cfg.get("adzuna") or {}
    out, errors = {}, []
    for country, where, pages in a.get("plan", ADZUNA_PLAN):
        for page in range(1, int(pages) + 1):
            params = {"app_id": app_id, "app_key": app_key, "results_per_page": 50, "sort_by": "date",
                      "max_days_old": a.get("max_days_old", 3),
                      "what_or": a.get("what_or", "intern internship internships stage stagiaire praktikum placement "
                                                  "off-cycle summer")}
            if where:
                params["where"] = where
            status, txt = http("https://api.adzuna.com/v1/api/jobs/%s/search/%d?%s"
                               % (country, page, urllib.parse.urlencode(params)), headers={"Accept": "application/json"})
            if status != 200:
                errors.append("%s : HTTP %d" % (country, status))
                break
            data = json.loads(txt)
            jobs = parse_adzuna(data, country)
            for j in jobs:
                out[j["ext_id"]] = j
            if len(jobs) < 50:
                break
            _pause(2.5, 3.5)  # 25 appels par minute au plus
    if errors and not out:
        raise SourceError("; ".join(errors[:3]))
    return list(out.values()), errors


def parse_reed(data):
    jobs = []
    for r in (data or {}).get("results", []) or []:
        jid = r.get("jobId") or r.get("id")
        url = r.get("jobUrl") or (("https://www.reed.co.uk/jobs/%s" % jid) if jid else "")
        if not jid or not r.get("jobTitle"):
            continue
        posted = r.get("date") or ""
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", posted)
        if m:
            posted = "%s-%s-%s" % (m.group(3), m.group(2), m.group(1))
        jobs.append(dict(source="Reed", ext_id=str(jid), title=r.get("jobTitle") or "", company=r.get("employerName") or "",
                         location=(r.get("locationName") or "") + ", United Kingdom", url=url, apply_url=url,
                         posted=norm_posted(posted), employment_type=""))
    return jobs


def collect_reed(cfg, log):
    """Reed.co.uk : API officielle (clé REED_API_KEY), stages à Londres."""
    key = os.environ.get("REED_API_KEY", "")
    if not key:
        raise SourceError("clé Reed absente (secret REED_API_KEY)")
    r = cfg.get("reed") or {}
    auth = "Basic " + base64.b64encode((key + ":").encode()).decode()
    out = {}
    for kw in r.get("keywords", ["internship", "intern", "summer internship", "placement"]):
        for page in range(int(r.get("max_pages", 2))):
            params = {"keywords": kw, "locationName": "London", "distanceFromLocation": 15, "resultsToTake": 100,
                      "resultsToSkip": page * 100}
            status, txt = http("https://www.reed.co.uk/api/1.0/search?" + urllib.parse.urlencode(params),
                               headers={"Accept": "application/json", "Authorization": auth})
            if status != 200:
                raise SourceError("HTTP %d" % status)
            data = json.loads(txt)
            jobs = parse_reed(data)
            if not jobs and int(data.get("totalResults") or 0) > 0 and page == 0:
                raise SourceError("format de réponse inattendu")
            for j in jobs:
                out[j["ext_id"]] = j
            if len(jobs) < 100:
                break
            _pause(0.5, 1.0)
    return list(out.values())


SITE_COLLECTORS = {
    "workday": collect_workday_site,
    "oracle": collect_oracle_site,
    "eightfold": collect_eightfold_site,
    "html": collect_html_site,
    "smartrecruiters": collect_smartrecruiters_site,
    "greenhouse": collect_greenhouse_site,
    "lever": collect_lever_site,
    "workable": collect_workable_site,
    "ashby": collect_ashby_site,
}


# =====================================================================
# Description d'une offre (langue exigée, confirmation du stage)
# =====================================================================
def _html_text(fragment):
    return _text(re.sub(r"<(script|style)\b.*?</\1>", " ", fragment or "", flags=re.S | re.I))


def _jsonld_job(page):
    """Bloc schema.org JobPosting d'une page (description + type de contrat), s'il existe."""
    for raw in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S | re.I):
        try:
            data = json.loads(html.unescape(raw.strip()))
        except ValueError:
            try:
                data = json.loads(raw.strip())
            except ValueError:
                continue
        items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for it in items:
            if isinstance(it, dict) and "JobPosting" in str(it.get("@type")):
                et = it.get("employmentType") or ""
                if isinstance(et, list):
                    et = " ".join(str(x) for x in et)
                return dict(description=_html_text(html.unescape(str(it.get("description") or ""))),
                            employment_type=str(et).replace("_", " "), location=_jsonld_location(it.get("jobLocation")))
    return None


def _jsonld_location(loc):
    """Lieu(x) d'un bloc schema.org jobLocation : "Ville, Région, Pays"."""
    out = []
    for l in loc if isinstance(loc, list) else [loc]:
        if isinstance(l, dict):
            a = l.get("address") or {}
            if isinstance(a, str):
                out.append(a)
            elif isinstance(a, dict):
                c = a.get("addressCountry")
                c = c.get("name") if isinstance(c, dict) else c
                out.append(", ".join(str(x) for x in (a.get("addressLocality"), a.get("addressRegion"), c) if x))
        elif isinstance(l, str):
            out.append(l)
    return "; ".join(x for x in out if x)


LOCATION_HTML = re.compile(r'class="[^"]*(?:jobGeoLocation|job-?location|jobLocation|location)[^"]*"[^>]*>\s*([^<]{2,100}?)\s*<', re.I)


def fetch_location(offer):
    """Lieu d'une offre de site carrière dont la page liste n'indique pas le lieu (JSON-LD, sinon balise "location")."""
    url = offer.get("url") or ""
    if not url.startswith("http") or not robots_allowed(url):
        return ""
    status, page = http(url, headers={"Accept": "text/html"})
    if status != 200:
        return ""
    d = _jsonld_job(page)
    if d and d.get("location"):
        return d["location"]
    m = LOCATION_HTML.search(page)
    return html.unescape(m.group(1)).strip() if m else ""


def fetch_description(offer):
    """Texte de l'offre et type de contrat. Renvoie dict(description, employment_type, trusted) ou None.

    trusted = le type de contrat vient de l'employeur et peut servir à écarter une offre (LinkedIn, MyCareersFuture).
    Lève RateLimited ; renvoie None si la page n'est pas lisible automatiquement."""
    url = offer.get("url") or ""
    src = offer.get("source") or ""
    try:
        if src == "LinkedIn" or "linkedin.com/jobs/view/" in url:
            jid = offer.get("ext_id") or _first(r"/jobs/view/(\d+)", url)
            d = linkedin_detail(jid)
            return dict(description=d["description"], employment_type=d["employment_type"], trusted=True)
        if src == "MyCareersFuture":
            status, txt = http("https://api.mycareersfuture.gov.sg/v2/jobs/%s" % offer.get("ext_id"),
                               headers={"Accept": "application/json"})
            if status != 200:
                return None
            d = json.loads(txt)
            emp = " ".join(str((e or {}).get("employmentType") or "") for e in (d.get("employmentTypes") or []))
            return dict(description=_html_text(d.get("description") or ""), employment_type=emp, trusted=True)
        m = re.match(r"https://([^/]+\.myworkdayjobs\.com)/(?:[a-z]{2}-[A-Z]{2}/)?([^/]+)(/job/.+)$", url)
        if m:
            host, site, path = m.groups()
            status, txt = http("https://%s/wday/cxs/%s/%s%s" % (host, host.split(".")[0], site, path),
                               headers={"Accept": "application/json"})
            if status != 200:
                return None
            info = json.loads(txt).get("jobPostingInfo") or {}
            return dict(description=_html_text(info.get("jobDescription") or ""), employment_type="", trusted=False)
        if "smartrecruiters.com" in url:
            return None  # l'API SmartRecruiters est interdite aux robots (robots.txt) : pas de lecture
        m = re.match(r"https://(?:boards|job-boards)\.greenhouse\.io/([^/]+)/jobs/(\d+)", url)
        if m:
            status, txt = http("https://boards-api.greenhouse.io/v1/boards/%s/jobs/%s" % m.groups(),
                               headers={"Accept": "application/json"})
            if status != 200:
                return None
            return dict(description=_html_text(html.unescape(json.loads(txt).get("content") or "")),
                        employment_type="", trusted=False)
        m = re.match(r"https://jobs\.lever\.co/([^/]+)/([0-9a-f-]{20,})", url)
        if m:
            status, txt = http("https://api.lever.co/v0/postings/%s/%s" % m.groups(), headers={"Accept": "application/json"})
            if status != 200:
                return None
            d = json.loads(txt)
            text = (d.get("descriptionPlain") or "") + " \n " + " \n ".join(
                "%s: %s" % (x.get("text") or "", _html_text(x.get("content") or "")) for x in (d.get("lists") or []))
            return dict(description=text, employment_type=(d.get("categories") or {}).get("commitment") or "",
                        trusted=False)
        m = re.match(r"https://jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-f-]{20,})", url)
        if m:
            status, txt = http("https://api.ashbyhq.com/posting-api/job-board/%s" % m.group(1),
                               headers={"Accept": "application/json"})
            if status != 200:
                return None
            for p in json.loads(txt).get("jobs") or []:
                if p.get("id") == m.group(2):
                    return dict(description=p.get("descriptionPlain") or _html_text(p.get("descriptionHtml") or ""),
                                employment_type=p.get("employmentType") or "", trusted=False)
            return None
        m = re.match(r"https://([^/]+)/hcmUI/CandidateExperience/[a-z]{2}/sites/([^/]+)/job/(\d+)", url)
        if m:
            host, site, rid = m.groups()
            site_number = _oracle_site_numbers.get(host) or site
            finder = 'ById;Id="%s",siteNumber=%s' % (rid, site_number)
            status, txt = http("https://%s/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?expand=all"
                               "&onlyData=true&finder=%s" % (host, urllib.parse.quote(finder, safe=";=,")),
                               headers={"Accept": "application/json"})
            if status != 200:
                return None
            items = json.loads(txt).get("items") or []
            if not items:
                return None
            it = items[0]
            text = " \n ".join(_html_text(it.get(k) or "") for k in (
                "ExternalDescriptionStr", "ExternalResponsibilitiesStr", "ExternalQualificationsStr",
                "CorporateDescriptionStr"))
            return dict(description=text, employment_type="", trusted=False)
        if not url.startswith("http"):
            return None
        status, page = http(url, headers={"Accept": "text/html"})
        if status != 200:
            return None
        d = _jsonld_job(page)  # description structurée seulement : le reste de la page n'est pas fiable
        if not d or len(d["description"]) < 80:
            return None
        d["trusted"] = False
        return d
    except RateLimited:
        raise
    except Exception:  # noqa: BLE001  page illisible : on n'écarte rien sur cette base
        return None


# =====================================================================
# Offres fermées : vérification ponctuelle de chaque offre
# =====================================================================
CLOSED_MARKERS = re.compile(
    r"no longer accepting applications|n[’']accepte plus de candidatures|candidatures (?:sont )?(?:closes|clôturées|fermées)"
    r"|this job is no longer available|job (?:posting )?(?:has )?expired|offre (?:n[’']est plus|plus) disponible"
    r"|cette offre (?:a expiré|est expirée|n[’']est plus en ligne)|position (?:has been )?filled"
    r"|this position is no longer|the job you are looking for is no longer", re.I)


def check_open(offer):
    """True = toujours ouverte, False = fermée, None = impossible à savoir (on réessaiera)."""
    url = offer.get("url") or ""
    try:
        if offer.get("source") == "LinkedIn" or "linkedin.com/jobs/view/" in url:
            jid = offer.get("ext_id") or _first(r"/jobs/view/(\d+)", url)
            status, page = http(LI_DETAIL % jid, headers={"Accept": "text/html"})
            if status in (404, 410):
                return False
            if status != 200:
                return None
            if re.search(r'class="[^"]*closed-job', page) or CLOSED_MARKERS.search(page[:300000]):
                return False
            return True
        m = re.match(r"https://([^/]+\.myworkdayjobs\.com)/([^/]+)(/job/.+)$", url)
        if m:
            host, site, path = m.groups()
            status, txt = http("https://%s/wday/cxs/%s/%s%s" % (host, host.split(".")[0], site, path),
                               headers={"Accept": "application/json"})
            if status in (404, 410):
                return False
            if status != 200:
                return None
            try:
                return bool(json.loads(txt).get("jobPostingInfo"))
            except ValueError:
                return None
        if "/hcmUI/CandidateExperience/" in url:
            return None  # pages construites en JavaScript : pas de vérification fiable
        status, page = http(url, headers={"Accept": "text/html"})
        if status in (404, 410):
            return False
        if status != 200:
            return None
        return not CLOSED_MARKERS.search(page[:300000])
    except RateLimited:
        raise
    except Exception:
        return None
