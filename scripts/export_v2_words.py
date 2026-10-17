#!/usr/bin/env python3
"""Reconcile Core V2 own-text segments into a public, aggregate-only snapshot.

Reads the existing normalized JSONL and its MANIFEST.json without modifying them.
Uses V2's segment labels, NOT its global exact-text/5-gram deduplicated counts or
sample-extrapolated authorship estimate. The result remains a classification-based
estimate, so the headline is rounded to 100,000 words.

Usage: python3 scripts/export_v2_words.py --source <zaznamy.jsonl> --write
No raw text, record identifiers, conversation titles or local paths are exported.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "v2-writing.json"
TZ = ZoneInfo("Europe/Bratislava")
PLACEHOLDER = re.compile(
    r"\[(?:príloha: [^\]]*|obrázok vložený do správy|obrázok|prepis hlasu|"
    r"vložený kontext: [^\]]*|priložený kontext: [^\]]*|cez OpenClaw/Telegram|"
    r"prístupové údaje vynechané|REDACTED)\]"
)
# V2's backup converter left these export-control blocks inside a few records.
# The excerpt is already a shortened copy; none of this block is new writing.
CONTEXT_COPY = re.compile(r"\[DEDUPED_CONTEXT_BLOCK\].*?\[END_DEDUPED_CONTEXT_BLOCK\]", re.S)
LABELS = {"vlastny", "neisty", "vlozeny_ai", "vlozeny_cudzi", "automaticky"}
PRIORITY = ["ChatGPT", "stary_gpt", "Kortex", "backup2_prompty", "Kortex_pdf_vyber",
            "archiv_promptov_2025", "Codex_rollout", "Codex_core_export"]
KORTEX = {"Kortex", "backup2_prompty", "Kortex_pdf_vyber", "archiv_promptov_2025"}
NATIVE = {"ChatGPT", "Claude", "Dia", "Codex_rollout"}


def clean(text):
    return PLACEHOLDER.sub(" ", text)


def own_words(record):
    """Recount the non-overlapping own-labelled spans; do not trust a cached sum."""
    text = record["normalized_text"] or ""
    masks = [(m.start(), m.end()) for m in CONTEXT_COPY.finditer(text)]
    previous_end = 0
    total = masked = 0
    for span in record["segmenty"]:
        a, b, label = span[:3]
        if not (0 <= a <= b <= len(text) and a >= previous_end and label in LABELS):
            raise ValueError("invalid or overlapping V2 segment coordinates/labels")
        previous_end = b
        if label != "vlastny":
            continue
        total += len(clean(text[a:b]).split())
        pieces, pos = [], a
        for start, end in masks:
            if end <= a or start >= b:
                continue
            pieces.append(text[pos:max(pos, start)])
            pieces.append(" ")
            pos = min(b, end)
        pieces.append(text[pos:b])
        masked += len(clean("".join(pieces)).split())
    return min(total, record["slov"]), min(masked, record["slov"])


def family(source):
    if source in {"ChatGPT", "stary_gpt"}:
        return "ChatGPT"
    if source in KORTEX:
        return "Writing archives"
    if source.startswith("Codex_") or source.endswith("_konverzacia"):
        return "Codex"
    return source


def public_source(source):
    group = family(source)
    if group in {"ChatGPT", "Writing archives", "Codex", "Dia"}:
        return group
    if source == "Claude":
        return "Claude Code"
    return "Notes and transcripts"


def edition(record):
    # The two backup ZIP editions have the same source name in V2.
    src = record["zdroj"]
    return (src, record["lokator"].split("/", 1)[0]) if src == "backup2_prompty" else (src,)


def priority(record):
    src = record["zdroj"]
    return (PRIORITY.index(src) if src in PRIORITY else len(PRIORITY),
            edition(record), record["lokator"])


def fingerprint(record):
    text = unicodedata.normalize("NFC", clean(record["normalized_text"] or "")).casefold()
    if record["zdroj"] in KORTEX:
        # Observed PDF font extraction loses these glyphs. Compare character
        # streams only as a copy key at the SAME SECOND in this export family.
        # The original text, spelling and word counts are never rewritten.
        text = text.translate(str.maketrans("", "", "čťďľň"))
    return hashlib.sha256("".join(c for c in text if c.isalnum()).encode()).digest()


def copy_key(record):
    if record["datum_presnost"] != "cas" or not record["datum"]:
        return ("individual", record["id"])
    stamp = dt.datetime.fromisoformat(record["datum"]).astimezone(dt.timezone.utc)
    # The old ChatGPT PDF retained minutes, the other archive exports seconds.
    if family(record["zdroj"]) == "ChatGPT":
        stamp = stamp.replace(second=0, microsecond=0)
    else:
        stamp = stamp.replace(microsecond=0)
    return (family(record["zdroj"]), stamp.isoformat(), fingerprint(record))


def remove_archive_copies(rows):
    """One-to-one copy matching; preserve multiplicity within an export edition."""
    groups = collections.defaultdict(list)
    for row in rows:
        groups[copy_key(row)].append(row)
    kept, removed = [], []
    for group in groups.values():
        editions = collections.defaultdict(list)
        for row in sorted(group, key=priority):
            editions[edition(row)].append(row)
        # Keeping the largest edition multiplicity preserves repeated writing
        # inside a conversation even when an older export rounds its timestamp.
        for index in range(max(map(len, editions.values()))):
            versions = [items[index] for items in editions.values() if len(items) > index]
            kept.append(versions[0])
            removed.extend(versions[1:])
    # Session forks can copy a native message verbatim, INCLUDING its original
    # timestamp. Match across conversation IDs only, at full timestamp precision.
    forks = collections.defaultdict(list)
    for row in kept:
        if row["zdroj"] in NATIVE and row["datum"] and row["datum_presnost"] == "cas":
            key = (row["zdroj"], dt.datetime.fromisoformat(row["datum"]).timestamp(), fingerprint(row))
        else:
            key = ("individual", row["id"])
        forks[key].append(row)
    final = []
    for group in forks.values():
        conversations = collections.defaultdict(list)
        for row in sorted(group, key=priority):
            conversations[row["rozhovor_id"] or row["id"]].append(row)
        for index in range(max(map(len, conversations.values()))):
            versions = [items[index] for items in conversations.values() if len(items) > index]
            final.append(versions[0])
            removed.extend(versions[1:])
    return final, removed


def validate_public(snapshot):
    allowed = {"schema_version", "source_system", "computed_on", "through", "coverage_years",
               "input_sha256", "input_records", "excluded_records", "raw_classified_own_words",
               "converter_copy_words_removed", "archive_copy_records_removed", "archive_copy_words_removed",
               "classified_own_words", "records_with_own_text", "rounded_estimate_words", "rounding_words",
               "authorship", "copy_handling", "scope", "sources"}
    if set(snapshot) != allowed:
        raise ValueError("V2 aggregate fields differ from the public whitelist")
    if snapshot["schema_version"] != 1 or snapshot["source_system"] != "Core V2":
        raise ValueError("unsupported V2 aggregate snapshot")
    for key in ("computed_on", "through"):
        dt.date.fromisoformat(snapshot[key])
    if snapshot["through"] > snapshot["computed_on"]:
        raise ValueError("V2 cutoff is after the reconciliation date")
    if not re.fullmatch(r"[0-9a-f]{64}", snapshot["input_sha256"]):
        raise ValueError("invalid whole-input hash")
    count_keys = {"input_records", "raw_classified_own_words", "converter_copy_words_removed",
                  "archive_copy_records_removed", "archive_copy_words_removed", "classified_own_words",
                  "records_with_own_text", "rounded_estimate_words", "rounding_words"}
    if any(type(snapshot[k]) is not int or snapshot[k] < 0 for k in count_keys):
        raise ValueError("invalid V2 aggregate counts")
    if snapshot["raw_classified_own_words"] != sum(snapshot[k] for k in (
            "converter_copy_words_removed", "archive_copy_words_removed", "classified_own_words")):
        raise ValueError("V2 own-word reconciliation does not close")
    if snapshot["rounding_words"] != 100000 or snapshot["rounded_estimate_words"] != (
            (snapshot["classified_own_words"] + 50000) // 100000) * 100000:
        raise ValueError("V2 headline rounding differs from the method")
    sources = snapshot["sources"]
    public_names = {"ChatGPT", "Claude Code", "Codex", "Dia", "Notes and transcripts", "Writing archives"}
    if any(set(s) != {"source", "records", "words"} or s["source"] not in public_names for s in sources):
        raise ValueError("V2 source rows differ from the public whitelist")
    if len({s["source"] for s in sources}) != len(sources):
        raise ValueError("duplicate V2 source groups")
    if any(type(s[k]) is not int or s[k] <= 0 for s in sources for k in ("records", "words")):
        raise ValueError("invalid V2 source counts")
    if sum(s["words"] for s in sources) != snapshot["classified_own_words"] or sum(
            s["records"] for s in sources) != snapshot["records_with_own_text"]:
        raise ValueError("V2 source totals do not close")


def export(source, computed_on):
    manifest = json.loads(source.with_name("MANIFEST.json").read_text())
    digest = hashlib.sha256()
    rows, counts = [], collections.Counter()
    for line in source.open("rb"):
        digest.update(line)
        r = json.loads(line)
        counts["input_records"] += 1
        if r["rola"] != "user":
            counts["other_roles"] += 1
            continue
        if r["embargo"]:
            counts["publication_boundary"] += 1
            continue
        if r["zdroj"] == "ChatGPT_prilohy":
            counts["standalone_attachments"] += 1
            continue
        before, after = own_words(r)
        if before != r["slov_vlastne"]:
            raise ValueError("recount differs from V2 own-word sum")
        r["measured_own_words"] = after
        counts["converter_copy_words_removed"] += before - after
        rows.append(r)
    kept, removed = remove_archive_copies(rows)
    by_source = collections.defaultdict(collections.Counter)
    for r in kept:
        if r["measured_own_words"]:
            by_source[public_source(r["zdroj"])].update(records=1, words=r["measured_own_words"])
    words = sum(v["words"] for v in by_source.values())
    assert counts["input_records"] == manifest["zaznamov"]
    assert len(kept) + len(removed) == len(rows)
    assert sum(r["slov_vlastne"] for r in rows) == (
        words + sum(r["measured_own_words"] for r in removed) + counts["converter_copy_words_removed"])
    dated = [dt.datetime.fromisoformat(r["datum"]).astimezone(TZ).year
             for r in kept if r["measured_own_words"] and r["datum"]]
    result = {
        "schema_version": 1,
        "source_system": "Core V2",
        "computed_on": computed_on,
        "through": dt.datetime.fromisoformat(manifest["cutoff"]).date().isoformat(),
        "coverage_years": [min(dated), max(dated)],
        "input_sha256": digest.hexdigest(),
        "input_records": counts["input_records"],
        "excluded_records": {k: counts[k] for k in ("other_roles", "publication_boundary", "standalone_attachments")},
        "raw_classified_own_words": sum(r["slov_vlastne"] for r in rows),
        "converter_copy_words_removed": counts["converter_copy_words_removed"],
        "archive_copy_records_removed": len(removed),
        "archive_copy_words_removed": sum(r["measured_own_words"] for r in removed),
        "classified_own_words": words,
        "records_with_own_text": sum(v["records"] for v in by_source.values()),
        "rounded_estimate_words": ((words + 50000) // 100000) * 100000,
        "rounding_words": 100000,
        "authorship": "Existing V2 own-labelled segments; automatic classification, not a manual census or a statistical confidence interval.",
        "copy_handling": "Same-time, same-text export copies counted once; native session forks matched at full timestamp precision. Repeated wording at different times is retained. No global text or 5-gram deduplication.",
        "scope": "Preserved own-classified text in the available archive, including typed text and dictation. Does not measure newly composed words or all lifetime writing. Uncertain, AI, foreign and automatic segments are excluded.",
        "sources": [{"source": s, **dict(v)} for s, v in sorted(by_source.items())],
    }
    validate_public(result)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--computed-on", default=dt.datetime.now(TZ).date().isoformat())
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    dt.date.fromisoformat(a.computed_on)
    result = json.dumps(export(a.source, a.computed_on), ensure_ascii=False, indent=2) + "\n"
    if a.write:
        a.out.write_text(result, encoding="utf-8")
        print(f"wrote {a.out.name}")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
