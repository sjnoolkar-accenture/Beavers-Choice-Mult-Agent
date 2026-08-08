"""Business catalog and deterministic parsing constants."""

from __future__ import annotations

import re

INITIAL_DATE = "2025-01-01"
STARTING_CASH_CENTS = 5_000_000

CATALOG = [
    ("A4 paper", "paper", 5, 1200, 300),
    ("A3 paper", "paper", 9, 700, 200),
    ("Letter-sized paper", "paper", 6, 900, 250),
    ("Cardstock", "paper", 15, 900, 200),
    ("Colored paper", "paper", 10, 800, 180),
    ("Glossy paper", "paper", 20, 850, 180),
    ("Matte paper", "paper", 18, 900, 180),
    ("Recycled paper", "paper", 8, 700, 160),
    ("Poster paper", "paper", 25, 700, 150),
    ("Construction paper", "paper", 7, 700, 150),
    ("Standard copy paper", "paper", 4, 1300, 300),
    ("Heavyweight paper", "paper", 20, 500, 120),
    ("Kraft paper", "paper", 10, 500, 120),
    ("Paper plates", "product", 10, 800, 180),
    ("Paper cups", "product", 8, 1200, 250),
    ("Paper napkins", "product", 2, 2400, 400),
    ("Envelopes", "product", 5, 700, 150),
    ("Flyers", "product", 15, 1200, 250),
    ("Party streamers", "product", 5, 600, 120),
    ("Decorative adhesive tape (washi tape)", "product", 20, 450, 100),
    ("Large poster paper (24x36 inches)", "large_format", 100, 350, 80),
]

HISTORICAL_QUOTES = [
    (
        "500 sheets of glossy paper and 300 sheets of cardstock",
        18_150,
        "Medium event order with a 5% volume discount.",
        "2024-11-10",
    ),
    (
        "1000 sheets of A4 paper and 500 sheets of colored paper",
        12_420,
        "Large school order with a 10% volume discount.",
        "2024-12-04",
    ),
    (
        "2000 sheets of poster paper",
        57_375,
        "Bulk poster order with a 15% volume discount.",
        "2024-12-18",
    ),
    (
        "500 sheets of cardstock",
        9_619,
        "Cardstock order with a 5% volume discount.",
        "2024-10-22",
    ),
]

ALIASES = {
    "a4": "A4 paper",
    "a4 paper": "A4 paper",
    "printer paper": "Standard copy paper",
    "printing paper": "Standard copy paper",
    "standard paper": "Standard copy paper",
    "white paper": "A4 paper",
    "a3": "A3 paper",
    "a3 paper": "A3 paper",
    "cardboard": "Cardstock",
    "cardstock": "Cardstock",
    "heavy cardstock": "Cardstock",
    "heavyweight cardstock": "Cardstock",
    "white cardstock": "Cardstock",
    "colored cardstock": "Cardstock",
    "recycled cardstock": "Cardstock",
    "colored paper": "Colored paper",
    "colorful paper": "Colored paper",
    "construction paper": "Construction paper",
    "glossy": "Glossy paper",
    "glossy paper": "Glossy paper",
    "matte": "Matte paper",
    "matte paper": "Matte paper",
    "recycled paper": "Recycled paper",
    "poster board": "Large poster paper (24x36 inches)",
    "poster boards": "Large poster paper (24x36 inches)",
    "poster paper": "Poster paper",
    "posters": "Poster paper",
    "kraft paper envelopes": "Envelopes",
    "envelopes": "Envelopes",
    "streamers": "Party streamers",
    "washi tape": "Decorative adhesive tape (washi tape)",
    "napkins": "Paper napkins",
    "paper napkins": "Paper napkins",
    "cups": "Paper cups",
    "paper cups": "Paper cups",
    "plates": "Paper plates",
    "paper plates": "Paper plates",
    "flyers": "Flyers",
}

QUALIFIERS = [
    ("washi", "Decorative adhesive tape (washi tape)"),
    ("streamer", "Party streamers"),
    ("napkin", "Paper napkins"),
    ("envelope", "Envelopes"),
    ("flyer", "Flyers"),
    ("cup", "Paper cups"),
    ("plate", "Paper plates"),
    ("cardstock", "Cardstock"),
    ("glossy", "Glossy paper"),
    ("matte", "Matte paper"),
    ("construction", "Construction paper"),
    ("recycled", "Recycled paper"),
    ("kraft", "Kraft paper"),
    ("poster board", "Large poster paper (24x36 inches)"),
    ("poster", "Poster paper"),
    ("colored", "Colored paper"),
    ("colorful", "Colored paper"),
]

ITEM_PATTERN = re.compile(
    r"(?P<quantity>\d[\d,]*)\s+"
    r"(?P<name>.*?)(?=(?:,\s*|\s+and\s+)\d[\d,]*\s+|[\n.;]|$)",
    re.IGNORECASE,
)

DUE_DATE_PATTERN = re.compile(
    r"(?:by|before|on)\s+"
    r"(?P<month>January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+"
    r"(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<year>\d{4})",
    re.IGNORECASE,
)
