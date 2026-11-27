# MOIN CARD – Dokumentation

Diese Sammlung beschreibt alles, was bei der Analyse der **MOIN CARD App**
(`de.buenting.moincard`) und beim Bau der Home-Assistant-Integration
herauskam.

| Dokument | Inhalt |
| --- | --- |
| [protokoll.md](protokoll.md) | Komplette Reverse-Engineered HTTP-API (Endpunkte, Header, Payloads, Semantik, Fehler) |
| [analyse.md](analyse.md) | Wie die App dekompiliert wurde (Flutter/Dart, blutter, Toolchain) |
| [scan-und-abhaken.md](scan-und-abhaken.md) | Scan-Features, Cart-Abgleich und das Abhaken per EAN |
| [produkte-und-vokabular.md](produkte-und-vokabular.md) | Woher Produkte/Namen/Kategorien/EAN/Preise kommen |
| [konto-einrichtung.md](konto-einrichtung.md) | Kunden-Datensatz anlegen (nötig für die Einkaufsliste) |
| [home-assistant.md](home-assistant.md) | Architektur + Verhalten der HA-Integration |
| [dashboard-card.md](dashboard-card.md) | Fertige Dashboard-Card, Helper, Scripts & Automationen |
| [erkenntnisse.md](erkenntnisse.md) | Kurz-Zusammenfassung, Stolperfallen, Grenzen |

## Kurzfassung

- Die Einkaufsliste ist **serverseitig** und wird über `https://www.moincard.de/api/...`
  synchronisiert (Header `x-api-key` + `x-auth-token`).
- Ein Artikel hat u. a. `name`, `quantity`, `category`, `gtin` (EAN), `sku`, `done`.
- Das **Vokabular** (Vorschläge) sind nur Namen + Kategorien (326 Standard-Einträge),
  **keine** EAN/Preise. EAN/Preis gibt es nur über Barcode-Lookup (mytime.de /
  OpenGTINDB) bzw. Angebote.
- Beim Scan & Go wird ein Artikel über die **GTIN/EAN** abgehakt – ein generisches
  „Bier" wird *nicht* durch eine Krombacher-Flasche abgehakt.
- Die HA-Integration nutzt ein `todo`-Entity je Liste, setzt die Kategorie
  automatisch aus dem Vokabular und kann optional eine EAN mitschicken.

> ⚠️ Inoffiziell, ohne Verbindung zu Bünting/MOIN CARD. Interne API, kann sich
> jederzeit ändern. Nutzung auf eigene Verantwortung.
