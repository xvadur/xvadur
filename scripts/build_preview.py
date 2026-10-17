#!/usr/bin/env python3
"""Build a local QA preview of the GitHub README into the ignored preview/ directory.

Standard library only. A deliberately small Markdown subset is rendered with
GitHub-like typography and colours so the generated blocks, pictures and links
can be inspected in light and dark mode without publishing. GitHub remains the
target; this approximation is for inspection only.

  python3 scripts/build_preview.py
  open preview/index.html
"""
from __future__ import annotations

import html
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "preview"

CSS = """
:root{color-scheme:light;--fg:#1f2328;--muted:#59636e;--bg:#ffffff;--border:#d1d9e0;--code:#f6f8fa;--link:#0969da;--sidebar:#f6f8fa}
html[data-theme=dark]{color-scheme:dark;--fg:#e6edf3;--muted:#9198a1;--bg:#0d1117;--border:#3d444d;--code:#161b22;--link:#4493f8;--sidebar:#0d1117}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif}
.bar{display:flex;flex-wrap:wrap;gap:16px;align-items:center;padding:10px 24px;border-bottom:1px solid var(--border);font-size:13px;color:var(--muted)}
.bar a{color:var(--link);text-decoration:none}.bar a.on{font-weight:600;text-decoration:underline}
.page{display:grid;grid-template-columns:296px minmax(0,1fr);gap:24px;max-width:1280px;margin:0 auto;padding:24px}
.side{font-size:14px}.side .avatar{width:200px;height:200px;border-radius:50%;background:var(--code);border:1px solid var(--border)}
.side h2{font-size:24px;margin:16px 0 0}.side .handle{color:var(--muted);font-size:20px;margin:0 0 12px}
article{border:1px solid var(--border);border-radius:6px;padding:32px;min-width:0}
article h1,article h2{border-bottom:1px solid var(--border);padding-bottom:.3em;margin:24px 0 16px;font-weight:600;line-height:1.25}
article h1{font-size:2em}article h2{font-size:1.5em}article h3{font-size:1.25em;margin:24px 0 16px}
article p,article ul,article table{margin:0 0 16px}article a{color:var(--link);text-decoration:none}article a:hover{text-decoration:underline}
article pre{background:var(--code);padding:16px;border-radius:6px;overflow:auto;font-size:85%;line-height:1.45}article pre code{background:none;padding:0;font-size:100%}
article code{background:var(--code);padding:.2em .4em;border-radius:6px;font:85% ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
article table{border-collapse:collapse;display:block;overflow:auto;width:max-content;max-width:100%}
article th,article td{border:1px solid var(--border);padding:6px 13px}article th{font-weight:600}article tr:nth-child(2n) td{background:var(--code)}
article img{max-width:100%;height:auto;vertical-align:top}article picture{display:block;margin:0 0 16px}
article ul{padding-left:2em}article li{margin:.25em 0}
article blockquote{margin:0 0 16px;padding:0 1em;color:var(--muted);border-left:.25em solid var(--border)}article blockquote p:last-child{margin:0}
@media (max-width:900px){.page{grid-template-columns:minmax(0,1fr);padding:16px}.side{display:flex;flex-wrap:wrap;gap:16px;align-items:center}.side .avatar{width:64px;height:64px;flex-shrink:0}.side h2{font-size:22px}.side .handle{font-size:16px}article{padding:16px}}
"""

INLINE_PATTERNS = [
    (re.compile(r"`([^`]+)`"), lambda m: f"<code>{html.escape(m.group(1))}</code>"),
    (re.compile(r"\*\*(.+?)\*\*"), lambda m: f"<strong>{m.group(1)}</strong>"),
    (re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])"), lambda m: f"<em>{m.group(1)}</em>"),
    (re.compile(r"!\[([^\]]*)\]\(([^)]+)\)"), lambda m: f'<img alt="{m.group(1)}" src="{m.group(2)}">'),
    (re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>'),
]


def inline(text: str) -> str:
    # protect raw inline HTML tags from escaping (GitHub allows a safe subset)
    out = html.escape(text, quote=False).replace("&lt;br&gt;", "<br>")
    for pat, fn in INLINE_PATTERNS:
        out = pat.sub(fn, out)
    return out


