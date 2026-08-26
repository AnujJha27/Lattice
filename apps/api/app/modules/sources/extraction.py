"""HTML → readable text extraction.

Dependency-light: strips non-content elements, prefers <article>/<main> when
present. Raw HTML is never stored; extracted text becomes chunk content.
"""
import re

_STRIP_BLOCKS = re.compile(
    r"<(script|style|noscript|svg|head|nav|footer|aside|form|iframe|template)[^>]*>.*?</\1>",
    re.I | re.S,
)
_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"[ \t]+")
_PARAGRAPHS = re.compile(r"\n\s*\n")

_CONTENT_ROOTS = ("article", "main")


def extract_text(html: str) -> str:
    cleaned = _STRIP_BLOCKS.sub(" ", html)

    # Prefer the main content root if one exists.
    for root in _CONTENT_ROOTS:
        match = re.search(rf"<{root}[^>]*>(.*)</{root}>", cleaned, re.I | re.S)
        if match and len(match.group(1)) > 500:
            cleaned = match.group(1)
            break

    # Block-level tags become paragraph breaks.
    cleaned = re.sub(r"</?(p|div|h[1-6]|li|tr|section|br)[^>]*>", "\n\n", cleaned, flags=re.I)
    cleaned = _TAG.sub(" ", cleaned)

    # Basic entity unescaping.
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                         ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " ")):
        cleaned = cleaned.replace(entity, char)

    lines = [_WHITESPACE.sub(" ", line).strip() for line in cleaned.splitlines()]
    paragraphs = [line for line in lines if line]
    text = "\n\n".join(paragraphs)
    return _PARAGRAPHS.sub("\n\n", text).strip()
