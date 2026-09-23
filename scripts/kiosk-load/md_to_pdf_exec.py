#!/usr/bin/env python3
"""Convert EXEC-SUMMARY markdown to print-ready HTML + PDF via Chrome."""
from __future__ import annotations

import argparse
import html
import re
import subprocess
from pathlib import Path


def inline_fmt(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    in_ul = False
    in_ol = False
    in_pre = False
    in_table = False
    table_rows: list[list[str]] = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def flush_table() -> None:
        nonlocal in_table, table_rows
        if not table_rows:
            return
        out.append('<table>')
        for r_i, row in enumerate(table_rows):
            tag = "th" if r_i == 0 else "td"
            # skip separator row
            if r_i == 1 and all(re.match(r"^:?-+:?$", c.strip()) for c in row):
                continue
            cells = "".join(f"<{tag}>{inline_fmt(c.strip())}</{tag}>" for c in row)
            out.append(f"<tr>{cells}</tr>")
        out.append("</table>")
        table_rows = []
        in_table = False

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            close_lists()
            flush_table()
            if in_pre:
                out.append("</pre>")
                in_pre = False
            else:
                out.append("<pre>")
                in_pre = True
            i += 1
            continue
        if in_pre:
            out.append(html.escape(line))
            i += 1
            continue
        if line.strip().startswith("|") and "|" in line.strip()[1:]:
            close_lists()
            cells = [c for c in line.strip().strip("|").split("|")]
            table_rows.append(cells)
            in_table = True
            i += 1
            continue
        if in_table:
            flush_table()

        if not line.strip():
            close_lists()
            i += 1
            continue
        if line.strip() == "---":
            close_lists()
            out.append("<hr>")
            i += 1
            continue
        if line.startswith("> "):
            close_lists()
            # gather blockquote
            parts = [line[2:]]
            i += 1
            while i < len(lines) and lines[i].startswith("> "):
                parts.append(lines[i][2:])
                i += 1
            out.append("<blockquote><p>" + "<br>".join(inline_fmt(p) for p in parts) + "</p></blockquote>")
            continue
        if line.startswith("# "):
            close_lists()
            out.append(f"<h1>{inline_fmt(line[2:])}</h1>")
            i += 1
            continue
        if line.startswith("## "):
            close_lists()
            out.append(f"<h2>{inline_fmt(line[3:])}</h2>")
            i += 1
            continue
        if line.startswith("### "):
            close_lists()
            out.append(f"<h3>{inline_fmt(line[4:])}</h3>")
            i += 1
            continue
        m = re.match(r"^(\d+)\.\s+(.*)$", line)
        if m:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline_fmt(m.group(2))}</li>")
            i += 1
            continue
        if line.startswith("- "):
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline_fmt(line[2:])}</li>")
            i += 1
            continue
        # paragraph (may be bold meta lines)
        close_lists()
        out.append(f"<p>{inline_fmt(line)}</p>")
        i += 1

    close_lists()
    flush_table()
    return "\n".join(out)


CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body {
  font-family: "Sarabun", "Leelawadee UI", "Tahoma", "Segoe UI", sans-serif;
  font-size: 11pt;
  line-height: 1.45;
  color: #1a1a1a;
  max-width: 900px;
  margin: 0 auto;
  padding: 12px 8px 24px;
}
h1 {
  font-size: 18pt;
  color: #0b3d5c;
  border-bottom: 3px solid #0b3d5c;
  padding-bottom: 8px;
  margin-top: 0;
}
h2 {
  font-size: 13pt;
  color: #0b3d5c;
  margin-top: 1.4em;
  border-left: 4px solid #2a9d8f;
  padding-left: 10px;
}
h3 { font-size: 11.5pt; color: #264653; margin-top: 1.1em; }
p { margin: 0.55em 0; }
ul, ol { margin: 0.4em 0 0.6em 1.2em; padding: 0; }
li { margin: 0.25em 0; }
hr { border: none; border-top: 1px solid #ccc; margin: 1.2em 0; }
code {
  font-family: Consolas, "Courier New", monospace;
  font-size: 0.92em;
  background: #f3f5f7;
  padding: 1px 5px;
  border-radius: 3px;
}
pre {
  font-family: Consolas, "Courier New", monospace;
  font-size: 9.5pt;
  background: #f3f5f7;
  border: 1px solid #dde2e6;
  border-radius: 6px;
  padding: 10px 12px;
  white-space: pre-wrap;
  line-height: 1.35;
}
blockquote {
  margin: 0.8em 0;
  padding: 10px 14px;
  background: #eef7f5;
  border-left: 4px solid #2a9d8f;
  color: #234;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.7em 0 1em;
  font-size: 10pt;
}
th, td {
  border: 1px solid #cfd8dc;
  padding: 7px 9px;
  vertical-align: top;
  text-align: left;
}
th {
  background: #0b3d5c;
  color: #fff;
  font-weight: 600;
}
tr:nth-child(even) td { background: #f7fafc; }
.meta { color: #445; }
.footer {
  margin-top: 1.5em;
  font-size: 9.5pt;
  color: #666;
  font-style: italic;
}
.banner {
  background: #0b3d5c;
  color: #fff;
  padding: 10px 14px;
  border-radius: 6px;
  margin: 0 0 1em;
  font-size: 10.5pt;
}
.banner strong { color: #9ef0d2; }
"""


DEFAULT_BANNER = "เอกสารสรุปผู้บริหาร · ความจุระบบลงเวลาด้วยใบหน้า · วัด 23 ก.ย. 2026"


def wrap_html(body: str, title: str, banner: str = DEFAULT_BANNER) -> str:
    # mark last italic paragraph as footer if present
    body = re.sub(
        r"<p><em>(.*?)</em></p>\s*$",
        r'<p class="footer">\1</p>',
        body,
        flags=re.S,
    )
    # first meta paragraphs after h1
    return f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="banner">{html.escape(banner)}</div>
  {body}
</body>
</html>
"""


def chrome_pdf(chrome: Path, html_path: Path, pdf_path: Path) -> None:
    html_uri = html_path.resolve().as_uri()
    cmd = [
        str(chrome),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path.resolve()}",
        html_uri,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--md",
        type=Path,
        default=Path("docs/EXEC-SUMMARY-KIOSK-CAPACITY.md"),
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("docs"),
    )
    p.add_argument("--title", default=None, help="<title>; default = first '# ' heading")
    p.add_argument("--banner", default=DEFAULT_BANNER, help="top banner text")
    args = p.parse_args()
    md_text = args.md.read_text(encoding="utf-8")
    title = args.title
    if not title:
        m = re.search(r"^# (.+)$", md_text, flags=re.M)
        title = m.group(1).strip() if m else args.md.stem
    body = md_to_html(md_text)
    # soften first h1 duplicate with banner — keep h1
    page = wrap_html(body, title, args.banner)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    html_path = args.out_dir / f"{args.md.stem}.html"
    pdf_path = args.out_dir / f"{args.md.stem}.pdf"
    html_path.write_text(page, encoding="utf-8")

    chrome_candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    chrome = next((c for c in chrome_candidates if c.exists()), None)
    if not chrome:
        raise SystemExit("Chrome/Edge not found")
    chrome_pdf(chrome, html_path, pdf_path)
    print(f"HTML: {html_path.resolve()}")
    print(f"PDF:  {pdf_path.resolve()}")
    print(f"size: {pdf_path.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
