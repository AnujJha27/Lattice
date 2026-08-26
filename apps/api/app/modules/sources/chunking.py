"""Chunking for embedding + retrieval.

Paragraph-aware packing to ~2000 chars with sentence-boundary trimming and
small overlap between consecutive chunks.
"""
import re

TARGET_CHARS = 2000
OVERLAP_CHARS = 200
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def chunk_text(text: str, target: int = TARGET_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()] if "\n\n" in text else [text]
    chunks: list[str] = []
    current = ""

    def flush(piece: str) -> str:
        """Trim trailing partial sentence; returns remainder to carry over."""
        remainder = ""
        if len(piece) > target * 1.3:
            sentences = _SENTENCE_END.split(piece)
            piece = ""
            for sentence in sentences:
                if len(piece) + len(sentence) > target and piece:
                    remainder = " ".join(sentences[sentences.index(sentence):])
                    break
                piece += (" " if piece else "") + sentence
        return remainder

    for paragraph in paragraphs:
        while len(paragraph) > target * 1.5:
            cut = paragraph.rfind(". ", 0, target)
            cut = cut + 1 if cut > 0 else target
            chunks.append(paragraph[:cut].strip())
            paragraph = paragraph[max(cut - overlap, 0):].strip()
        if len(current) + len(paragraph) <= target:
            current += ("\n\n" if current else "") + paragraph
            continue
        remainder = flush(current)
        if current.strip():
            chunks.append(current.strip())
        carry = remainder[-overlap:] if len(remainder) > overlap else remainder
        current = (carry + "\n\n" + paragraph).strip() if carry else paragraph

    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 80]
