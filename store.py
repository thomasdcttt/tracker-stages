"""Stockage SQLite : offres retenues, offres écartées, état des sources."""
import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS offers (
    uid TEXT PRIMARY KEY, source TEXT, ext_id TEXT, title TEXT, company TEXT, location TEXT,
    url TEXT, apply_url TEXT, posted TEXT, category TEXT, summer INTEGER DEFAULT 0,
    first_seen REAL, notified INTEGER DEFAULT 0, dedup_key TEXT, duplicate_of TEXT
);
CREATE INDEX IF NOT EXISTS offers_dedup ON offers(dedup_key);
CREATE TABLE IF NOT EXISTS rejected (uid TEXT PRIMARY KEY, reason TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS seedset (uid TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS source_status (
    name TEXT PRIMARY KEY, ok INTEGER, message TEXT, last_run REAL, last_ok REAL, found INTEGER
);
"""


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        # Colonnes ajoutées après coup (bases existantes mises à niveau sans perte)
        cols = {r["name"] for r in self.db.execute("PRAGMA table_info(offers)")}
        for col, decl in (("closed", "INTEGER DEFAULT 0"), ("closed_at", "REAL"), ("last_checked", "REAL")):
            if col not in cols:
                self.db.execute("ALTER TABLE offers ADD COLUMN %s %s" % (col, decl))
        rcols = {r["name"] for r in self.db.execute("PRAGMA table_info(rejected)")}
        for col in ("title", "company", "location", "source", "url"):
            if col not in rcols:
                self.db.execute("ALTER TABLE rejected ADD COLUMN %s TEXT" % col)
        self.db.commit()

    # --- méta ---
    def get_meta(self, key, default=None):
        r = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default

    def set_meta(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", (key, str(value)))
        self.db.commit()

    # --- offres ---
    def known(self, uid):
        return self.db.execute("SELECT 1 FROM offers WHERE uid=? UNION SELECT 1 FROM rejected WHERE uid=?",
                               (uid, uid)).fetchone() is not None

    def is_offer(self, uid):
        return self.db.execute("SELECT 1 FROM offers WHERE uid=?", (uid,)).fetchone() is not None

    def find_duplicate(self, dedup_key):
        r = self.db.execute("SELECT uid FROM offers WHERE dedup_key=? AND duplicate_of IS NULL LIMIT 1",
                            (dedup_key,)).fetchone()
        return r["uid"] if r else None

    def add_offer(self, o, notified, duplicate_of=None):
        self.db.execute(
            "INSERT OR IGNORE INTO offers(uid, source, ext_id, title, company, location, url, apply_url, posted,"
            " category, summer, first_seen, notified, dedup_key, duplicate_of)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (o["uid"], o["source"], o["ext_id"], o["title"], o.get("company") or "", o.get("location") or "",
             o["url"], o.get("apply_url"), o.get("posted") or "", o["category"], int(bool(o.get("summer"))),
             time.time(), int(notified), o["dedup_key"], duplicate_of))
        self.db.commit()

    def add_rejected(self, uid, reason, job=None):
        j = job or {}
        self.db.execute("INSERT OR REPLACE INTO rejected(uid, reason, ts, title, company, location, source, url)"
                        " VALUES(?,?,?,?,?,?,?,?)",
                        (uid, reason, time.time(), j.get("title"), j.get("company"), j.get("location"),
                         j.get("source"), j.get("url")))
        self.db.commit()

    def purge_rejected(self):
        n = self.db.execute("SELECT COUNT(*) FROM rejected").fetchone()[0]
        self.db.execute("DELETE FROM rejected")
        self.db.commit()
        return n

    def recent_rejected(self, since, limit=300, skip_reasons=("hors Paris", "publiée il y a trop longtemps")):
        q = ("SELECT uid, reason, ts, title, company, location, source, url FROM rejected WHERE ts >= ? "
             "AND title IS NOT NULL AND reason NOT IN (%s) ORDER BY ts DESC LIMIT ?" % ",".join("?" * len(skip_reasons)))
        return [dict(r) for r in self.db.execute(q, (since,) + tuple(skip_reasons) + (limit,))]

    def mark_seed(self, uid):
        self.db.execute("INSERT OR IGNORE INTO seedset(uid) VALUES(?)", (uid,))
        self.db.commit()

    def in_seed(self, uid):
        return self.db.execute("SELECT 1 FROM seedset WHERE uid=?", (uid,)).fetchone() is not None

    def prune(self, days=45):
        self.db.execute("DELETE FROM rejected WHERE ts < ?", (time.time() - days * 86400,))
        self.db.commit()

    def offers_to_check(self, limit, min_age_hours=20):
        """Offres ouvertes à revérifier (jamais vérifiées d'abord, puis les plus anciennes)."""
        cutoff = time.time() - min_age_hours * 3600
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM offers WHERE duplicate_of IS NULL AND COALESCE(closed,0)=0 "
            "AND COALESCE(last_checked, first_seen) < ? ORDER BY COALESCE(last_checked, 0) LIMIT ?",
            (cutoff, limit))]

    def set_checked(self, uid, closed):
        if closed:
            self.db.execute("UPDATE offers SET last_checked=?, closed=1, closed_at=? WHERE uid=?",
                            (time.time(), time.time(), uid))
        else:
            self.db.execute("UPDATE offers SET last_checked=? WHERE uid=?", (time.time(), uid))
        self.db.commit()

    def recent_notified(self, since):
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM offers WHERE duplicate_of IS NULL AND notified=1 AND first_seen>=? "
            "ORDER BY first_seen DESC", (since,))]

    def offers(self):
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM offers WHERE duplicate_of IS NULL ORDER BY first_seen DESC")]

    def other_links(self, uid):
        return [dict(r) for r in self.db.execute(
            "SELECT source, url, apply_url FROM offers WHERE duplicate_of=?", (uid,))]

    # --- sources ---
    def set_source(self, name, ok, message, found=0):
        now = time.time()
        prev = self.db.execute("SELECT last_ok FROM source_status WHERE name=?", (name,)).fetchone()
        last_ok = now if ok else (prev["last_ok"] if prev else None)
        self.db.execute("INSERT OR REPLACE INTO source_status(name, ok, message, last_run, last_ok, found)"
                        " VALUES(?,?,?,?,?,?)", (name, int(ok), message, now, last_ok, found))
        self.db.commit()

    def sources(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM source_status ORDER BY name")]
