# Methodology

How the numbers on [the profile](../README.md) are defined, where they come from, and what they do not say. Everything shown is one frozen, dated measurement stored in [`data/profile.json`](../data/profile.json). The profile is regenerated from that file only; nothing on the page is live.

## Snapshot and freshness

| Field | Value in the current file | Meaning |
|---|---|---|
| `as_of` | `2026-10-13` | Snapshot date, Europe/Bratislava. Upper bound of every date range. |
| `corpus.last_day` | `2026-10-12` | Last corpus day included. The as-of day was still in progress and was left out. |
| `corpus_last_ingest` | timestamp in the file | When Korpus last ingested sources before the export. |
| `snapshot_at` | timestamp in the file | When the export script ran (UTC). |

Korpus keeps ingesting while this page stays still. A later snapshot will show different numbers; this page shows these.

## Human words indexed in Korpus

- **Source system:** Korpus, Adam's private writing/time/language analytics (the Lab at adam.xvadur.com, behind Cloudflare Access). Its SQLite store holds every prompt, note and commit it has indexed.
- **Measured:** `words` of entries whose `origin` is `human`, summed per source and per day. Word counting is Korpus's own tokeniser on the stored text.
- **Excluded origins:** `machine` (model output and tool logs), `pasted` (text pasted from elsewhere), `repeat` (near-duplicate re-sends). These are classified by Korpus at ingest time and are not counted anywhere on the profile.
- **Sources (whitelist):** `codex`, `claude`, `chatgpt`, `dia`, `obsidian`. Codex and Claude Code entries are the human side of agent sessions. ChatGPT and Dia are exported chat histories. Obsidian entries are notes from the vault; they are few but long, which is why their word share is large.
- **Entries:** one entry is one human prompt or one note. Entry counts are not comparable across sources (a note is longer than a prompt).
- **Day boundary:** a corpus day runs from 05:00 to 05:00 Europe/Bratislava. Writing at 02:00 belongs to the previous calendar date. Days are assigned at ingest; the export reads the stored day.
- **Coverage is partial.** The index begins 2026-01-17 and is dense only from mid-April 2026, because older sessions were imported later and not every tool exports history. Early 2026 months are therefore thin in the chart; that is coverage, not silence. Nothing before 2026 is indexed. The total is not a lifetime figure.
- **Empty calendar cell** = no indexed human writing that day. It is not evidence that no work happened.

Calendar levels (words per day): none · 1–999 · 1,000–2,999 · 3,000–7,999 · 8,000+. Thresholds are fixed in the renderer, not derived from the data, so two snapshots are comparable.

## Workspace commits

- **Measured:** rows in Korpus's `git_commits` table, which it fills from `git log --branches --no-merges` over the repositories it is configured to watch in Adam's workspace.
- **Semantics:** local git. Local branches are included, so a commit may exist that was never pushed. Author is not filtered, so commits made by agents inside those repositories count as well. Merge commits are excluded by the log flags.
- **Excluded:** the profile repository itself (`xvadur-profile`), so the page does not count its own edits.
- **Scope:** `2026-09-02` → `2026-10-11`, 13 repositories. Repository names are not exported.
- Commit counts say how often a tree was snapshotted, not how much code or whose idea it was.

## Provider token counts

Two numbers, two products, two definitions. They are shown side by side and are never added together.

| Provider | Reported | What the panel says it is | Evidence | Received |
|---|---:|---|---|---|
| Codex | 22.4B | "Lifetime tokens" on the Codex profile page | [`assets/evidence/codex-profile.png`](../assets/evidence/codex-profile.png) | 2026-10-11 |
| Claude Code | 14.4B | "Total tokens" with the **All** range selected, alongside 141 sessions, 49,318 messages, 27 active days | [`assets/evidence/claude-usage.png`](../assets/evidence/claude-usage.png) | 2026-10-11 |

- The counts are what each provider's own usage panel displayed. Adam supplied the screenshots; they were copied unchanged into `assets/evidence/`. See [`assets/evidence/README.md`](../assets/evidence/README.md) for provenance.
- "Received" is the date Adam supplied the screenshots. They do not prove the exact capture time or disclose the accounting definition behind each counter.
- Token usage can include repeated context and cached input, depending on the tool's accounting. These screenshots do not provide the input/output/cache breakdown. The displayed counts are measures of tool usage and are distinct from the words counted in Korpus.
- "Active days" in the Claude Code panel is that product's own definition and has nothing to do with Korpus days.

## What is not measured or claimed

No ranking, revenue, client outcomes, lines-of-code valuation, skill scores or deployment status is derived from these numbers. Project descriptions on the profile state their current state in words (public site, prototype, private, in development) and should be read as such.

## Reproducing the file

Both scripts are standard-library Python and make no network calls.

```text
python3 scripts/export_corpus.py --db <path to corpus.sqlite> --as-of 2026-10-13 --through 2026-10-12
python3 scripts/export_corpus.py --db <path to corpus.sqlite> --as-of 2026-10-13 --through 2026-10-12 --write
python3 scripts/render_profile.py
python3 scripts/render_profile.py --check
```

- `export_corpus.py` opens the database read-only, runs every query inside one read transaction, and writes only the whitelisted aggregates listed in its header. Without `--write` it prints to stdout and changes nothing. Only known public fields of provider snapshots are preserved from the existing file; the token figures are never recomputed.
- `render_profile.py` regenerates sixteen SVGs (English/Slovak × desktop board, mobile board, calendar, sources × light/dark) and rewrites the marked blocks in `README.md` and `README.sk.md`. `--check` exits non-zero if anything is stale.
- `build_preview.py` writes an ignored local `preview/` for inspection. It approximates GitHub and is not the target renderer.

Nothing runs on a schedule. A new snapshot is a deliberate, dated act.
