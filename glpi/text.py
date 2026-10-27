"""Conversão de HTML (campo 'content') para texto puro. Só stdlib."""
from __future__ import annotations

import re
from html.parser import HTMLParser


class _Extractor(HTMLParser):
    _BLOCK = {"p", "div", "br", "li", "ul", "ol", "tr", "h1", "h2", "h3",
              "h4", "h5", "h6", "pre", "table"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.parts.append("\n- ")
        elif tag in self._BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._BLOCK and tag != "li":
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(html: str | None) -> str:
    if not html:
        return ""
    p = _Extractor()
    p.feed(html)
    text = "".join(p.parts).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def ensure_html(text: str) -> str:
    """Texto simples vira <p>...</p> com escape; HTML passa direto."""
    if re.search(r"<\w+[^>]*>", text):
        return text
    esc = (text.replace("&", "&amp;").replace("<", "&lt;")
               .replace(">", "&gt;").replace("\n", "<br>"))
    return f"<p>{esc}</p>"
