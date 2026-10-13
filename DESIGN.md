# Design

Native GitHub profile README for github.com/xvadur. GitHub owns the frame, typography and colour system; this repository adds a measured record, responsive SVGs and plain Markdown with links to actual work.

## Direction

Thesis from the brief: Adam's measured practice, connected to the systems it creates. The page leads with a title and measurement board, then the person, five distinct projects, the writing calendar and the working method. Exact figures and the monthly/source charts are in an expandable details block. Sources and definitions are linked.

## Constraints that shaped it

- **Numbers come from one frozen file.** Every figure in images and Markdown is rendered from `data/profile.json` by `scripts/render_profile.py`. The README keeps its numbers inside `<!-- generated:… -->` blocks so a refresh cannot leave stale prose behind.
- **Provider boundaries are visible.** Codex and Claude Code tokens sit in separate cells with their own scope lines. There is no grand total anywhere.
- **Calendar is writing, not tokens.** The 26-week grid shows human words per day from Korpus (05:00 day boundary, Europe/Bratislava). Fixed level thresholds, month labels, legend, window total and an explicit "empty ≠ idle" note. A weekly commits row sits under the same columns so the two timelines can be read together without being confused.
- **Self-contained SVG.** No scripts, fonts, external images, `foreignObject` or links. System font stack matches GitHub's UI so the images sit in its typographic world. Tabular numerals for all measurements. Transparent background; light and dark variants are selected with `<picture>` and `prefers-color-scheme`, and the `<img>` fallback is the light file.
- **Accessibility and mobile.** Each SVG has `<title>`, `<desc>` and a descriptive `alt`. The board changes to a 420-pixel, two-column composition below 600 pixels. Exact figures and source shares remain available in native Markdown inside the details block. The calendar and source chart are dense overviews; their data and definitions are linked.
- **Honest project state.** Public site, prototype, private, in development. No "live" claims without a public URL, no publish counts, no client outcomes.

## Palette

| Role | Light | Dark |
|---|---|---|
| Accent (XVADUR) | `#ED4E26` | `#ED4E26` / `#F2673F` |
| Text | `#1F2328` | `#E6EDF3` |
| Muted | `#59636E` | `#9198A1` |
| Rules | `#D1D9E0` | `#3D444D` |
| Empty cell | `#EBEDF0` | `#21262D` |
| Calendar levels | `#F9D4C8 → #F3A184 → #ED4E26 → #9E2F13` | `#5A2616 → #A33A1B → #ED4E26 → #FFA383` |
| Commits / monthly bars | `#57606A` | `#9198A1` |
| Sources | Codex orange, Obsidian `#8E7CC3`, Claude `#C9A27E`, Dia `#6FA8DC`, ChatGPT `#74AA9C` | lightened equivalents |

Orange marks the primary writing measurement and the writing calendar. Graphite carries the other counts. Source colours encode the source shares.

## Files

- `README.md`, `README.sk.md` – English main and Slovak alternate, same structure, cross-linked.
- `assets/en/`, `assets/sk/` – desktop board, mobile board, calendar and sources × light/dark (16 generated SVGs).
- `assets/evidence/` – two unchanged user-supplied screenshots with a provenance README.
- `data/profile.json` – frozen aggregates; the only input to the renderer.
- `docs/methodology.md` – definitions, scopes, exclusions, evidence links, reproduction.
- `scripts/export_corpus.py`, `scripts/render_profile.py`, `scripts/build_preview.py` – stdlib tooling. `preview/` is git-ignored QA only.

## Known limits

- The local preview approximates GitHub's Markdown and cannot emulate `prefers-color-scheme`; it rewrites image sources per page instead. Final rendering must be checked on github.com in both themes.
- SVG text widths depend on the viewer's system font; layouts leave slack but very different fonts could tighten the board's scope lines.
- The calendar window is 26 weeks because the corpus is dense only from April 2026; a 52-week grid would be mostly empty for coverage reasons and would read as idleness.
