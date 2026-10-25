"""Sondage ponctuel : syntaxe des mots-clés de la recherche LinkedIn (invité) à Londres."""
import json, time, sources, filters
LOC = "London, England, United Kingdom"
V = [
 ("corporate M&A intern", None), ('"corporate M&A" AND (intern OR internship OR placement)', None),
 ('"M&A" AND (intern OR internship)', None), ("M&A", "I"), ('"M&A"', "I"),
 ("investment banking", "I"), ('"investment banking"', "I"),
 ("broker", "I"), ('broking OR broker', "I"),
 ("corporate finance", "I"), ('"corporate finance"', "I"),
 ("finance", "I"), ("", "I"),
]
out = []
for q, jt in V:
    try:
        res = sources.linkedin_search(q, LOC, 2592000, start=0, job_type=jt)
        titles = [j["title"] for j in res]
        ok = sum(1 for j in res if filters.classify(j["title"], j["location"], "", "", company=j.get("company") or "")["ok"])
        out.append(dict(q=q, jt=jt, n=len(res), in_scope=ok, titles=titles[:12]))
    except Exception as e:
        out.append(dict(q=q, jt=jt, error=str(e)))
    time.sleep(3)
json.dump(out, open("li_results.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:3000])
