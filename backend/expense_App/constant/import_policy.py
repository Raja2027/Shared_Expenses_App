from datetime import date
from decimal import Decimal


DEFAULT_YEAR = 2026

EXPECTED_COLUMNS = [
    "date",
    "description",
    "paid_by",
    "amount",
    "currency",
    "split_type",
    "split_with",
    "split_details",
    "notes",
]

SUPPORTED_SPLIT_TYPES = {"equal", "unequal", "percentage", "share"}

FX_RATES_TO_INR = {
    "INR": Decimal("1.00"),
    "USD": Decimal("83.00"),
}

PERSON_ALIASES = {
    "aisha": "Aisha",
    "rohan": "Rohan",
    "priya": "Priya",
    "priya s": "Priya",
    "meera": "Meera",
    "dev": "Dev",
    "sam": "Sam",
    "kabir": "Kabir",
    "devs friend kabir": "Kabir",
}

KNOWN_PEOPLE = set(PERSON_ALIASES.values())

MEMBERSHIP_WINDOWS = {
    "Aisha": (date(2026, 2, 1), None),
    "Rohan": (date(2026, 2, 1), None),
    "Priya": (date(2026, 2, 1), None),
    "Meera": (date(2026, 2, 1), date(2026, 3, 31)),
    "Sam": (date(2026, 4, 8), None),
}

REVIEW_NOTE_TERMS = [
    "wrong",
    "oops",
    "forgot",
    "cant remember",
    "not expense",
    "counted twice",
    "format is a mess",
    "percentages might be off",
    "i think",
    "is this",
    "fixing later",
]

SETTLEMENT_TERMS = [
    "paid back",
    "settlement",
    "deposit share",
    "paid aisha his deposit",
]
