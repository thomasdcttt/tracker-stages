"""Sondage ponctuel : date de publication lue sur la page des offres sans date."""
import json, time, collections, urllib.parse, sources
items = json.load(open("nodate.json"))
out, ok = [], collections.Counter()
for it in items:
    host = urllib.parse.urlparse(it["url"]).netloc
    try:
        d = sources.fetch_posted(it)
        err = ""
    except Exception as e:
        d, err = "", str(e)[:120]
    ok[(host, bool(d))] += 1
    out.append(dict(it, date=d, err=err))
    time.sleep(0.8)
json.dump(dict(results=out, summary={"%s|%s" % k: v for k, v in ok.items()}), open("li_results.json", "w"), ensure_ascii=False, indent=1)
print(ok)
