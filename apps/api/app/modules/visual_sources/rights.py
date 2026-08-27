from enum import StrEnum


class RightsClass(StrEnum):
    PUBLIC_DOMAIN = "PUBLIC_DOMAIN"
    CC0 = "CC0"
    CC_BY = "CC_BY"
    CC_BY_SA = "CC_BY_SA"
    RESTRICTED = "RESTRICTED"
    UNKNOWN = "UNKNOWN"


def classify_license(value: str | None) -> RightsClass:
    text = (value or "").casefold().replace("-", " ").replace("_", " ")
    if "public domain" in text or text in {"pd", "pdm"}:
        return RightsClass.PUBLIC_DOMAIN
    if "cc0" in text or "creative commons zero" in text:
        return RightsClass.CC0
    if "cc by sa" in text or "cc-by-sa" in text:
        return RightsClass.CC_BY_SA
    if "cc by" in text or "cc-by" in text:
        return RightsClass.CC_BY
    if "restrict" in text or "all rights" in text or "non commercial" in text or "no derivatives" in text:
        return RightsClass.RESTRICTED
    return RightsClass.UNKNOWN


def is_composable(rights_class: RightsClass) -> bool:
    return rights_class in {RightsClass.PUBLIC_DOMAIN, RightsClass.CC0, RightsClass.CC_BY, RightsClass.CC_BY_SA}