def render_markdown(md: str, theme: str) -> str:
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    para: list[str] = []

    def flush_para():
        if para:
            out.append("<p>" + "<br>\n".join(inline(l) for l in para) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            flush_para(); i += 1; continue
        if stripped.startswith("```"):
            flush_para()
            i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i]); i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(block)) + "</code></pre>"); continue
        if stripped.startswith("<!--"):
            flush_para()
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1; continue
        if stripped.startswith(">"):
            flush_para()
            block = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                block.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            paragraphs = "\n".join(block).split("\n\n")
            out.append("<blockquote>" + "".join("<p>" + inline(p) + "</p>" for p in paragraphs) + "</blockquote>")
            continue
        if stripped.startswith("<"):  # raw HTML block until blank line
            flush_para()
            block = []
            while i < len(lines) and lines[i].strip():
                block.append(lines[i]); i += 1
            raw = "\n".join(block)
            # Fix the theme for each preview page and preserve the responsive board.
            mobile = re.search(r'srcset="([^\"]+/board-mobile-' + theme + r'\.svg)"', raw)
            raw = re.sub(r"\s*<source [^>]*>", "", raw)
            if mobile:
                raw = raw.replace("<picture>", '<picture>\n<source media="(max-width: 600px)" srcset="' + mobile.group(1) + '">')
            if theme == "dark":
                raw = re.sub(r'(<img [^>]*src=")([^"]+)-light\.svg', r"\1\2-dark.svg", raw)
            out.append(raw); continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para()
            lvl, txt = len(m.group(1)), m.group(2)
            anchor = re.sub(r"[^\w\- ]", "", txt.lower()).replace(" ", "-")
            out.append(f'<h{lvl} id="{anchor}">{inline(txt)}</h{lvl}>'); i += 1; continue
        if stripped in ("---", "***"):
            flush_para(); out.append("<hr>"); i += 1; continue
        if stripped.startswith("|"):
            flush_para()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            aligns = ["right" if c.endswith(":") and not c.startswith(":") else "left" for c in rows[1]] if len(rows) > 1 else []
            t = ["<table><thead><tr>" + "".join(f'<th align="{aligns[k] if k < len(aligns) else "left"}">{inline(c)}</th>' for k, c in enumerate(rows[0])) + "</tr></thead><tbody>"]
            for r in rows[2:]:
                t.append("<tr>" + "".join(f'<td align="{aligns[k] if k < len(aligns) else "left"}">{inline(c)}</td>' for k, c in enumerate(r)) + "</tr>")
            t.append("</tbody></table>")
            out.append("\n".join(t)); continue
        if re.match(r"^[-*]\s+", stripped):
            flush_para()
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i])); i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>"); continue
        if re.match(r"^\d+\.\s+", stripped):
            flush_para()
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i])); i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>"); continue
        para.append(line.rstrip()); i += 1
    flush_para()
    return "\n".join(out)


def page(body: str, theme: str, lang: str, title: str) -> str:
    nav = " ".join(
        f'<a class="{"on" if (l, t) == (lang, theme) else ""}" href="{l}-{t}.html">{l.upper()} {t}</a>'
        for l in ("en", "sk") for t in ("light", "dark"))
    return f"""<!doctype html><html lang="{lang}" data-theme="{theme}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{CSS}</style></head>
<body><div class="bar"><span>Local QA preview · approximation of github.com/xvadur · not the real renderer</span>{nav}</div>
<div class="page"><aside class="side"><div class="avatar"></div><h2>Adam Rudavský</h2><p class="handle">xvadur</p></aside>
<article>{body}</article></div></body></html>"""


def main() -> None:
    OUT.mkdir(exist_ok=True)
    if (OUT / "assets").exists():
        shutil.rmtree(OUT / "assets")
    shutil.copytree(ROOT / "assets", OUT / "assets", ignore=shutil.ignore_patterns("*.png"))
    (OUT / "docs").mkdir(exist_ok=True)
    (OUT / "data").mkdir(exist_ok=True)
    shutil.copy(ROOT / "data" / "profile.json", OUT / "data" / "profile.json")
    for lang, src in (("en", "README.md"), ("sk", "README.sk.md")):
        md = (ROOT / src).read_text(encoding="utf-8")
        for theme in ("light", "dark"):
            body = render_markdown(md, theme)
            # keep ordinary relative links working inside preview/
            body = body.replace('href="README.sk.md"', 'href="sk-light.html"').replace('href="README.md"', 'href="en-light.html"')
            (OUT / f"{lang}-{theme}.html").write_text(page(body, theme, lang, f"xvadur · {lang} · {theme}"), encoding="utf-8")
    meth = (ROOT / "docs" / "methodology.md")
    if meth.exists():
        body = render_markdown(meth.read_text(encoding="utf-8"), "light").replace('href="../', 'href="')
        (OUT / "docs" / "methodology.html").write_text(page(body, "light", "en", "methodology"), encoding="utf-8")
    index = "".join(f'<li><a href="{l}-{t}.html">{l.upper()} · {t}</a></li>' for l in ("en", "sk") for t in ("light", "dark"))
    (OUT / "index.html").write_text(
        f'<!doctype html><meta charset="utf-8"><title>xvadur profile preview</title><body style="font-family:-apple-system,sans-serif;padding:24px">'
        f'<h1>xvadur profile · local preview</h1><ul>{index}<li><a href="docs/methodology.html">methodology</a></li></ul>', encoding="utf-8")
    print(f"preview written to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
