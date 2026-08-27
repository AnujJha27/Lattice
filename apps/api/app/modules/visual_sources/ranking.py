from dataclasses import dataclass

from app.modules.visual_sources.rights import RightsClass, is_composable


@dataclass(frozen=True)
class VisualAssetCandidate:
    title: str
    canonical_url: str
    image_url: str
    rights_class: RightsClass
    relevance_score: float
    aesthetic_score: float
    rights_score: float
    quality_score: float
    thumbnail_url: str | None = None
    creator: str | None = None
    institution: str | None = None
    date: str | None = None
    license: str | None = None
    attribution_text: str | None = None
    width: int | None = None
    height: int | None = None
    provider: str = "Wikimedia Commons"


def rank_candidates(candidates: list[VisualAssetCandidate], limit: int = 12) -> list[VisualAssetCandidate]:
    usable = sorted(
        (candidate for candidate in candidates
         if is_composable(candidate.rights_class) and candidate.rights_score >= 0.7),
        key=lambda candidate: (
            -(
                0.38 * candidate.relevance_score
                + 0.18 * candidate.aesthetic_score
                + 0.22 * candidate.rights_score
                + 0.22 * candidate.quality_score
            ),
            candidate.canonical_url,
        ),
    )
    selected: list[VisualAssetCandidate] = []
    seen_canonical: set[str] = set()
    seen_images: set[str] = set()
    for candidate in usable:
        if candidate.canonical_url in seen_canonical or candidate.image_url in seen_images:
            continue
        selected.append(candidate)
        seen_canonical.add(candidate.canonical_url)
        seen_images.add(candidate.image_url)
        if len(selected) == limit:
            break
    return selected
