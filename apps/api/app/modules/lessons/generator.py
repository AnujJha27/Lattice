"""Grounded lesson generation with hard citation validation (§18)."""
import logging
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.db.models import AIGeneration, Concept, Lesson, LessonSource
from app.modules.lessons.context import gather_contexts
from app.modules.lessons.schemas import LessonContent, LessonOut, SourceContext
from app.providers.factory import get_llm_provider

logger = logging.getLogger(__name__)

PROMPT_KEY = "lesson_generation"
PROMPT_VERSION = 1

SYSTEM_PROMPT = """You write grounded learning material worthy of a graduate-level textbook chapter. You will receive numbered source excerpts.

HARD RULES for citations:
- Every factual paragraph MUST carry "source_ids": [n, ...] referencing ONLY the provided excerpt numbers.
- NEVER invent a citation, URL, author, title or year. If no excerpt supports a claim, either omit the claim or leave that paragraph's source_ids empty.
- The "intuition" field is your own pedagogical explanation — it needs no citations.
- Examples and common_mistakes are pedagogy; cite only when they come from a specific excerpt.

Structure — write a genuine textbook chapter (2500+ words of teaching):
- intuition: one vivid paragraph, the core idea in plain language.
- sections: 6 to 8 sections forming a complete mastery path:
  1. The problem — what question or failure makes this concept necessary; what the world looked like before it.
  2. First formal contact — core definitions stated precisely, each unpacked sentence by sentence, notation explained.
  3. Mechanics — how the thing actually works, step by step, with the reasoning behind every step.
  4. The central results — the key theorems/properties/mechanisms, each stated, explained, and stress-tested against cases.
  5. Worked reasoning — walk through representative cases in detail, showing the learner's internal monologue.
  6. Boundaries and pathologies — where intuition breaks, degenerate cases, common traps.
  7. Connections — how this links to prerequisites and to adjacent fields the learner may know.
  8. Where to go from here — what this concept unlocks.
  Each section: heading, 3-5 paragraphs of 5-8 sentences. Use LaTeX equations
  (WITHOUT $ delimiters) wherever formalism helps. End each section with 2-4
  key_points that a learner must retain before continuing.
- examples: 4-6 concrete examples, at least two worked in step-by-step detail.
- common_mistakes: 4-6 genuine misconceptions, each with WHY it is wrong.

Coverage rules:
- Define every symbol you use, the first time it appears.
- Never say "it can be shown that" — either show it, sketch why, or cite the excerpt that establishes it.
- Prefer one deep explanation over three shallow ones. Do not summarize — teach.
- If the excerpts undersupport a section, teach what they support and mark the rest cautiously rather than inventing."""


def user_prompt(concept_name: str, description: str | None, depth: str,
                contexts: list[dict], known: list[str]) -> str:
    context_block = "\n\n".join(
        f"[{c['index']}] {c['title']}"
        + (f" — {c['publisher']}" if c.get("publisher") else "")
        + (f" ({c['year']})" if c.get("year") else "")
        + f"\nEXCERPT: {c['excerpt'][:1200]}"
        for c in contexts
    )
    known_block = f"\nThe learner already knows: {', '.join(known[:30])}." if known else ""
    return (
        f"Concept: {concept_name}\n"
        f"Description: {description or 'n/a'}\n"
        f"Target depth: {depth}{known_block}\n\n"
        f"SOURCES:\n{context_block}"
    )


def validate_citations(content: LessonContent, valid_indexes: set[int]) -> tuple[LessonContent, int]:
    """Strip any citation the model invented. Returns (cleaned, dropped_count)."""
    dropped = 0

    def clean(paragraphs: list) -> list:
        nonlocal dropped
        out = []
        for paragraph in paragraphs:
            valid = [i for i in paragraph.source_ids if i in valid_indexes]
            dropped += len(paragraph.source_ids) - len(valid)
            out.append(paragraph.model_copy(update={"source_ids": sorted(set(valid))}))
        return out

    cleaned_sections = [
        section.model_copy(update={"paragraphs": clean(section.paragraphs)})
        for section in content.sections
    ]
    cleaned_flat = clean(content.paragraphs)
    return content.model_copy(update={"sections": cleaned_sections, "paragraphs": cleaned_flat}), dropped


