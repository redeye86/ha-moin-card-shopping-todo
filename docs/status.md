# Status & Übergabe

Stand: siehe letzter Commit auf `main`.

Repo: https://github.com/redeye86/ha-moin-card-shopping-todo
(`git@github.com:redeye86/ha-moin-card-shopping-todo.git`)

## Fertig

- **HA-Integration `custom_components/moincard/`**
  - Config-Flow (Login/Reauth/Options), Coordinator-Polling, Re-Login bei 401/403.
  - `todo`-Entity je Einkaufsliste (Menge als `Nx`, Kategorie-Autofill aus dem
    Vokabular, EAN via Beschreibung/Service).
  - **Read-only `todo.moin_card_vokabular`** – Produktkatalog für Sprach-/LLM-Agenten.
  - Service `moincard.add_item` (Name, Menge, EAN, Kategorie, Einheit, Liste).
  - 11 Tests grün, ruff clean (HA 2026.2.3).
- **PoC `moin_list.py`** inkl. `vocab`-Export.
- **`data/`**: `vocabulary.csv`, `vocabulary.json`, `vocabulary_names.txt` (326 Einträge).
- **`docs/`**: Protokoll, App-Analyse, Scan/Abbaken, Produkte/Vokabular,
  Konto-Einrichtung, HA-Integration, Dashboard-Card, Sprachassistent,
  Vokabular-Export, Erkenntnisse, index.

## Offen / nächste Ideen

1. **`moincard.match_item`-Service** (Text rein → bester Vokabular-Treffer als
   Response) + **`only_known`-Flag** an `add_item`, damit der Abgleich
   deterministisch in HA läuft (Agent ruft nur den Service).
2. **Produkt-/EAN-Autofill** per Name (mytime.de/OpenGTINDB), damit Freitext-
   Artikel eine `gtin` bekommen und beim Scan abhaken.
3. **Override-Liste** (spoken → kanonisch) – Muster wie Store-Zuordnung,
   ggf. als eigener Helper/Service kapseln.
4. Optional: `sensor` „offene Artikel", Kategorie-Auswahl im Options-Flow,
   `MOVE`-Support.

## Hinweise / Zustand

- **Testaccount** `redeyeschulte@googlemail.com` hat jetzt einen Kunden-Datensatz
  (Testdaten) und eine Liste „Einkaufsliste" mit Demo-/Testartikeln
  (`Milch`, `Brot`, `Eier`, `Kaffee`, `Butter`, `SemantikNEU`, `NeuTest2`, …).
  → aufräumen, wenn gewünscht.
- Die `MOIN-CARD_*.xapk` ist per `.gitignore` **nicht** im Repo.
- Git-Identität lokal: `redeye86 <redeye86@users.noreply.github.com>`.
- AddQuantity-Semantik beachten (siehe [protokoll.md](protokoll.md)) – die
  HA-Integration behandelt das automatisch.

## Wichtige API-Fakten (Kurz)

- Basis `https://www.moincard.de`, Header `x-api-key` + `x-auth-token`.
- Liste hat numerische `id` **und** Hex-`internalId` (nicht verwechseln).
- `item/update`: Body-`quantity` = **aktuelle** Menge (sonst 409),
  `addQuantity` = **Delta**; neue Items: `addQuantity` = Zielmenge.
- Scan-Abhaken läuft über **GTIN/EAN**, nicht über die Kategorie.
