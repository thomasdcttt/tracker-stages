"""Sondage ponctuel : syntaxe des mots-clés de la recherche LinkedIn (invité) à Londres."""
import json, time, sources, filters
LOC = "London, England, United Kingdom"
V = [
 ('(intern OR internship OR placement OR "summer analyst" OR "off-cycle" OR "off cycle")', None),
 ('intern OR internship OR placement OR "summer analyst" OR "off-cycle"', None),
 ('internship', None), ('intern', None), ('"summer analyst"', None), ('"summer internship"', None),
 ('"off-cycle"', None), ('placement', None),
 ('"M&A" AND (intern OR internship OR placement OR "summer analyst" OR "off-cycle" OR "off cycle")', None),
 ('"finance" AND (intern OR internship OR placement OR "summer analyst" OR "off-cycle" OR "off cycle")', None),
]
out = []
for q, jt in V:
    try:
        res = sources.linkedin_search(q, LOC, 21600 if not q.startswith('"') or "AND" not in q else 2592000, start=0, job_type=jt)
        titles = [j["title"] for j in res]
        ok = sum(1 for j in res if filters.classify(j["title"], j["location"], "", "", company=j.get("company") or "")["ok"])
        out.append(dict(q=q, jt=jt, n=len(res), in_scope=ok, titles=titles[:12]))
    except Exception as e:
        out.append(dict(q=q, jt=jt, error=str(e)))
    time.sleep(3)
json.dump(out, open("li_results.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:3000])
