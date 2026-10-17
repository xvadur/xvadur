#!/usr/bin/env python3
"""Render the profile's generated artifacts from data/profile.json.

Deterministic, standard library only. Produces:

  assets/<lang>/board-{light,dark}.svg      title + measurement board
  assets/<lang>/calendar-{light,dark}.svg   26-week human-writing calendar + weekly commits
  assets/<lang>/sources-{light,dark}.svg    monthly words trend + source shares

and rewrites the marked generated blocks in README.md (en) and README.sk.md (sk):

  <!-- generated:metrics:start --> ... <!-- generated:metrics:end -->
  <!-- generated:snapshot:start --> ... <!-- generated:snapshot:end -->

Usage:
  python3 scripts/render_profile.py            # render everything
  python3 scripts/render_profile.py --check    # exit 1 if any output would change
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "profile.json"
ASSETS = ROOT / "assets"

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
ORANGE = "#ED4E26"
WEEKS = 26
WIDTH = 920

THEMES = {
    "light": {
        "bg": "#FFFFFF", "fg": "#1F2328", "muted": "#526272", "faint": "#526272", "rule": "#D1D9E0",
        "panel": "#F6F8FA", "empty": "#EBEDF0", "bar": "#087C91", "bar_partial": "#D9A268",
        "metrics": ["#B83B19", "#7047BC", "#087C91", "#16734C", "#956214", "#AE3B88"],
        "levels": ["#F9D4C8", "#F3A184", "#ED4E26", "#9E2F13"],
        "sources": {"codex": "#16734C", "obsidian": "#7047BC", "claude": "#956214",
                    "dia": "#087C91", "chatgpt": "#AE3B88"},
    },
    "dark": {
        "bg": "#0D1117", "fg": "#E6EDF3", "muted": "#A6B3C2", "faint": "#A6B3C2", "rule": "#3D444D",
        "panel": "#161B22", "empty": "#21262D", "bar": "#6DDCEB", "bar_partial": "#D5A252",
        "metrics": ["#FF956E", "#C3A6FF", "#6DDCEB", "#7CE0AE", "#F6C875", "#F3A6D9"],
        "levels": ["#5A2616", "#A33A1B", "#ED4E26", "#FFA383"],
        "sources": {"codex": "#7CE0AE", "obsidian": "#C3A6FF", "claude": "#F6C875",
                    "dia": "#6DDCEB", "chatgpt": "#F3A6D9"},
    },
}

LEVEL_THRESHOLDS = [1, 1000, 3000, 8000]  # words/day lower bounds for levels 1..4

TEXT = {
    "en": {
        "board_kicker": "XVADUR · measured record",
        "board_title": "Adam Rudavský",
        "board_sub": "Websites, agent workflows and research systems. Healthcare 2017–2025, daily AI work since January 2025.",
        "snapshot": "snapshot {as_of} · {tz}",
        "m_words": "human words indexed",
        "m_words_scope": "Korpus · {first} → {last}",
        "m_days": "writing days indexed",
        "m_days_scope": "{entries} entries · 05:00 day boundary",
        "m_commits": "workspace commits",
        "m_commits_scope": "{repos} local repos · {first} → {last}",
        "m_codex": "Codex lifetime tokens",
        "m_codex_scope": "provider screenshot · received {recv}",
        "m_claude": "Claude Code total tokens",
        "m_claude_scope": "{sessions} sessions, {days} active days · received {recv}",
        "board_foot1": "Provider-reported token usage: two separate counters. Screenshots do not disclose the input, output or cache breakdown.",
        "board_foot2": "Words are human-origin text classified in Korpus; machine, pasted and repeat origins are excluded. Partial 2026 index, not a lifetime total.",
        "cal_title": "Writing calendar · human words per day, indexed in Korpus",
        "cal_range": "{weeks} weeks · {start} → {end}",
        "cal_window": "Window: {words} words on {days} days · empty cell = no indexed human writing that day, not proof of no work",
        "cal_legend": "words/day",
        "cal_none": "none",
        "commits_label": "commits / week",
        "commits_note": "indexed non-merge commits across {repos} workspace repos, local branches included · {first} → {last} · total {total}",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "src_title": "Human words by month, 2026",
        "src_partial": "{month} is partial · through {last}",
        "src_shares": "Share by source · {total} words",
        "src_names": {"codex": "Codex", "claude": "Claude Code", "chatgpt": "ChatGPT", "dia": "Dia", "obsidian": "Obsidian notes"},
        "src_note": "Entries: {entries} human prompts and notes, {days} days. Percentages are shares of the same {total}-word total.",
        "alt_board": "Measurement board for Adam Rudavský (XVADUR), snapshot {as_of}: {words} human words indexed in Korpus ({first} to {last}); {days} writing days; {commits} workspace commits across {repos} local repositories ({gfirst} to {glast}); Codex reports {codex} lifetime tokens and Claude Code reports {claude} total tokens, both from screenshots received {recv}.",
        "alt_calendar": "Calendar of human words written per day over {weeks} weeks ({start} to {end}), indexed in Korpus: {wwords} words on {wdays} days, plus weekly counts of indexed workspace commits since {gfirst}.",
        "alt_sources": "Human words per month in 2026 and share by source: {shares}.",
    },
    "sk": {
        "board_kicker": "XVADUR · meraný záznam",
        "board_title": "Adam Rudavský",
        "board_sub": "Weby, agentské workflow a výskumné systémy. Zdravotníctvo 2017–2025, denná práca s AI od januára 2025.",
        "snapshot": "snímka {as_of} · {tz}",
        "m_words": "ľudských slov v indexe",
        "m_words_scope": "Korpus · {first} → {last}",
        "m_days": "dní s písaním v indexe",
        "m_days_scope": "{entries} záznamov · hranica dňa 05:00",
        "m_commits": "commitov vo workspace",
        "m_commits_scope": "{repos} lokálnych repozitárov · {first} → {last}",
        "m_codex": "Codex · lifetime tokens",
        "m_codex_scope": "snímka poskytovateľa · prijatá {recv}",
        "m_claude": "Claude Code · total tokens",
        "m_claude_scope": "{sessions} sessions, {days} aktívnych dní · prijatá {recv}",
        "board_foot1": "Tokeny hlásené poskytovateľmi: dve samostatné počítadlá. Snímky neukazujú rozdelenie vstupu, výstupu a cache.",
        "board_foot2": "Slová sú text ľudského pôvodu klasifikovaný v Korpuse; strojový, vložený a opakovaný pôvod je vylúčený. Čiastočný index 2026, nie celoživotný súčet.",
        "cal_title": "Kalendár písania · ľudské slová za deň, indexované v Korpuse",
        "cal_range": "{weeks} týždňov · {start} → {end}",
        "cal_window": "Okno: {words} slov v {days} dňoch · prázdne políčko = žiadne indexované ľudské písanie v ten deň, nie dôkaz nečinnosti",
        "cal_legend": "slov/deň",
        "cal_none": "nič",
        "commits_label": "commity / týždeň",
        "commits_note": "indexované non-merge commity v {repos} repozitároch workspace, vrátane lokálnych vetiev · {first} → {last} · spolu {total}",
        "months": ["jan", "feb", "mar", "apr", "máj", "jún", "júl", "aug", "sep", "okt", "nov", "dec"],
        "days": ["po", "ut", "st", "št", "pi", "so", "ne"],
        "src_title": "Ľudské slová po mesiacoch, 2026",
        "src_partial": "{month} je čiastočný · do {last}",
        "src_shares": "Podiel podľa zdroja · {total} slov",
        "src_names": {"codex": "Codex", "claude": "Claude Code", "chatgpt": "ChatGPT", "dia": "Dia", "obsidian": "Obsidian poznámky"},
        "src_note": "Záznamy: {entries} ľudských promptov a poznámok, {days} dní. Percentá sú podiely z toho istého súčtu {total} slov.",
        "alt_board": "Merací panel Adama Rudavského (XVADUR), snímka {as_of}: {words} ľudských slov indexovaných v Korpuse ({first} až {last}); {days} dní s písaním; {commits} commitov v {repos} lokálnych repozitároch ({gfirst} až {glast}); Codex hlási {codex} lifetime tokens a Claude Code {claude} total tokens, obe zo snímok obrazovky prijatých {recv}.",
        "alt_calendar": "Kalendár ľudských slov napísaných za deň počas {weeks} týždňov ({start} až {end}), indexovaných v Korpuse: {wwords} slov v {wdays} dňoch, plus týždenné počty indexovaných commitov vo workspace od {gfirst}.",
        "alt_sources": "Ľudské slová po mesiacoch 2026 a podiel podľa zdroja: {shares}.",
    },
}


# ---------------------------------------------------------------- helpers

def fmt_int(n: int, lang: str) -> str:
    s = f"{n:,}"
    return s if lang == "en" else s.replace(",", " ")


def pct(part: int, whole: int, lang: str) -> str:
    v = 100.0 * part / whole
    s = f"{v:.1f}"
    return (s + "%") if lang == "en" else (s.replace(".", ",") + " %")


def d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def t(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".")


class SVG:
    def __init__(self, width: int, height: int, title: str, desc: str, theme: dict):
        self.w, self.h = width, height
        self.parts: list[str] = []
        self.theme = theme
        self.title, self.desc = title, desc

    def text(self, x, y, s, size=13, weight=400, fill=None, anchor="start", family=FONT,
             tabular=False, ls=None, opacity=None):
        style = f"font-family:{family};font-size:{size}px;font-weight:{weight};"
        if tabular:
            style += "font-variant-numeric:tabular-nums;"
        if ls is not None:
            style += f"letter-spacing:{ls}px;"
        attrs = f'x="{t(x)}" y="{t(y)}" fill="{fill or self.theme["fg"]}" text-anchor="{anchor}" style="{style}"'
        if opacity is not None:
            attrs += f' opacity="{opacity}"'
        self.parts.append(f"<text {attrs}>{escape(s)}</text>")

    def rect(self, x, y, w, h, fill, rx=0, extra=""):
        self.parts.append(
            f'<rect x="{t(x)}" y="{t(y)}" width="{t(w)}" height="{t(h)}" rx="{rx}" fill="{fill}"{extra}/>')

    def line(self, x1, y1, x2, y2, stroke, sw=1):
        self.parts.append(
            f'<line x1="{t(x1)}" y1="{t(y1)}" x2="{t(x2)}" y2="{t(y2)}" stroke="{stroke}" stroke-width="{sw}"/>')

    def render(self) -> str:
        head = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="title desc">\n'
            f"<title id=\"title\">{escape(self.title)}</title>\n<desc id=\"desc\">{escape(self.desc)}</desc>\n"
        )
        ground = f'<rect width="{self.w}" height="{self.h}" fill="{self.theme["bg"]}"/>'
        return head + ground + "\n" + "\n".join(self.parts) + "\n</svg>\n"


# ---------------------------------------------------------------- derived values

def derive(data: dict) -> dict:
    as_of = d(data["as_of"])
    monday = as_of - dt.timedelta(days=as_of.weekday())
    start = monday - dt.timedelta(weeks=WEEKS - 1)
    by_day = {w["day"]: w for w in data["writing_days"]}
    commits_by_day = {c["day"]: c["commits"] for c in data["commit_days"]}
    window_days = [w for w in data["writing_days"] if d(w["day"]) >= start]
    monthly: dict[str, int] = {}
    for w in data["writing_days"]:
        monthly[w["day"][:7]] = monthly.get(w["day"][:7], 0) + w["words"]
    weekly_commits = []
    for i in range(WEEKS):
        wk = start + dt.timedelta(weeks=i)
        weekly_commits.append(sum(commits_by_day.get((wk + dt.timedelta(days=j)).isoformat(), 0) for j in range(7)))
    prov = {p["provider"]: p for p in data["provider_snapshots"]}
    sources = sorted(data["sources"], key=lambda s: -s["words"])
    return {
        "as_of": as_of, "start": start, "monday": monday, "by_day": by_day,
        "window_words": sum(w["words"] for w in window_days), "window_days": len(window_days),
        "monthly": monthly, "weekly_commits": weekly_commits,
        "codex": prov["Codex"], "claude": prov["Claude Code"], "sources": sources,
    }


def level(words: int) -> int:
    lv = 0
    for i, th in enumerate(LEVEL_THRESHOLDS, start=1):
        if words >= th:
            lv = i
    return lv


# ---------------------------------------------------------------- board

def render_board(data: dict, dv: dict, lang: str, theme_name: str) -> str:
    T, th = TEXT[lang], THEMES[theme_name]
    c, g, cx, cl = data["corpus"], data["workspace_git"], dv["codex"], dv["claude"]
    alt = T["alt_board"].format(
        as_of=data["as_of"], words=fmt_int(c["words"], lang), first=c["first_day"], last=c["last_day"],
        days=c["active_days"], commits=g["commits"], repos=g["repositories"], gfirst=g["first_day"],
        glast=g["last_day"], codex=cx["display"], claude=cl["display"], recv=cx["received_on"])
    H = 306
    s = SVG(WIDTH, H, T["board_title"] + " · " + T["board_kicker"], alt, th)
    s.text(WIDTH, 104, T["snapshot"].format(as_of=data["as_of"], tz=data["timezone"]), size=12,
           fill=th["muted"], anchor="end", tabular=True)
    # title
    s.text(0, 46, T["board_title"], size=38, weight=700, fill=th["metrics"][0], ls=-0.6)
    s.text(0, 72, T["board_sub"], size=14, fill=th["muted"])
    # metric strip
    top, bottom = 128, 246
    s.line(0, top, WIDTH, top, th["rule"])
    s.line(0, bottom, WIDTH, bottom, th["rule"])
    cells = [
        (fmt_int(c["words"], lang), T["m_words"],
         T["m_words_scope"].format(first=c["first_day"], last=c["last_day"]), ORANGE),
        (str(c["active_days"]), T["m_days"],
         T["m_days_scope"].format(entries=fmt_int(c["entries"], lang)), th["fg"]),
        (str(g["commits"]), T["m_commits"],
         T["m_commits_scope"].format(repos=g["repositories"], first=g["first_day"], last=g["last_day"]), th["fg"]),
        (cx["display"], T["m_codex"], T["m_codex_scope"].format(recv=cx["received_on"]), th["fg"]),
        (cl["display"], T["m_claude"],
         T["m_claude_scope"].format(sessions=cl["sessions"], days=cl["active_days"], recv=cl["received_on"]), th["fg"]),
    ]
    n = len(cells)
    cw = WIDTH / n
    for i, (num, label, scope, color) in enumerate(cells):
        x = i * cw
        if i:
            s.line(x, top + 14, x, bottom - 14, th["rule"])
        px = x + (0 if i == 0 else 16)
        s.text(px, top + 46, num, size=30, weight=700, fill=th["metrics"][i], tabular=True, ls=-0.5)
        s.text(px, top + 68, label, size=12.5, weight=600)
        for k, part in enumerate(scope.split(" · ")):
            s.text(px, top + 86 + k * 15, part, size=11, fill=th["muted"], tabular=True)
    s.text(0, bottom + 24, T["board_foot1"], size=11.5, fill=th["muted"])
    s.text(0, bottom + 42, T["board_foot2"], size=11.5, fill=th["muted"])
    return s.render()


# ---------------------------------------------------------------- calendar

def render_calendar(data: dict, dv: dict, lang: str, theme_name: str) -> str:
    T, th = TEXT[lang], THEMES[theme_name]
    g = data["workspace_git"]
    start, as_of = dv["start"], dv["as_of"]
    alt = T["alt_calendar"].format(weeks=WEEKS, start=start.isoformat(), end=as_of.isoformat(),
                                   wwords=fmt_int(dv["window_words"], lang), wdays=dv["window_days"],
                                   gfirst=g["first_day"])
    cell, gap = 24, 4
    pitch = cell + gap
    left = 44
    grid_top = 74
    H = 372
    s = SVG(WIDTH, H, T["cal_title"], alt, th)
    s.text(0, 20, T["cal_title"], size=15, weight=600)
    s.text(WIDTH, 20, T["cal_range"].format(weeks=WEEKS, start=start.isoformat(), end=as_of.isoformat()),
           size=12, fill=th["muted"], anchor="end", tabular=True)
    # month labels: a column is labelled when it contains the 1st of a month;
    # the first column is labelled only if no month starts within the next two columns
    labels: list[tuple[int, int]] = []
    for i in range(WEEKS):
        wk = start + dt.timedelta(weeks=i)
        for j in range(7):
            day = wk + dt.timedelta(days=j)
            if day.day == 1 and day <= as_of:
                labels.append((i, day.month))
                break
    if not labels or labels[0][0] > 2:
        labels.insert(0, (0, start.month))
    for i, month in labels:
        s.text(left + i * pitch, grid_top - 12, T["months"][month - 1], size=12, fill=th["muted"])
    # day labels
    for j in (0, 2, 4, 6):
        s.text(0, grid_top + j * pitch + cell * 0.72, T["days"][j], size=11, fill=th["muted"])
    # cells
    max_in_window = 0
    for i in range(WEEKS):
        for j in range(7):
            day = start + dt.timedelta(weeks=i, days=j)
            if day > as_of:
                continue
            w = dv["by_day"].get(day.isoformat())
            words = w["words"] if w else 0
            max_in_window = max(max_in_window, words)
            lv = level(words)
            fill = th["empty"] if lv == 0 else th["levels"][lv - 1]
            x, y = left + i * pitch, grid_top + j * pitch
            s.parts.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="4" fill="{fill}">'
                f"<title>{day.isoformat()}: {fmt_int(words, lang)}</title></rect>")
    grid_bottom = grid_top + 7 * pitch - gap
    # legend (right of grid)
    lx = left + WEEKS * pitch + 20
    ly = grid_top + 2
    s.text(lx, ly + 10, T["cal_legend"], size=11, weight=600, fill=th["muted"])
    bounds = [T["cal_none"]] + [
        (f"{fmt_int(LEVEL_THRESHOLDS[i], lang)}–{fmt_int(LEVEL_THRESHOLDS[i + 1] - 1, lang)}"
         if i + 1 < len(LEVEL_THRESHOLDS) else f"{fmt_int(LEVEL_THRESHOLDS[i], lang)}+")
        for i in range(len(LEVEL_THRESHOLDS))]
    for k, label in enumerate(bounds):
        y = ly + 20 + k * 22
        fill = th["empty"] if k == 0 else th["levels"][k - 1]
        s.rect(lx, y, 14, 14, fill, rx=3)
        s.text(lx + 20, y + 11.5, label, size=11, fill=th["muted"], tabular=True)
    # window note
    s.text(0, grid_bottom + 22, T["cal_window"].format(words=fmt_int(dv["window_words"], lang), days=dv["window_days"]),
           size=11.5, fill=th["muted"])
    # weekly commits row
    row_top = grid_bottom + 44
    bar_h = 34
    base = row_top + bar_h
    maxc = max(dv["weekly_commits"]) or 1
    s.text(0, row_top + 10, T["commits_label"], size=11, weight=600, fill=th["muted"])
    s.line(left, base + 0.5, left + WEEKS * pitch - gap, base + 0.5, th["rule"])
    for i, v in enumerate(dv["weekly_commits"]):
        x = left + i * pitch
        if v <= 0:
            continue
        h = max(2, bar_h * v / maxc)
        s.rect(x, base - h, cell, h, th["bar"], rx=2)
        s.text(x + cell / 2, base - h - 4, str(v), size=10, fill=th["muted"], anchor="middle", tabular=True)
    s.text(0, base + 22, T["commits_note"].format(repos=g["repositories"], first=g["first_day"], last=g["last_day"],
                                                   total=g["commits"]), size=11.5, fill=th["muted"])
    return s.render()


# ---------------------------------------------------------------- sources

def render_sources(data: dict, dv: dict, lang: str, theme_name: str) -> str:
    T, th = TEXT[lang], THEMES[theme_name]
    c = data["corpus"]
    total = c["words"]
    shares_txt = ", ".join(f"{T['src_names'][x['source']]} {fmt_int(x['words'], lang)} ({pct(x['words'], total, lang)})"
                           for x in dv["sources"])
    alt = T["alt_sources"].format(shares=shares_txt)
    s = SVG(WIDTH, 0, T["src_title"], alt, th)
    # monthly bars
    s.text(0, 20, T["src_title"], size=15, weight=600)
    year = str(dv["as_of"].year)
    months = [f"{year}-{m:02d}" for m in range(1, dv["as_of"].month + 1)]
    vals = [dv["monthly"].get(m, 0) for m in months]
    maxv = max(vals) or 1
    chart_top, chart_h = 52, 110
    base = chart_top + chart_h
    slot = WIDTH / len(months)
    bw = min(64, slot * 0.6)
    s.line(0, base + 0.5, WIDTH, base + 0.5, th["rule"])
    last_month = c["last_day"][:7]
    for i, (m, v) in enumerate(zip(months, vals)):
        x = i * slot + (slot - bw) / 2
        h = chart_h * v / maxv
        partial = (m == last_month and c["last_day"] != _month_end(m))
        s.rect(x, base - h, bw, h, th["bar_partial"] if partial else th["metrics"][0], rx=3)
        label = fmt_int(v, lang)
        s.text(x + bw / 2, base - h - 6, label, size=11, fill=th["fg"], anchor="middle", tabular=True)
        s.text(x + bw / 2, base + 16, T["months"][int(m[5:]) - 1], size=12, fill=th["muted"], anchor="middle")
        if partial:
            s.text(WIDTH, 20, T["src_partial"].format(month=T["months"][int(m[5:]) - 1], last=c["last_day"]),
                   size=12, fill=th["muted"], anchor="end", tabular=True)
    # shares
    sy = base + 62
    s.text(0, sy, T["src_shares"].format(total=fmt_int(total, lang)), size=13, weight=600)
    bar_y = sy + 12
    x = 0.0
    for src in dv["sources"]:
        w = WIDTH * src["words"] / total
        s.rect(x, bar_y, max(w - 2, 1), 16, th["sources"][src["source"]], rx=2)
        x += w
    ly = bar_y + 40
    lx = 0.0
    for src in dv["sources"]:
        label = f"{T['src_names'][src['source']]} {fmt_int(src['words'], lang)} · {pct(src['words'], total, lang)}"
        width = 18 + len(label) * 7.2
        if lx and lx + width > WIDTH:
            lx, ly = 0.0, ly + 24
        s.rect(lx, ly - 10, 12, 12, th["sources"][src["source"]], rx=2)
        s.text(lx + 18, ly, label, size=12, tabular=True)
        lx += width + 26
    s.text(0, ly + 28, T["src_note"].format(entries=fmt_int(c["entries"], lang), days=c["active_days"],
                                           total=fmt_int(total, lang)), size=11.5, fill=th["muted"])
    s.h = int(ly + 44)
    return s.render()


def _month_end(ym: str) -> str:
    y, m = int(ym[:4]), int(ym[5:])
    nxt = dt.date(y + (m == 12), (m % 12) + 1, 1)
    return (nxt - dt.timedelta(days=1)).isoformat()


# ---------------------------------------------------------------- README blocks

def render_mobile_board(data: dict, dv: dict, lang: str, theme_name: str) -> str:
    """Recompose the measurements at phone width instead of shrinking six columns."""
    T, th = TEXT[lang], THEMES[theme_name]
    c, g, cx, cl = data["corpus"], data["workspace_git"], dv["codex"], dv["claude"]
    s = SVG(420, 548, T["board_title"], T["alt_board"].format(
        as_of=data["as_of"], words=fmt_int(c["words"], lang), first=c["first_day"], last=c["last_day"],
        days=c["active_days"], commits=g["commits"], repos=g["repositories"], gfirst=g["first_day"],
        glast=g["last_day"], codex=cx["display"], claude=cl["display"], recv=cx["received_on"]), th)
    s.text(12, 44, T["board_title"], size=34, weight=700, fill=th["metrics"][0], ls=-0.6)
    subtitle = "Websites · agents · research" if lang == "en" else "Weby · agenti · výskum"
    s.text(12, 76, subtitle, size=18, fill=th["muted"])
    s.text(12, 104, data["as_of"] + " · Europe/Bratislava", size=15, fill=th["muted"])
    s.line(12, 121, 408, 121, th["rule"])
    if lang == "en":
        labels = [("Words in Korpus", "human origin"), ("Writing days", "indexed days"),
                  ("Workspace commits", f"{g['repositories']} local repositories"),
                  ("Codex tokens", "lifetime, reported"), ("Claude Code tokens", "total, reported"),
                  ("Corpus entries", "prompts + notes")]
        foot = "Partial corpus · separate tool counters"
    else:
        labels = [("Slová v Korpuse", "ľudský pôvod"), ("Dni s písaním", "dni v indexe"),
                  ("Commity", f"{g['repositories']} lokálnych repozitárov"),
                  ("Tokeny Codex", "lifetime, hlásené"), ("Tokeny Claude Code", "total, hlásené"),
                  ("Záznamy Korpusu", "prompty + poznámky")]
        foot = "Čiastočný korpus · samostatné počítadlá"
    nums = [fmt_int(c["words"], lang), str(c["active_days"]), str(g["commits"]),
            cx["display"], cl["display"], fmt_int(c["entries"], lang)]
    for i, (num, (label, scope)) in enumerate(zip(nums, labels)):
        x = 12 + (i % 2) * 210
        y = 167 + (i // 2) * 119
        s.text(x, y, num, size=34, weight=700, fill=th["metrics"][i], tabular=True)
        s.text(x, y + 28, label, size=17, weight=600)
        s.text(x, y + 51, scope, size=15, fill=th["muted"])
    s.line(12, 492, 408, 492, th["rule"])
    s.text(12, 522, foot, size=16, fill=th["muted"])
    return s.render()


def picture(lang: str, name: str, alt: str) -> str:
    base = f"assets/{lang}/{name}"
    mobile = (
        f'  <source media="(max-width: 600px)" srcset="{base}-mobile-dark.svg">\n'
    ) if name == "board" else ""
    return (
        "<picture>\n"
        + mobile
        +
        f'  <img alt="{escape(alt, {chr(34): "&quot;"})}" src="{base}-dark.svg" width="100%">\n'
        "</picture>"
    )


def metrics_block(data: dict, dv: dict, lang: str) -> str:
    T = TEXT[lang]
    c, g, cx, cl = data["corpus"], data["workspace_git"], dv["codex"], dv["claude"]
    f = lambda n: fmt_int(n, lang)
    alt_cal = T["alt_calendar"].format(weeks=WEEKS, start=dv["start"].isoformat(), end=dv["as_of"].isoformat(),
                                       wwords=f(dv["window_words"]), wdays=dv["window_days"], gfirst=g["first_day"])
    shares_txt = ", ".join(f"{T['src_names'][x['source']]} {f(x['words'])} ({pct(x['words'], c['words'], lang)})"
                           for x in dv["sources"])
    alt_src = T["alt_sources"].format(shares=shares_txt)
    if lang == "en":
        rows = [
            ("Measure", "Value", "Scope"),
            ("Human words indexed", f"**{f(c['words'])}**", f"Korpus, {c['first_day']} → {c['last_day']}, human origin only"),
            ("Writing days indexed", f"**{c['active_days']}**", f"{f(c['entries'])} entries; day boundary 05:00 {data['timezone']}"),
            ("Workspace commits", f"**{g['commits']}**", f"{g['repositories']} local repositories, non-merge, {g['first_day']} → {g['last_day']}"),
            ("Codex lifetime tokens", f"**{cx['display']}**", f"provider screenshot, received {cx['received_on']}"),
            ("Claude Code total tokens", f"**{cl['display']}**", f"{cl['sessions']} sessions, {f(cl['messages'])} messages, {cl['active_days']} active days; screenshot received {cl['received_on']}"),
        ]
        src_line = "By source: " + "; ".join(
            f"{T['src_names'][x['source']]} {f(x['words'])} ({pct(x['words'], c['words'], lang)})" for x in dv["sources"]) + "."
        notes = (
            f"Snapshot `{data['as_of']}`. Token counts are two separate provider counters with different semantics "
            f"and are not summed. The screenshots do not disclose their input/output/cache breakdown. Words are a partial 2026 index of my own "
            f"writing, not a lifetime total. Definitions and evidence: [methodology](docs/methodology.md)."
        )
    else:
        rows = [
            ("Miera", "Hodnota", "Rozsah"),
            ("Ľudských slov v indexe", f"**{f(c['words'])}**", f"Korpus, {c['first_day']} → {c['last_day']}, iba ľudský pôvod"),
            ("Dní s indexovaným písaním", f"**{c['active_days']}**", f"{f(c['entries'])} záznamov; hranica dňa 05:00 {data['timezone']}"),
            ("Commitov vo workspace", f"**{g['commits']}**", f"{g['repositories']} lokálnych repozitárov, bez merge, {g['first_day']} → {g['last_day']}"),
            ("Codex lifetime tokens", f"**{cx['display']}**", f"snímka obrazovky poskytovateľa, prijatá {cx['received_on']}"),
            ("Claude Code total tokens", f"**{cl['display']}**", f"{cl['sessions']} sessions, {f(cl['messages'])} správ, {cl['active_days']} aktívnych dní; snímka prijatá {cl['received_on']}"),
        ]
        src_line = "Podľa zdroja: " + "; ".join(
            f"{T['src_names'][x['source']]} {f(x['words'])} ({pct(x['words'], c['words'], lang)})" for x in dv["sources"]) + "."
        notes = (
            f"Snímka `{data['as_of']}`. Počty tokenov sú dve oddelené počítadlá poskytovateľov s rôznou sémantikou "
            f"a nesčítavajú sa. Snímky neukazujú rozdelenie vstupu, výstupu a cache. Slová sú čiastočný index môjho písania za rok 2026, "
            f"nie celoživotný súčet. Definície a dôkazy: [metodika](docs/methodology.md)."
        )
    table = "\n".join(
        ["| " + " | ".join(rows[0]) + " |", "|---|---:|---|"] + ["| " + " | ".join(r) + " |" for r in rows[1:]])
    summary = "Exact figures, monthly trend and sources" if lang == "en" else "Presné čísla, mesačný vývoj a zdroje"
    detail = "\n\n".join([table, picture(lang, "sources", alt_src), src_line, notes])
    if lang == "en":
        caption = (f"**{f(dv['window_words'])} words across {dv['window_days']} indexed days** in this 26-week window "
                   f"({dv['start'].isoformat()} → {dv['as_of'].isoformat()}). "
                   "Shades: 1–999 / 1,000–2,999 / 3,000–7,999 / 8,000+ words per day. "
                   "Empty cells mean no indexed entry. Lower bars show weekly workspace commits.")
    else:
        caption = (f"**{f(dv['window_words'])} slov v {dv['window_days']} dňoch so záznamom** v tomto 26-týždňovom okne "
                   f"({dv['start'].isoformat()} → {dv['as_of'].isoformat()}). "
                   "Odtiene: 1–999 / 1 000–2 999 / 3 000–7 999 / 8 000+ slov za deň. "
                   "Prázdne políčko znamená chýbajúci záznam. Spodné stĺpce ukazujú týždenné commity.")
    return picture(lang, "calendar", alt_cal) + "\n\n" + caption + "\n\n<details>\n<summary>" + summary + "</summary>\n\n" + detail + "\n\n</details>"


def snapshot_block(data: dict, lang: str) -> str:
    if lang == "en":
        return (f"Snapshot `{data['as_of']}` ({data['timezone']}), Korpus last ingest `{data['corpus_last_ingest']}`. "
                f"Generated from [data/profile.json](data/profile.json) by `scripts/render_profile.py`.")
    return (f"Snímka `{data['as_of']}` ({data['timezone']}), posledný ingest Korpusu `{data['corpus_last_ingest']}`. "
            f"Vygenerované z [data/profile.json](data/profile.json) skriptom `scripts/render_profile.py`.")


def replace_block(text: str, name: str, body: str) -> str:
    start, end = f"<!-- generated:{name}:start -->", f"<!-- generated:{name}:end -->"
    i, j = text.find(start), text.find(end)
    if i < 0 or j < 0 or j < i:
        raise SystemExit(f"missing generated block '{name}'")
    return text[: i + len(start)] + "\n" + body + "\n" + text[j:]


# ---------------------------------------------------------------- main

def outputs(data: dict) -> dict[Path, str]:
    dv = derive(data)
    out: dict[Path, str] = {}
    for lang in ("en", "sk"):
        for theme in ("light", "dark"):
            out[ASSETS / lang / f"board-{theme}.svg"] = render_board(data, dv, lang, theme)
            out[ASSETS / lang / f"board-mobile-{theme}.svg"] = render_mobile_board(data, dv, lang, theme)
            out[ASSETS / lang / f"calendar-{theme}.svg"] = render_calendar(data, dv, lang, theme)
            out[ASSETS / lang / f"sources-{theme}.svg"] = render_sources(data, dv, lang, theme)
        readme = ROOT / ("README.md" if lang == "en" else "README.sk.md")
        if readme.exists():
            text = readme.read_text(encoding="utf-8")
            T = TEXT[lang]
            c, g = data["corpus"], data["workspace_git"]
            alt_board = T["alt_board"].format(
                as_of=data["as_of"], words=fmt_int(c["words"], lang), first=c["first_day"], last=c["last_day"],
                days=c["active_days"], commits=g["commits"], repos=g["repositories"], gfirst=g["first_day"],
                glast=g["last_day"], codex=dv["codex"]["display"], claude=dv["claude"]["display"],
                recv=dv["codex"]["received_on"])
            text = replace_block(text, "board", picture(lang, "board", alt_board))
            text = replace_block(text, "metrics", metrics_block(data, dv, lang))
            text = replace_block(text, "snapshot", snapshot_block(data, lang))
            out[readme] = text
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--check", action="store_true", help="do not write; exit 1 if outputs differ")
    a = ap.parse_args()
    data = json.loads(a.data.read_text(encoding="utf-8"))
    changed = []
    for path, content in outputs(data).items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            changed.append(path)
            if not a.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
    rel = [str(p.relative_to(ROOT)) for p in changed]
    if a.check:
        print("up to date" if not changed else "stale: " + ", ".join(rel))
        return 1 if changed else 0
    print("written: " + (", ".join(rel) if rel else "nothing changed"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
