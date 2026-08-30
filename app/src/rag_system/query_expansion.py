"""Static, bidirectional acronym expansion for retrieval queries.

Closes retrieval failure mode #3b from the course (acronyms & abbreviations):
embedding models treat strings like ``DNxHR`` or ``AGB`` as meaningless
character sequences, so a query using the acronym misses chunks that only
use the full term — and vice versa.

The expansion is a hand-maintained, domain-specific dictionary (post
production / German business offers). It runs on the QUERY side only, so
no index rebuild is needed and no LLM call is involved — it is a
deterministic string lookup with ~0 ms latency. The original question is
never modified for reranking, the refusal gate, or answer generation.
"""

from __future__ import annotations

import re

# canonical acronym -> full term(s) to append to the query.
# Keys are matched case-insensitively (and hyphen-insensitively); the
# canonical spelling is what gets appended in the reverse direction.
EXPANSIONS: dict[str, str] = {
    # technical / post production
    "DNxHR": "Dolby Vision Codec",
    "UHD": "Ultra HD 4K",
    "HD": "High Definition",
    "SDR": "Standard Dynamic Range",
    "HDR": "High Dynamic Range",
    "DCI": "Digital Cinema Initiatives",
    "DCP": "Digital Cinema Package",
    "AVC": "Advanced Video Coding H.264",
    "QC": "Quality Control",
    "VFX": "Visual Effects",
    "EOTF": "Electro-Optical Transfer Function",
    "YCbCr": "YCbCr Farbraum",
    "ITU": "ITU Standard",
    "RGB": "RGB Farbraum",
    "MXF": "MXF Container",
    "MP4": "MP4 Container",
    "exFAT": "exFAT Dateisystem",
    "USB": "USB Datenträger",
    "XML": "XML Metadaten",
    # contract / admin (German business)
    "AGB": "Allgemeine Geschäftsbedingungen",
    "USt-IdNr": "Umsatzsteuer-ID Steuernummer",
    "PKW": "Personenkraftwagen",
    "kWh": "Kilowattstunde",
    "GmbH": "Gesellschaft mit beschränkter Haftung",
}

# reverse direction: first two words of each full term -> acronym
FULL_TO_ACRONYM: dict[str, str] = {
    " ".join(v.lower().split()[:2]): k for k, v in EXPANSIONS.items()
}


def _normalized(text: str) -> str:
    """Lowercase and collapse hyphens to spaces for phrase matching."""
    return text.lower().replace("-", " ")


def expand_query(question: str) -> str:
    """Return the question with acronym expansions appended.

    Bidirectional: acronyms found in the question get their full terms
    appended, and full terms get their acronyms appended. If nothing
    matches, the question is returned unchanged.
    """
    additions: list[str] = []
    norm = _normalized(question)
    for acronym, full in EXPANSIONS.items():
        if re.search(rf"\b{re.escape(_normalized(acronym))}\b", norm):
            additions.append(full)
    for phrase, acronym in FULL_TO_ACRONYM.items():
        if phrase in norm:
            additions.append(acronym)
    if not additions:
        return question
    # de-duplicate while preserving order
    seen: set[str] = set()
    unique = [a for a in additions if not (a.lower() in seen or seen.add(a.lower()))]
    return question + " " + " ".join(unique)
