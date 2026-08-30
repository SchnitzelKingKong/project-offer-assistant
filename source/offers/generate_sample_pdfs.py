#!/usr/bin/env python3
"""Generate fictitious offer PDFs for the submission package.

This script produces a small, fully fictitious corpus of German post-production
offer PDFs ("Angebote" / "Kostenvoranschläge"). It exists so the submission
package can demonstrate the *full* pipeline — from raw PDF to indexed, redacted
chunks — **without any real customer data**.

Design goals
------------
1. **Clearly fictitious.** Every name, address, IBAN, BIC, e-mail, phone,
   USt-IdNr and Steuernummer is invented. No value is taken from the real
   corpus.
2. **Sanitizer-compatible.** The fictitious values deliberately *match* the
   regex patterns the sanitizer redacts (IBAN, BIC, e-mail, phone,
   USt-IdNr ``DE\\d{9}``, Steuernummer ``\\d{2}/\\d{3}/\\d{5}``). Running the
   pipeline on these PDFs therefore exercises the exact same redaction logic
   it would on real data — proving the pipeline works, on safe data.
3. **Two layouts.**
   - *Standard* (7 offers): a flowing letter, like a normal e-mailed offer.
   - *Tricky two-column* (3 offers): a two-column header (customer left,
     vendor right) + a metadata row + a position table. This mirrors the
     real-world layout that breaks naive text extraction and is the reason
     the vision path exists.

Output
------
One PDF per offer, written next to this script (``sample_pdfs/``), named
``Angebot_<ID>_<date>.pdf`` (e.g. ``Angebot_AG1001_12.03.2024.pdf``).

Reproducible: the data is hard-coded (no randomness), so re-running always
produces byte-identical content.

Usage
-----
    python generate_sample_pdfs.py
"""

from __future__ import annotations

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- #
# Fictitious vendor (consistent across all offers so the index is coherent)
# --------------------------------------------------------------------------- #
VENDOR = {
    "name": "Jonas Berger",
    "tagline": "Post-Production · Color · Sound",
    "address": "Lindenstraße 42, 20359 Hamburg",
    "phone": "+49 40 1234567",
    "email": "jonas@berger-post.de",
    "web": "www.berger-post.de",
    "iban": "DE00 1234 5678 0000 0000 01",
    "bic": "TESTDEFFXXX",
    "ust_id": "DE000000001",
    "steuer_nr": "00/000/00000",
}

