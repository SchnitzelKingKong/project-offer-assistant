"""
PII Sanitizer for the offer pipeline.

Based on the security section of the freeCodeCamp course
("Production RAG with LangChain & Vector Databases"):
- Regex-based PII detection (deterministic, testable, no extra model)
- detect()  → lists what was found (for logging / evaluation)
- mask()    → replaces with redaction markers (for ingestion)

IMPORTANT: runs BEFORE chunking / embedding — customer data must never
end up in the SQLite table or the vector index.

German-specific patterns: IBAN, German phone numbers, email,
account number, BIC. Names / addresses are fuzzy for regex → optionally
follow up with an LLM pass (see notebook).
"""

import re
from dataclasses import dataclass, field


@dataclass
class PIIReport:
    """What was found? (for golden-set evaluation of the sanitizer)"""
    found: dict = field(default_factory=dict)   # {"email": 2, "iban": 1, ...}
    masked_text: str = ""

    def summary(self) -> str:
        if not self.found:
            return "No PII found"
        parts = [f"{k}={v}" for k, v in self.found.items()]
        return ", ".join(parts)


# --- PII patterns (regex) ---
# Order matters: IBAN / account number BEFORE generic number detection.
PII_PATTERNS: dict[str, re.Pattern] = {
    # IBAN: DE + 20 further digits (2 check digits + 18 account digits),
    # with or without spaces. MUST run before ust_id (DE + 9 digits is a subset).
    "iban": re.compile(r"\bDE\d{2}(?:\s?\d){18}\b"),
    # BIC: exactly 8 or 11 characters (4 bank + 2 country + 2 location [+ 3 branch]).
    # IMPORTANT: only detect with label context ("BIC:" / "SWIFT"). A bare
    # letter pattern would falsely mask German all-caps words like "LEISTUNGEN"
    # or "BEDINGUNGEN" (8-11 characters) as BICs and corrupt the offer text
    # in the index. Groups: (1)=label, (2)=separator, (3)=BIC code.
    # mask() replaces only group 3 and keeps label + separator.
    "bic": re.compile(
        r"\b(BIC|SWIFT)(\s*[:.]?\s*)([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b"
    ),
    # E-Mail
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    # German phone numbers: +49 / 0049 / 0 prefix, 6-20 characters after.
    # (?<!\d) instead of \b: prevents a 0 in the middle of another number
    # (e.g. postal code "22607" or house number "208") from matching as a prefix.
    # [ \t] instead of \s: prevents matches across line breaks
    # (e.g. "Straße 208\n22607 Hamburg" used to be a false positive).
    "phone": re.compile(
        r"(?<!\d)(?:\+49|0049|0)[ \t]?[\d \t\-()]{6,20}\d\b"
    ),
    # VAT ID (USt-IdNr): DE + 9 digits, with or without spaces (e.g. "DE 111 222 333").
    # The \b after the 9th digit protects against partial matches inside IBANs
    # (DE + 20 digits), which ran earlier.
    "ust_id": re.compile(r"\bDE(?:\s?\d){9}\b"),
    # Tax number (Steuernummer): XX/XXX/XXXXX (e.g. "00/000/00000")
    "steuer_nr": re.compile(r"\b\d{2}/\d{3}/\d{5}\b"),
    # Street + house number (e.g. "Caprivistr. 11", "Baron-Voght-Straße 208",
    # "Dreiecksplatz 7", "Westendstraße 49a"). Catches abbreviations (str.),
    # hyphenated names and letter suffixes (2a). Postal-code/city lines are
    # left untouched (no street-name word) — the redaction policy keeps the
    # customer's postal code / city on purpose.
    "street": re.compile(
        r"\b[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-]*"
        r"(?:straße|str\.?|weg|platz|allee|ring|gasse|hof|kamp|damm|feld|garten|pfad|chaussee|bogen|markt)"
        r"\.?[ \t]*\d+[a-z]?\b",
        re.IGNORECASE,
    ),
}

# Markers used by mask()
MASK_MAP: dict[str, str] = {
    "iban": "[IBAN_REDACTED]",
    "bic": "[BIC_REDACTED]",
    "email": "[EMAIL_REDACTED]",
    "phone": "[PHONE_REDACTED]",
    "account_number": "[KONTO_REDACTED]",
    "ust_id": "[USTID_REDACTED]",
    "steuer_nr": "[STEUERNR_REDACTED]",
    "street": "[ADRESSE_REDACTED]",
}

# Masking order: specific patterns first, the generic phone pattern last.
# IBAN (DE+20) before VAT ID (DE+9) before phone, so no subset gets
# "eaten" by a broader pattern.
MASK_ORDER: list[str] = [
    "iban",
    "ust_id",
    "steuer_nr",
    "bic",
    "email",
    "phone",
    "street",
]


class PIISanitizer:
    """Detect + mask PII in text. Deterministic, regex only."""

    def detect(self, text: str) -> dict[str, list[str]]:
        """Return all PII instances found, per category."""
        found: dict[str, list[str]] = {}
        for category, pattern in PII_PATTERNS.items():
            if category == "bic":
                # The BIC pattern has 3 groups (label, separator, code) →
                # only count the code (group 3) as an instance.
                matches = [m.group(3) for m in pattern.finditer(text)]
            else:
                matches = pattern.findall(text)
            if matches:
                found[category] = matches
        return found

    def mask(self, text: str) -> PIIReport:
        """Replace all PII instances with redaction markers.

        Order matters: specific patterns (IBAN, VAT ID) must run BEFORE the
        generic phone pattern. Otherwise the phone pattern eats digit runs
        that belong to a VAT ID (e.g. the "000000001" in "DE000000001") and
        masks them as [PHONE_REDACTED] instead of [USTID_REDACTED].
        """
        masked = text
        counts: dict[str, int] = {}
        for category in MASK_ORDER:
            pattern = PII_PATTERNS[category]
            if category == "bic":
                # Replace only the BIC code (group 3), keep label + separator.
                def _bic_repl(m: re.Match) -> str:
                    return f"{m.group(1)}{m.group(2)}{MASK_MAP['bic']}"
                masked, n = pattern.subn(_bic_repl, masked)
            else:
                masked, n = pattern.subn(MASK_MAP[category], masked)
            if n:
                counts[category] = n
        return PIIReport(found=counts, masked_text=masked)


if __name__ == "__main__":
    # Quick self-test (fictitious values only — no real PII in the repo)
    sample = (
        "Kunde: Max Mustermann, max@mustermann-film.de, Tel. +49 171 2345678\n"
        "Zahlung auf IBAN DE00 1234 5678 0000 0000 01, BIC: TESTDEFFXXX\n"
        "USt.-IdNr.: DE000000001\n"
        "Finanzamt Beispiel · USt-IdNr.: DE 111 222 333\n"
        "Steuernummer: 00/000/00000\n"
        "STUDIO / Caprivistr. 11 - 24105 Kiel\n"
        "Kunde: Muster GmbH, Baron-Voght-Straße 208, 22607 Hamburg"
    )
    s = PIISanitizer()
    report = s.mask(sample)
    print("Found:", report.summary())
    print("--- Masked text ---")
    print(report.masked_text)
