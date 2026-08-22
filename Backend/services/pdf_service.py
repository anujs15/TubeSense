# services/pdf_service.py

from __future__ import annotations

import base64
import re
from io import BytesIO

import markdown as md_lib
import requests
from xhtml2pdf import pisa


_CSS = """
@page { size: A4; margin: 2cm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 11pt; color: #1a1a1a; line-height: 1.5; }
h1 { font-size: 22pt; margin: 0 0 12pt 0; }
h2 { font-size: 16pt; margin: 18pt 0 8pt 0; border-bottom: 1px solid #dddddd; padding-bottom: 4pt; }
h3 { font-size: 13pt; margin: 14pt 0 6pt 0; }
h4, h5, h6 { font-size: 11pt; margin: 12pt 0 4pt 0; }
p { margin: 0 0 8pt 0; }
ul, ol { margin: 0 0 8pt 16pt; }
li { margin: 0 0 4pt 0; }
a { color: #2563eb; text-decoration: none; }
code { font-family: "Courier New", monospace; background-color: #f3f4f6; font-size: 9.5pt; }
pre { background-color: #f6f8fa; border: 1px solid #e5e7eb; padding: 8pt; font-size: 9pt; }
pre code { background-color: #f6f8fa; }
blockquote { border-left: 3px solid #d1d5db; margin: 8pt 0; padding: 4pt 10pt; color: #4b5563; background-color: #fafafa; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; }
th, td { border: 1px solid #d1d5db; padding: 5pt 7pt; text-align: left; font-size: 10pt; }
th { background-color: #f3f4f6; }
img { max-width: 100%; }
em { color: #6b7280; }
"""

_IMG_SRC_RE = re.compile(
    r'<img([^>]*?)src=["\'](https?://[^"\']+)["\']([^>]*?)>', re.IGNORECASE
)


def _inline_remote_images(html: str) -> str:
    """Replace remote ``<img src="http(s)://…">`` with base64 ``data:`` URIs so the
    PDF renderer never hits the network (and nothing is written to disk). A fetch
    failure leaves the original tag, so xhtml2pdf falls back to its alt text."""

    def repl(m: "re.Match[str]") -> str:
        pre, url, post = m.group(1), m.group(2), m.group(3)
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "image/png").split(";")[0].strip()
            if not ctype.startswith("image/"):
                ctype = "image/png"
            b64 = base64.b64encode(resp.content).decode("ascii")
            return f'<img{pre}src="data:{ctype};base64,{b64}"{post}>'
        except Exception:
            return m.group(0)  

    return _IMG_SRC_RE.sub(repl, html)


def notes_markdown_to_pdf(markdown_text: str, title: str = "Study notes") -> bytes:
    """Convert notes markdown to PDF bytes. Raises on a hard rendering failure."""
    body_html = md_lib.markdown(
        markdown_text or "",
       
        extensions=["extra", "sane_lists"],
    )
    body_html = _inline_remote_images(body_html)

    safe_title = (title or "Study notes").strip() or "Study notes"
    html = (
        "<html><head><meta charset='utf-8'>"
        f"<title>{safe_title}</title><style>{_CSS}</style></head>"
        f"<body>{body_html}</body></html>"
    )

    out = BytesIO()
    result = pisa.CreatePDF(src=html, dest=out, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"PDF generation failed ({result.err} error(s)).")
    return out.getvalue()