# --------------------------------------------------------------------------- #
# Offer data. Each offer is a dict. ``layout`` is "standard" or "twocol".
# Line items: (pos, bezeichnung, menge, einheit, einzelpreis, gesamt)
# --------------------------------------------------------------------------- #
OFFERS = [
    # ---- Standard layout (flowing letter) -------------------------------- #
    {
        "id": "AG1001",
        "layout": "standard",
        "date": "12.03.2024",
        "valid_until": "12.04.2024",
        "customer": {
            "name": "Filmstudio Nord GmbH",
            "contact": "Frau Sabine Krüger",
            "email": "sabine.krueger@filmstudionord.de",
            "phone": "+49 40 8823456",
            "address": "Speicherstadt 7, 20457 Hamburg",
        },
        "project": 'Webserie "Hafenkante" — Staffel 2, 6 Folgen',
        "items": [
            (1, "Color Grading, 6 x 42 Min, Rec.709, DaVinci Resolve", 1, "Festpreis", "4.200,00", "4.200,00"),
            (2, "Online & Finishing (ProRes 422 HQ, 1080p H.264)", 6, "Folge", "150,00", "900,00"),
            (3, "Sound-Mix (Stereo, 5.1), 6 Folgen", 6, "Folge", "380,00", "2.280,00"),
        ],
        "total": "7.380,00",
        "terms": "50 % Anzahlung bei Auftragserteilung, 50 % bei Abnahme. Zahlungsziel: 30 Tage netto.",
    },
    {
        "id": "AG1002",
        "layout": "standard",
        "date": "08.07.2024",
        "valid_until": "22.07.2024",
        "customer": {
            "name": "TransLog AG",
            "contact": "Herr Peter Brandt",
            "email": "p.brandt@translog-ag.de",
            "phone": "+49 40 5566778",
            "address": "Hafenweg 12, 20457 Hamburg",
        },
        "project": 'Imagefilm "Zukunft Logistik" (ca. 3:30 Min, 4K, 25 fps)',
        "items": [
            (1, "Schnitt & Feinschnitt", 3, "Tag", "950,00", "2.850,00"),
            (2, "Color Grading (DaVinci Resolve, 4K)", 1, "Tag", "950,00", "950,00"),
            (3, "Motion Graphics / Titel", 2, "Sequenz", "700,00", "1.400,00"),
            (4, "Mastering: ProRes 4444 + H.264 4K", 1, "Festpreis", "450,00", "450,00"),
        ],
        "total": "5.650,00",
        "terms": "40 % bei Vertragsunterzeichnung, 60 % nach finaler Abnahme. Zahlungsziel 14 Tage.",
    },
    {
        "id": "AG1003",
        "layout": "standard",
        "date": "14.01.2025",
        "valid_until": "13.02.2025",
        "customer": {
            "name": 'Streaming-Plattform "Kanal9"',
            "contact": "Frau Julia Weber",
            "email": "julia.weber@kanal9.tv",
            "phone": "+49 30 4455667",
            "address": "Mediastraße 3, 10115 Berlin",
        },
        "project": 'Dokumentation "Zwischen den Zeilen" (52 Min, 4K)',
        "items": [
            (1, "Paket A — Schnitt (ca. 18 h Rohmaterial)", 1, "Festpreis", "9.500,00", "9.500,00"),
            (2, "Paket B — Color, Primary + Secondary, 4K", 1, "Festpreis", "3.800,00", "3.800,00"),
            (3, "Paket C — Sound & Mix, 5.1, -27 LUFS", 1, "Festpreis", "4.200,00", "4.200,00"),
            (4, "Paket D — Delivery, ProRes 4444 XQ, DCP, DE/EN", 1, "Festpreis", "1.800,00", "1.800,00"),
        ],
        "total": "19.300,00",
        "terms": "Meilenstein-Zahlung: 30 % bei Start, 40 % nach Grading-Freigabe, 30 % bei Delivery. 30 Tage netto.",
    },
    {
        "id": "AG1004",
        "layout": "standard",
        "date": "02.04.2025",
        "valid_until": "02.05.2025",
        "customer": {
            "name": "NordBank AG",
            "contact": "Frau Anna Lindner",
            "email": "a.lindner@nordbank-ex.de",
            "phone": "+49 40 2211334",
            "address": "Bankenviertel 1, 20095 Hamburg",
        },
        "project": "Social-Media-Cutdowns Q2 (8 x 30 s aus Hauptfilm, 2 Min)",
        "items": [
            (1, "Cutdown 30 s, inkl. Titel + Musik-Lizenz-Check, 9:16 + 1:1", 8, "Stück", "290,00", "2.320,00"),
        ],
        "total": "2.320,00",
        "terms": "Zahlung per Rechnung, 14 Tage. Frist: 2 Wochen nach Materialübergabe.",
    },
    {
        "id": "AG1005",
        "layout": "standard",
        "date": "03.05.2025",
        "valid_until": "03.06.2025",
        "customer": {
            "name": 'Theater Ensemble "Bühne Frei" e.V.',
            "contact": "Herr Dr. Markus Hoffmann",
            "email": "m.hoffmann@buehne-frei.org",
            "phone": "+49 351 998877",
            "address": "Kulturhof 5, 01067 Dresden",
        },
        "project": "Rahmenvertrag Post-Production (Aufführungs-Videos, Promo, Livestream)",
        "items": [
            (1, "Schnitt / Editing", 1, "Std.", "95,00", "95,00"),
            (2, "Color Grading", 1, "Std.", "110,00", "110,00"),
            (3, "Sound-Mix (Stereo)", 1, "Std.", "85,00", "85,00"),
            (4, "Sound-Mix (5.1)", 1, "Std.", "105,00", "105,00"),
            (5, "Motion Graphics", 1, "Std.", "120,00", "120,00"),
            (6, "Projektmanagement / Abstimmung", 1, "Std.", "80,00", "80,00"),
        ],
        "total": "Stundensätze (netto), Mindestaufwand 4 h pro Beauftragung",
        "terms": "Abrechnung monatlich, Sammelrechnung zum Monatsende. 30 Tage netto. Laufzeit 01.06.2025 – 31.05.2026.",
    },
    {
        "id": "AG1006",
        "layout": "standard",
        "date": "21.09.2025",
        "valid_until": "21.10.2025",
        "customer": {
            "name": "GreenWave Energy SE",
            "contact": "Herr Thomas Reuter",
            "email": "t.reuter@greenwave-energy.de",
            "phone": "+49 89 7766554",
            "address": "Energiepark 9, 80939 München",
        },
        "project": 'Corporate Video "Wind von Morgen" (ca. 4 Min, 4K)',
        "items": [
            (1, "Schnitt & Feinschnitt", 4, "Tag", "950,00", "3.800,00"),
            (2, "Color Grading, 4K, DaVinci Resolve", 2, "Tag", "950,00", "1.900,00"),
            (3, "Sounddesign & 5.1-Mix", 2, "Tag", "850,00", "1.700,00"),
            (4, "Mastering + Social-Cutdowns (3 x 30 s)", 1, "Festpreis", "900,00", "900,00"),
        ],
        "total": "8.300,00",
        "terms": "50 % Anzahlung, 50 % bei Abnahme. Zahlungsziel 30 Tage netto.",
    },
    {
        "id": "AG1007",
        "layout": "standard",
        "date": "10.11.2025",
        "valid_until": "10.12.2025",
        "customer": {
            "name": "Museum der Moderne",
            "contact": "Frau Dr. Elena Fischer",
            "email": "e.fischer@museum-moderne.de",
            "phone": "+49 821 334455",
            "address": "Kunsthalle 1, 80331 München",
        },
        "project": 'Ausstellungs-Film "Licht und Form" (ca. 8 Min, 4K, Loop)',
        "items": [
            (1, "Schnitt & Feinschnitt", 5, "Tag", "950,00", "4.750,00"),
            (2, "Color Grading, 4K, DaVinci Resolve Studio", 3, "Tag", "950,00", "2.850,00"),
            (3, "Motion Graphics / Titel & Infografiken", 3, "Tag", "1.100,00", "3.300,00"),
            (4, "Mastering, ProRes 4444 XQ + H.264 4K", 1, "Festpreis", "600,00", "600,00"),
        ],
        "total": "11.500,00",
        "terms": "Meilenstein-Zahlung: 40 % bei Start, 60 % bei Delivery. 30 Tage netto.",
    },
    # ---- Tricky two-column layout (customer left / vendor right) --------- #
    {
        "id": "AG1008",
        "layout": "twocol",
        "date": "16.09.2024",
        "valid_until": "26.09.2024",
        "customer": {
            "name": "Harbor & Co. GbR",
            "contact": "Herr Felix Wagner",
            "email": "f.wagner@harbor-co.de",
            "phone": "+49 431 223344",
            "address": "Werftbahnstraße 8, 24143 Kiel",
        },
        "project": "Imagefilm für Hafenlogistik (ca. 2:30 Min, 4K)",
        "items": [
            (1, "Honorar Kameramann (ohne Equipment)", 1, "Tag", "550,00", "550,00"),
            (2, "Honorar Colorist (Farbkorrektur & Grade)", 1, "Tag", "550,00", "550,00"),
            (3, "Schnitt & Feinschnitt", 2, "Tag", "950,00", "1.900,00"),
            (4, "Sound-Mix (Stereo)", 1, "Tag", "850,00", "850,00"),
        ],
        "total": "3.850,00",
        "terms": "50 % Anzahlung, 50 % bei Abnahme. Zahlungsziel 30 Tage netto.",
    },
    {
        "id": "AG1009",
        "layout": "twocol",
        "date": "05.02.2025",
        "valid_until": "15.02.2025",
        "customer": {
            "name": "Alster Media GmbH",
            "contact": "Frau Nina Petersen",
            "email": "n.petersen@alster-media.de",
            "phone": "+49 40 6677889",
            "address": "Alsterufer 21, 20095 Hamburg",
        },
        "project": 'Doku-Short "Stadt im Fluss" (ca. 12 Min, 4K)',
        "items": [
            (1, "Schnitt & Feinschnitt", 6, "Tag", "950,00", "5.700,00"),
            (2, "Color Grading, 4K", 3, "Tag", "950,00", "2.850,00"),
            (3, "Sounddesign & 5.1-Mix", 3, "Tag", "850,00", "2.550,00"),
            (4, "Mastering + Untertitel (DE/EN)", 1, "Festpreis", "700,00", "700,00"),
        ],
        "total": "11.800,00",
        "terms": "Meilenstein-Zahlung: 30 % bei Start, 40 % nach Grading, 30 % bei Delivery. 30 Tage netto.",
    },
    {
        "id": "AG1010",
        "layout": "twocol",
        "date": "28.06.2025",
        "valid_until": "08.07.2025",
        "customer": {
            "name": "Baltic Events UG",
            "contact": "Herr Jonas Meyer",
            "email": "j.meyer@baltic-events.de",
            "phone": "+49 451 556677",
            "address": "Strandpromenade 3, 23552 Lübeck",
        },
        "project": "Event-Recap & Livestream-Nachbearbeitung (Festival, 2 Tage)",
        "items": [
            (1, "Livestream-Regie & -Aufzeichnung", 2, "Tag", "1.200,00", "2.400,00"),
            (2, "Schneller Recap-Edit (60 s + 3 x 30 s)", 1, "Festpreis", "1.800,00", "1.800,00"),
            (3, "Color Grading, 4K", 2, "Tag", "950,00", "1.900,00"),
            (4, "Sound-Mix (Stereo)", 1, "Tag", "850,00", "850,00"),
        ],
        "total": "6.950,00",
        "terms": "50 % Anzahlung, 50 % bei Abnahme. Zahlungsziel 14 Tage.",
    },
]


