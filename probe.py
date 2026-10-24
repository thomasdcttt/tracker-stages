"""Sondage ponctuel : quels employeurs finance publient leurs offres sur une API publique d'ATS (Greenhouse, Lever,
Ashby, Workable) et combien de stages ont-ils dans les zones suivies. Lecture seule, API publiques prévues pour ça."""
import json, re, sys, unicodedata, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ZONES = re.compile(r"london|paris|geneva|gen[eè]ve|zurich|z[uü]rich|zug|lausanne|lugano|singapore|dublin|ireland|switzerland|united kingdom|\buk\b|france", re.I)
INTERN = re.compile(r"intern|stage|stagiaire|placement|summer|off.?cycle|praktik|graduate|analyst program", re.I)

def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return s

def slugs(name):
    n = norm(name).replace("&", "and")
    words = re.findall(r"[a-z0-9]+", n)
    out = ["".join(words), "-".join(words)]
    core = [w for w in words if w not in ("partners", "capital", "management", "group", "asset", "investment", "investments", "and", "co", "the", "international", "securities")]
    if core:
        out += ["".join(core), "-".join(core)]
    out.append(words[0])
    return list(dict.fromkeys(x for x in out if len(x) >= 3))

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 tracker-stages probe", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, str(e)

def jobs_of(kind, slug):
    if kind == "greenhouse" or kind == "greenhouse_eu":
        host = "boards-api.eu.greenhouse.io" if kind == "greenhouse_eu" else "boards-api.greenhouse.io"
        st, t = get("https://%s/v1/boards/%s/jobs" % (host, slug))
        if st != 200: return None
        d = json.loads(t); st2, t2 = get("https://%s/v1/boards/%s" % (host, slug))
        name = json.loads(t2).get("name") if st2 == 200 else ""
        return name, [(j.get("title") or "", (j.get("location") or {}).get("name") or "") for j in d.get("jobs", [])]
    if kind == "lever":
        st, t = get("https://api.lever.co/v0/postings/%s?mode=json" % slug)
        if st != 200: return None
        d = json.loads(t)
        if not isinstance(d, list): return None
        return slug, [(j.get("text") or "", ", ".join([(j.get("categories") or {}).get("location") or ""] + list((j.get("categories") or {}).get("allLocations") or []))) for j in d]
    if kind == "ashby":
        st, t = get("https://api.ashbyhq.com/posting-api/job-board/%s" % slug)
        if st != 200: return None
        d = json.loads(t)
        return slug, [(j.get("title") or "", ", ".join([j.get("location") or ""] + [(x.get("location") or "") for x in j.get("secondaryLocations") or []])) for j in d.get("jobs", [])]
    if kind == "workable":
        st, t = get("https://apply.workable.com/api/v1/widget/accounts/%s" % slug)
        if st != 200: return None
        d = json.loads(t)
        return d.get("name") or slug, [(j.get("title") or "", ", ".join(x for x in [j.get("city") or "", j.get("country") or ""] if x)) for j in d.get("jobs", [])]

def probe(firm):
    res = []
    for kind in ("greenhouse", "greenhouse_eu", "lever", "ashby", "workable"):
        for s in slugs(firm):
            try:
                r = jobs_of(kind, s)
            except Exception:
                r = None
            if r is None:
                continue
            name, jobs = r
            zone = [j for j in jobs if ZONES.search(j[1])]
            res.append(dict(firm=firm, kind=kind, slug=s, board_name=name, total=len(jobs), in_zones=len(zone),
                            interns_in_zones=[j for j in zone if INTERN.search(j[0])][:15], sample=[j for j in jobs[:4]]))
            break
    return res

if __name__ == "__main__":
    firms = [l.strip() for l in open("firms.txt") if l.strip()]
    out = []
    with ThreadPoolExecutor(12) as ex:
        for r in ex.map(probe, firms):
            out.extend(r)
    json.dump(out, open("probe_results.json", "w"), ensure_ascii=False, indent=1)
    print(len(out), "boards trouvés")
