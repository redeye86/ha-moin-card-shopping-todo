"""Constants for the MOIN CARD integration."""

from __future__ import annotations

DOMAIN = "moincard"
NAME = "MOIN CARD"

# Reverse-engineered from the Android app de.buenting.moincard 2.28.1 (Flutter/Dart 3.13.4).
BASE_URL = "https://www.moincard.de"
API_KEY = "jsdirjgldd4453ldsjkfjfkeiweucxhjskdldoe"

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 300  # seconds
MIN_SCAN_INTERVAL = 30

DEFAULT_LIST_NAME = "Einkaufsliste"

MANUFACTURER = "Bünting / MOIN CARD"

# todo item description tokens:  "gtin:4008165000016  category:Getränke  unit:Flasche"
TOKEN_GTIN = ("gtin", "ean")
TOKEN_CATEGORY = ("category", "kategorie")
TOKEN_UNIT = ("unit", "einheit")