# --------------------------------------------------------------------------- #
# Styles
# --------------------------------------------------------------------------- #
def _styles():
    base = getSampleStyleSheet()
    s = {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontSize=16, leading=20,
            spaceAfter=4, textColor=colors.HexColor("#1a1a1a"),
        ),
        "h": ParagraphStyle(
            "h", parent=base["Heading2"], fontSize=11, leading=14,
            spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#333333"),
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontSize=10, leading=14,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"], fontSize=8.5, leading=11,
            textColor=colors.HexColor("#555555"),
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["BodyText"], fontSize=9, leading=12,
        ),
    }
    return s


def _vendor_block(st):
    """Vendor contact block (used in both layouts)."""
    lines = [
        f"<b>{VENDOR['name']}</b>",
        VENDOR["tagline"],
        VENDOR["address"],
        f"Telefon: {VENDOR['phone']}",
        f"MAIL: {VENDOR['email']}",
        f"WEB: {VENDOR['web']}",
        f"USt-IdNr.: {VENDOR['ust_id']}",
        f"Steuernummer: {VENDOR['steuer_nr']}",
        f"IBAN: {VENDOR['iban']} · BIC: {VENDOR['bic']}",
    ]
    return Paragraph("<br/>".join(lines), st["small"])


def _customer_block(c, st):
    lines = [
        f"<b>{c['name']}</b>",
        f"z. Hd. {c['contact']}",
        c["address"],
        c["email"],
        f"Tel: {c['phone']}",
    ]
    return Paragraph("<br/>".join(lines), st["small"])


