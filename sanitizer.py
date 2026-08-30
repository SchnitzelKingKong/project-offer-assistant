"""
PII Sanitizer für die Angebotspipeline.

Angelehnt an den Security-Abschnitt des freeCodeCamp-Kurses
("Production RAG with LangChain & Vector Databases"):
- Regex-basierte PII-Erkennung (deterministisch, testbar, kein extra Modell)
- detect()  → listet, was gefunden wurde (für Logging/Evaluation)
- mask()    → ersetzt durch Redaction-Marker (für den Ingest)

WICHTIG: Läuft VOR Chunking/Embedding — Kundendaten dürfen weder in
die SQLite-Tabelle noch in den Vektorindex.

Deutsche Anpassungen: IBAN, deutsche Telefonnummern, E-Mail,
Kontonummer, BIC. Namen/Adressen sind Regex-unscharf → optional
per LLM nachfassen (siehe Notebook).
"""

import re
from dataclasses import dataclass, field


@dataclass
class PIIReport:
    """Was wurde gefunden? (für Golden-Set-Evaluation des Sanitizers)"""
    found: dict = field(default_factory=dict)   # {"email": 2, "iban": 1, ...}
    masked_text: str = ""

    def summary(self) -> str:
        if not self.found:
            return "Keine PII gefunden"
        parts = [f"{k}={v}" for k, v in self.found.items()]
        return ", ".join(parts)


# --- PII-Patterns (Regex) ---
# Reihenfolge ist wichtig: IBAN/Kontonummer VOR generischer Zahlenerkennung.
PII_PATTERNS: dict[str, re.Pattern] = {
    # IBAN: DE + 20 weitere Stellen (2 Prüfziffern + 18 Kontostellen),
    # mit oder ohne Leerzeichen. MUSS vor ust_id laufen (DE + 9 Ziffern wäre Teilmenge).
    "iban": re.compile(r"\bDE\d{2}(?:\s?\d){18}\b"),
    # BIC: exakt 8 oder 11 Zeichen (4 Bank + 2 Land + 2 Ort [+ 3 Filiale]).
    # WICHTIG: nur mit Label-Kontext ("BIC:" / "SWIFT") erkennen. Ein reines
    # Buchstaben-Pattern würde deutsche Großwörter wie "LEISTUNGEN" oder
    # "BEDINGUNGEN" (8-11 Zeichen) fälschlich als BIC maskieren und den
    # Angebots-Text im Index korruptieren. Die Gruppen: (1)=Label, (2)=Trenner,
    # (3)=BIC-Code. mask() ersetzt nur Gruppe 3 und behält Label+Trenner.
    "bic": re.compile(
        r"\b(BIC|SWIFT)(\s*[:.]?\s*)([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b"
    ),
    # E-Mail
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    # Deutsche Telefonnummern: +49 / 0049 / 0 voran, 6-20 Zeichen danach.
    # (?<!\d) statt \b: verhindert, dass eine 0 mitten in einer anderen Zahl
    # (z.B. PLZ "22607" oder Hausnummer "208") als Vorwahl matcht.
    # [ \t] statt \s: verhindert Matches ueber Zeilenumbrueche hinweg
    # (z.B. "Straße 208\n22607 Hamburg" war frueher ein False Positive).
    "phone": re.compile(
        r"(?<!\d)(?:\+49|0049|0)[ \t]?[\d \t\-()]{6,20}\d\b"
    ),
    # USt-IdNr: DE + 9 Ziffern, mit oder ohne Leerzeichen (z.B. "DE 111 222 333").
    # Das \b nach der 9. Ziffer schützt vor Teil-Matches in IBANs (DE + 20 Ziffern),
    # die vorher gelaufen sind.
    "ust_id": re.compile(r"\bDE(?:\s?\d){9}\b"),
    # Steuernummer: XX/XXX/XXXXX (z.B. "00/000/00000")
    "steuer_nr": re.compile(r"\b\d{2}/\d{3}/\d{5}\b"),
    # Straße + Hausnummer (z.B. "Caprivistr. 11", "Baron-Voght-Straße 208",
    # "Dreiecksplatz 7", "Westendstraße 49a"). Fangt Abkürzungen (str.),
    # Bindestrich-Namen und Buchstaben-Zusätze (2a). PLZ/Ort-Zeilen bleiben
    # unangetastet (kein Straßennamen-Wort) — die Redaktions-Policy behält
    # die Kunden-PLZ/Ort bewusst bei.
    "street": re.compile(
        r"\b[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-]*"
        r"(?:straße|str\.?|weg|platz|allee|ring|gasse|hof|kamp|damm|feld|garten|pfad|chaussee|bogen|markt)"
        r"\.?[ \t]*\d+[a-z]?\b",
        re.IGNORECASE,
    ),
}

# Marker, die mask() einsetzt
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

# Maskierungs-Reihenfolge: spezifische Muster zuerst, das generische
# Phone-Pattern zuletzt. IBAN (DE+20) vor USt-IdNr (DE+9) vor Phone,
# damit keine Teilmenge von einem breiteren Pattern "aufgefressen" wird.
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
    """Detect + mask PII in Text. Deterministisch, nur Regex."""

    def detect(self, text: str) -> dict[str, list[str]]:
        """Gibt alle gefundenen PII-Instanzen pro Kategorie zurück."""
        found: dict[str, list[str]] = {}
        for category, pattern in PII_PATTERNS.items():
            if category == "bic":
                # BIC-Pattern hat 3 Gruppen (Label, Trenner, Code) → nur den
                # Code (Gruppe 3) als Instanz zählen.
                matches = [m.group(3) for m in pattern.finditer(text)]
            else:
                matches = pattern.findall(text)
            if matches:
                found[category] = matches
        return found

    def mask(self, text: str) -> PIIReport:
        """Ersetzt alle PII-Instanzen durch Redaction-Marker.

        Die Reihenfolge ist wichtig: spezifische Muster (IBAN, USt-IdNr)
        müssen VOR dem generischen Phone-Pattern laufen. Sonst frisst das
        Phone-Pattern Ziffernfolgen, die zu einer USt-IdNr gehören
        (z.B. die "000000001" in "DE000000001") und maskt sie als
        [PHONE_REDACTED] statt [USTID_REDACTED].
        """
        masked = text
        counts: dict[str, int] = {}
        for category in MASK_ORDER:
            pattern = PII_PATTERNS[category]
            if category == "bic":
                # Nur den BIC-Code (Gruppe 3) ersetzen, Label+Trenner behalten.
                def _bic_repl(m: re.Match) -> str:
                    return f"{m.group(1)}{m.group(2)}{MASK_MAP['bic']}"
                masked, n = pattern.subn(_bic_repl, masked)
            else:
                masked, n = pattern.subn(MASK_MAP[category], masked)
            if n:
                counts[category] = n
        return PIIReport(found=counts, masked_text=masked)


if __name__ == "__main__":
    # Quick-Selbsttest (nur fiktive Werte — keine echte PII im Repo)
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
    print("Gefunden:", report.summary())
    print("--- Maskierter Text ---")
    print(report.masked_text)