def _coerce_payload(model: type[BaseModel], data: object) -> object:
    """Free models typo schema keys ("keheading" -> "heading"). Recursively
    snap dict keys to the nearest expected field name (cutoff 0.8)."""
    from difflib import get_close_matches
    from typing import get_args, get_origin

    origin = get_origin(model)
    if origin is list:
        (element,) = get_args(model)
        if isinstance(data, list):
            return [_coerce_payload(element, item) for item in data]
        return data
    if not isinstance(data, dict):
        return data

    fields = set(model.model_fields.keys())
    out: dict = {}
    for key, value in data.items():
        match = get_close_matches(str(key), fields, n=1, cutoff=0.8)
        canonical = match[0] if match else str(key)
        if canonical in fields:
            field_type = model.model_fields[canonical].annotation
            out[canonical] = _coerce_payload(field_type, value)
        else:
            out[key] = value  # unknown key: keep, Pydantic ignores extras
    return out


def grounding_status(content: LessonContent) -> str:
    paragraphs = content.all_paragraphs()
    cited = sum(1 for p in paragraphs if p.source_ids)
    total = len(paragraphs)
    if cited == 0:
        return "GENERATED"
    if cited < total:
        return "MIXED"
    return "GROUNDED"


async def generate_lesson(
    session: AsyncSession,
    user: CurrentUser,
    concept: Concept,
    depth: str = "beginner",
) -> tuple[LessonOut, dict]:
    contexts_raw = await gather_contexts(session, concept)
    if not contexts_raw:
        raise RuntimeError("no grounding sources available")

    # Stable indexes for this generation run
    contexts = [{**c, "index": i} for i, c in enumerate(contexts_raw)]

    provider = get_llm_provider()
    response = await provider.generate_structured(
        prompt=user_prompt(concept.canonical_name, concept.description, depth, contexts, []),
        schema=LessonContent,
        system=SYSTEM_PROMPT,
    )

    # Usage accounting: exactly one row per attempt (success or failure).
    generation_row = AIGeneration(
        user_id=user.id,
        feature="lesson_generation",
        prompt_key=PROMPT_KEY,
        prompt_version=PROMPT_VERSION,
        provider=response.provider,
        model=response.model,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        latency_ms=response.latency_ms,
        success=1 if response.structured else 0,
    )
    session.add(generation_row)
    await session.flush()

    if response.structured is None:
        await session.commit()
        raise ValueError("model returned unparseable lesson JSON")

    content = LessonContent.model_validate(_coerce_payload(LessonContent, response.structured))
    valid_indexes = {c["index"] for c in contexts}
    content, dropped = validate_citations(content, valid_indexes)
    if dropped:
        logger.warning("dropped %d fabricated citation(s) for concept %s", dropped, concept.id)

    status = grounding_status(content)

    # Persist lesson + provenance
    used_source_ids = sorted({
        str(contexts[i]["source_id"]) for p in content.all_paragraphs() for i in p.source_ids
    })

    lesson = Lesson(
        concept_id=concept.id,
        user_id=user.id,
        title=concept.canonical_name,
        content=content.model_dump(),
        grounding=status,
        generated_at=datetime.now(UTC),
        generation_id=generation_row.id,
    )
    session.add(lesson)
    await session.flush()

    for sid in used_source_ids:
        session.add(LessonSource(lesson_id=lesson.id, source_id=uuid.UUID(sid), relevance=1.0))

    out_sources = [SourceContext(**c) for c in contexts]
    out = LessonOut(
        concept_id=str(concept.id),
        title=lesson.title,
        content=content,
        grounding=status,
        sources=out_sources,
        generated_at=lesson.generated_at,
        cached=False,
    )
    stats = {
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "dropped_citations": dropped,
        "contexts": len(contexts),
    }
    return out, stats