def _position_table(items, st):
    header = ["Pos.", "Bezeichnung", "Menge", "Einheit", "Einzel €", "Gesamt €"]
    data = [header]
    for pos, bez, menge, einheit, einz, gesamt in items:
        data.append([str(pos), bez, str(menge), einheit, einz, gesamt])
    t = Table(data, colWidths=[14 * mm, 86 * mm, 16 * mm, 20 * mm, 24 * mm, 24 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


# --------------------------------------------------------------------------- #
# Layout builders
# --------------------------------------------------------------------------- #
def build_standard(offer, out_path):
    st = _styles()
    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"Angebot {offer['id']}", author=VENDOR["name"],
    )
    c = offer["customer"]
    story = []
    story.append(Paragraph(f"ANGEBOT Nr. {offer['id']}", st["title"]))
    story.append(Spacer(1, 6 * mm))

    # Customer / vendor as a two-cell row (still reads as a letter header)
    hdr = Table(
        [[_customer_block(c, st), _vendor_block(st)]],
        colWidths=[80 * mm, 80 * mm],
    )
    hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph(
        f"<b>Datum:</b> {offer['date']} &nbsp;&nbsp; "
        f"<b>Gültig bis:</b> {offer['valid_until']}", st["body"]))
    story.append(Paragraph(f"<b>Projekt:</b> {offer['project']}", st["body"]))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("LEISTUNGEN", st["h"]))
    story.append(_position_table(offer["items"], st))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        f"<b>GESAMT: {offer['total']} EUR</b> zzgl. 19 % MwSt.", st["body"]))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("ZAHLUNGSBEDINGUNGEN", st["h"]))
    story.append(Paragraph(offer["terms"], st["body"]))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Mit freundlichen Grüßen<br/>" + VENDOR["name"], st["body"]))

    doc.build(story)


