#!/usr/bin/env python3
"""Export aggregate profile measures from a Korpus SQLite database into data/profile.json.

Standard library only. Read-only. One consistent read transaction. No network.

What is written (strict whitelist, nothing else):
  corpus            human-origin entry count, word count, indexed days, first/last day
  sources           per-source entries and words for the whitelisted source names only
  writing_days      per-day human entries and words
  workspace_git     indexed non-merge commits and repository count, excluding the profile repo
  commit_days       per-day commit counts
  provider_snapshots  known public fields preserved from the existing output file

Never written: prompt ids or text, titles, project names, authors, subjects, file paths.

Usage:
  python3 scripts/export_corpus.py --db /path/to/corpus.sqlite                 # dry run, prints JSON
  python3 scripts/export_corpus.py --db /path/to/corpus.sqlite --as-of 2026-10-13 --through 2026-10-12 --write

--as-of     snapshot date (default: today in Europe/Bratislava). Range upper bound.
--through   last corpus day to include (default: same as --as-of). Use the previous
            day when the as-of day is still in progress.
--write     actually replace data/profile.json; without it nothing on disk changes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "profile.json"
TIMEZONE = "Europe/Bratislava"
SOURCE_WHITELIST = ("codex", "claude", "chatgpt", "dia", "obsidian")
PROFILE_REPO_PATTERN = "%xvadur-profile%"
SCHEMA_VERSION = 1
DATE_RE = r"^\d{4}-\d{2}-\d{2}$"
PROVIDER_FIELDS = {"provider", "reported_tokens", "display", "scope", "evidence", "received_on",
                   "sessions", "messages", "active_days"}


def parse_date(s: str) -> dt.date:
    try:
        return dt.date.fromisoformat(s)
    except ValueError as e:
        raise SystemExit(f"invalid date {s!r}: {e}")


def q(conn: sqlite3.Connection, sql: str, *params):
    return conn.execute(sql, params).fetchall()


def export(db: Path, as_of: dt.date, through: dt.date, previous: dict | None) -> dict:
    if not db.is_file():
        raise SystemExit(f"database not found: {db}")
    uri = db.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, isolation_level=None)
    conn.execute("PRAGMA query_only = 1")
    conn.execute("BEGIN")  # single read transaction: every query sees the same snapshot
    try:
        src_marks = ",".join("?" * len(SOURCE_WHITELIST))
        human = f"origin = 'human' AND source IN ({src_marks}) AND day <= ?"
        hp = (*SOURCE_WHITELIST, through.isoformat())

        (entries, words, days, first_day, last_day), = q(
            conn, f"SELECT COUNT(*), COALESCE(SUM(words),0), COUNT(DISTINCT day), MIN(day), MAX(day) FROM prompts WHERE {human}", *hp)
        sources = q(conn, f"SELECT source, COUNT(*), COALESCE(SUM(words),0) FROM prompts WHERE {human} GROUP BY source ORDER BY SUM(words) DESC, source", *hp)
        writing_days = q(conn, f"SELECT day, COUNT(*), COALESCE(SUM(words),0) FROM prompts WHERE {human} GROUP BY day ORDER BY day", *hp)

        git_where = "repo NOT LIKE ? AND day <= ?"
        gp = (PROFILE_REPO_PATTERN, through.isoformat())
        (commits, repos, g_first, g_last), = q(
            conn, f"SELECT COUNT(*), COUNT(DISTINCT repo), MIN(day), MAX(day) FROM git_commits WHERE {git_where}", *gp)
        commit_days = q(conn, f"SELECT day, COUNT(*) FROM git_commits WHERE {git_where} GROUP BY day ORDER BY day", *gp)
        last_ingest = q(conn, "SELECT value FROM meta WHERE key = 'last_ingest'")
    finally:
        conn.execute("COMMIT")
        conn.close()

    out = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "as_of": as_of.isoformat(),
        "timezone": TIMEZONE,
        "corpus_last_ingest": last_ingest[0][0] if last_ingest else None,
        "corpus": {"entries": entries, "words": words, "active_days": days, "first_day": first_day, "last_day": last_day},
        "sources": [{"source": s, "entries": e, "words": w} for s, e, w in sources],
        "writing_days": [{"day": d, "entries": e, "words": w} for d, e, w in writing_days],
        "workspace_git": {"commits": commits, "repositories": repos, "first_day": g_first, "last_day": g_last},
        "commit_days": [{"day": d, "commits": c} for d, c in commit_days],
        "provider_snapshots": [
            {k: v for k, v in snapshot.items() if k in PROVIDER_FIELDS}
            for snapshot in (previous or {}).get("provider_snapshots", [])
        ],
    }
    validate(out, as_of, through)
    return out


def validate(p: dict, as_of: dt.date, through: dt.date) -> None:
    import re

    def is_day(s) -> bool:
        return isinstance(s, str) and re.match(DATE_RE, s) is not None and dt.date.fromisoformat(s) is not None

    def check(cond: bool, msg: str) -> None:
        if not cond:
            raise SystemExit(f"validation failed: {msg}")

    c = p["corpus"]
    check(all(isinstance(c[k], int) and c[k] > 0 for k in ("entries", "words", "active_days")), "corpus counts must be positive integers")
    check(is_day(c["first_day"]) and is_day(c["last_day"]), "corpus first/last day must be ISO dates")
    check(c["first_day"] <= c["last_day"] <= through.isoformat() <= as_of.isoformat(), "corpus day range out of order")
    check(all(s["source"] in SOURCE_WHITELIST for s in p["sources"]), "source outside whitelist")
    check(sum(s["entries"] for s in p["sources"]) == c["entries"], "source entries do not sum to total")
    check(sum(s["words"] for s in p["sources"]) == c["words"], "source words do not sum to total")
    wd = p["writing_days"]
    check(len(wd) == c["active_days"], "writing_days length != active_days")
    check(all(is_day(d["day"]) and d["entries"] > 0 and d["words"] >= 0 for d in wd), "writing day rows invalid")
    check([d["day"] for d in wd] == sorted(d["day"] for d in wd), "writing_days not sorted")
    check(sum(d["entries"] for d in wd) == c["entries"] and sum(d["words"] for d in wd) == c["words"], "writing_days do not sum to totals")
    g = p["workspace_git"]
    check(isinstance(g["commits"], int) and g["commits"] >= 0 and isinstance(g["repositories"], int), "git counts invalid")
    cd = p["commit_days"]
    check(sum(d["commits"] for d in cd) == g["commits"], "commit_days do not sum to total")
    check(all(is_day(d["day"]) and d["commits"] > 0 for d in cd), "commit day rows invalid")
    if cd:
        check(g["first_day"] == cd[0]["day"] and g["last_day"] == cd[-1]["day"], "git first/last day mismatch")
    for s in p["provider_snapshots"]:
        check({"provider", "reported_tokens", "display", "scope", "evidence", "received_on"} <= set(s), "provider snapshot missing keys")
        check(set(s) <= PROVIDER_FIELDS, "provider snapshot contains unexpected keys")
        check(s["provider"] in {"Codex", "Claude Code"}, "unsupported provider snapshot")
        check(isinstance(s["reported_tokens"], int) and s["reported_tokens"] > 0 and is_day(s["received_on"]), "provider snapshot values invalid")
        evidence = (ROOT / s["evidence"]).resolve()
        check(evidence.is_relative_to((ROOT / "assets/evidence").resolve()) and evidence.is_file(), "evidence must be an existing file inside assets/evidence")
    # whitelist: no unexpected top-level keys
    allowed = {"schema_version", "snapshot_at", "as_of", "timezone", "corpus_last_ingest", "corpus", "sources",
               "writing_days", "workspace_git", "commit_days", "provider_snapshots"}
    check(set(p) == allowed, f"unexpected keys: {set(p) - allowed}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True, type=Path, help="path to the Korpus SQLite file (opened read-only)")
    ap.add_argument("--as-of", type=parse_date, default=None, help="snapshot date, default today in Europe/Bratislava")
    ap.add_argument("--through", type=parse_date, default=None, help="last corpus day to include, default = as-of")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write", action="store_true", help="replace the output file (default: dry run to stdout)")
    a = ap.parse_args()
    as_of = a.as_of or dt.datetime.now(ZoneInfo(TIMEZONE)).date()
    through = a.through or as_of
    if through > as_of:
        raise SystemExit("--through must not be after --as-of")
    previous = json.loads(a.out.read_text(encoding="utf-8")) if a.out.exists() else None
    data = export(a.db, as_of, through, previous)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if a.write:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text, encoding="utf-8")
        print(f"wrote {a.out.relative_to(ROOT) if a.out.is_relative_to(ROOT) else a.out}")
    else:
        sys.stdout.write(text)
        print("(dry run: nothing written; add --write to replace the output file)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
