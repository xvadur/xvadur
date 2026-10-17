# Methodology

The numbers on [the profile](../README.md) come from two frozen snapshots: [`data/v2-writing.json`](../data/v2-writing.json) measures own-classified text across the available Core V2 archive; [`data/profile.json`](../data/profile.json) supplies the narrower Korpus daily index, Git activity and provider screenshots. Nothing on the page is live.

## Own words archived — Core V2

The headline is **approximately 2.4 million own words**, covering material dated **2017–2026**, through **2026-10-14**. The reconciliation was run on **2026-10-17** against the existing V2 normalized records. The exact classifier-derived sum is **2,409,914**; rounding the headline avoids implying that automatic authorship classification is a manual word-by-word census.

| Reconciliation | Words |
|---|---:|
| Words in V2 segments labelled `vlastny` (own), before copy reconciliation | 3,379,008 |
| Export-control blocks containing shortened context copies | −3,314 |
| Matched archive and native-session fork copies | −965,780 |
| Own-classified words retained | **2,409,914** |

- **Input:** 40,964 normalized V2 records. The file's SHA-256 is recorded in the public aggregate JSON. It is the same input used by the current V2 text report.
- **Selection:** user-side records only. Excludes 10,543 other-role records, 321 user records outside the publication boundary and 67 standalone attachments. Inside the remaining records, only segments labelled `vlastny` count. Segments labelled uncertain, inserted AI, foreign or automatic do not count, even inside a mixed message.
- **Words:** whitespace-separated items, recounted from the original segment coordinates after removing converter placeholders. The recount is checked against every V2 cached own-word sum. Typed text and transcribed dictation both count.
- **Copy matching:** within an export family, match the timestamp and the normalized alphanumeric character stream. The old ChatGPT PDF retained minutes; other export matches use seconds. Source editions are matched one-to-one and the largest within-edition multiplicity is preserved. The two backup ZIP editions are treated as separate editions.
- **PDF conversion:** Kortex PDF extraction loses some Slovak glyphs (`č`, `ť`, `ď`, `ľ`, `ň`) and inserts spaces. These glyphs and spacing are ignored in the copy key at the same second within that archive family. The original text and its word count are not rewritten. Structured exports take priority over lossy PDF copies.
- **Native session forks:** identical messages copied into different conversations with the same full original timestamp count once. A message with the same wording at a different time remains in the count.
- **No global wording penalty:** the V2 `slov_vlastne_dedup` field, global exact-text elimination, sampled 5-gram overlap and the previous sample-extrapolated authorship estimate are not used. Similar phrasing alone does not reduce the count.

This measures **own-classified text preserved in the available archive**. It does not reconstruct how many words were newly composed: an own text pasted again at another time remains an own-text occurrence. Revised or differently converted copies can remain unmatched. Authorship labels are inferred from converter metadata and language/style rules; the existing V2 spot check is not a complete manual review. The rounded figure is therefore an estimate, not an exact lifetime writing total or a statistical confidence interval. Some notes also have estimated dates; those dates are not used to create a new writing-day count.

The older approximately 2.37-million figure came from an earlier working count. The current V2 descriptive report's **4,847,123 words** uses a different definition: preserved user-side inputs after technical filtering, including archive copies and inserted nontechnical texts. Neither number is substituted for this own-segment reconciliation. The profile's former **646,607-word** headline was the partial Korpus index described below; it remains the denominator for its own calendar and source chart.

## Korpus snapshot and freshness

| Field | Value in the current file | Meaning |
|---|---|---|
| `as_of` | `2026-10-13` | Korpus snapshot date, Europe/Bratislava. Upper bound of its index and chart date ranges. |
| `corpus.last_day` | `2026-10-12` | Last corpus day included. The as-of day was still in progress and was left out. |
| `corpus_last_ingest` | timestamp in the file | When Korpus last ingested sources before the export. |
| `snapshot_at` | timestamp in the file | When the export script ran (UTC). |

Korpus keeps ingesting while this page stays still. A later snapshot will show different numbers; this page shows these.

## Human words indexed in Korpus

- **Source system:** Korpus, Adam's private writing/time/language analytics (the Lab at adam.xvadur.com, behind Cloudflare Access). Its SQLite store holds every prompt, note and commit it has indexed.
- **Measured:** `words` of entries whose `origin` is `human`, summed per source and per day. Word counting is Korpus's own tokeniser on the stored text.
- **Excluded origins in the Korpus index:** `machine` (model output and tool logs), `pasted` (text pasted from elsewhere), `repeat` (near-duplicate re-sends). These are classified by Korpus at ingest time. Core V2 uses its separate segment-based definition above.
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

The scripts use standard-library Python and make no network calls. Source paths stay local; only aggregates are exported.

```text
python3 scripts/export_corpus.py --db <path to corpus.sqlite> --as-of 2026-10-13 --through 2026-10-12
python3 scripts/export_corpus.py --db <path to corpus.sqlite> --as-of 2026-10-13 --through 2026-10-12 --write
python3 scripts/export_v2_words.py --source <path to V2 normalizovane/zaznamy.jsonl> --computed-on 2026-10-17 --write
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/render_profile.py
python3 scripts/render_profile.py --check
```

- `export_corpus.py` opens the database read-only, runs every query inside one read transaction, and writes only the whitelisted aggregates listed in its header. Without `--write` it prints to stdout and changes nothing. Only known public fields of provider snapshots are preserved from the existing file; the token figures are never recomputed.
- `export_v2_words.py` reads the normalized JSONL and adjacent `MANIFEST.json` without changing them. It validates segment boundaries, recounts own words and reconciles removals to source totals. Its explicit public output contains only aggregate counts, dates, method descriptions and a whole-input hash. It never exports text, record IDs, titles or local paths.
- `render_profile.py` reads both independent aggregate snapshots, regenerates sixteen SVGs (English/Slovak × desktop board, mobile board, calendar, sources × light/dark) and rewrites the marked blocks in `README.md` and `README.sk.md`. `--check` exits non-zero if anything is stale. Refreshing Korpus cannot overwrite the V2 headline.
- `build_preview.py` writes an ignored local `preview/` for inspection. It approximates GitHub and is not the target renderer.

Nothing runs on a schedule. A new snapshot is a deliberate, dated act.