def build_twocol(offer, out_path):
    """Two-column header (customer left / vendor right) + metadata row +
    position table — mirrors the real-world layout that breaks naive
    extraction (the AG0006 failure mode)."""
    st = _styles()
    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Kostenvoranschlag {offer['id']}", author=VENDOR["name"],
    )
    c = offer["customer"]
    story = []

    # Two-column header: customer LEFT, vendor RIGHT.
    hdr = Table(
        [[_customer_block(c, st), _vendor_block(st)]],
        colWidths=[82 * mm, 82 * mm],
    )
    hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Kostenvoranschlag", st["title"]))
    story.append(Paragraph("Gerne bieten wir Ihnen an:", st["body"]))
    story.append(Spacer(1, 3 * mm))

    # Metadata row (Angebotsnr / Kundennr / Datum / gültig bis)
    meta = Table(
        [
            ["Angebotsnr.:", "Kundennr.:", "Datum:", "gültig bis:"],
            [offer["id"], "10001", offer["date"], offer["valid_until"]],
        ],
        colWidths=[45 * mm, 45 * mm, 45 * mm, 45 * mm],
    )
    meta.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(meta)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(f"<b>Projekt:</b> {offer['project']}", st["body"]))
    story.append(Spacer(1, 3 * mm))
    story.append(_position_table(offer["items"], st))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        f"<b>GESAMT: {offer['total']} EUR</b> zzgl. 19 % MwSt.", st["body"]))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("BEDINGUNGEN", st["h"]))
    story.append(Paragraph(offer["terms"], st["body"]))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Jonas Berger — Post-Production", st["small"]))

    doc.build(story)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    builders = {"standard": build_standard, "twocol": build_twocol}
    print(f"Generating {len(OFFERS)} fictitious offer PDFs into: {HERE}\n")
    for offer in OFFERS:
        out = os.path.join(HERE, f"Angebot_{offer['id']}_{offer['date']}.pdf")
        builders[offer["layout"]](offer, out)
        print(f"  [{offer['layout']:>8}] {offer['id']}  ->  {os.path.basename(out)}")
    print(f"\nDone. {len(OFFERS)} PDFs written.")


if __name__ == "__main__":
    main()
