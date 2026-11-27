# Erkenntnisse, Stolperfallen & offene Punkte

## Zentrale Erkenntnisse

1. **Die Einkaufsliste ist serverseitig** und komplett über die App-API
   (`https://www.moincard.de/api/shoppinglist/...`) les- und schreibbar – mit
   `x-api-key` + `x-auth-token`. Damit lässt sie sich von außen befüllen/abhaken.
2. **Zwei IDs pro Liste:** numerische `id` (→ Item-Feld `shoppingListId`) und
   Hex-`internalId` (→ Body-Feld `internalId`). Verwechslung = Fehler.
3. **`addQuantity` ist ein Delta**, und das `quantity`-Feld im Body ist die
   *erwartete aktuelle* Menge (sonst **409**). Neue Artikel nutzen `addQuantity`
   als Zielmenge.
4. **Das Vokabular sind nur Namen + Kategorien** – keine EAN/Preise.
   EAN/Preis kommen über mytime.de / OpenGTINDB (per Barcode) bzw. Angebote.
5. **Abhaken beim Scan läuft über die GTIN/EAN**, nicht über die Kategorie.
   „Krombacher" hakt also **nicht** „Bier" ab.
6. **Die Einkaufsliste braucht einen Kunden-Datensatz** (`POST /api/customer`),
   sonst 404 „Kunde nicht gefunden".

## Stolperfallen (aus der Praxis)

- **App ist Dart 3.13** → die aktuelle blutter-Version braucht PR #230, sonst
  `Cannot find Dart VM Snapshot Data` (unified Snapshot).
- **blutter-String-Bug:** im Decompile teils nur `"n"`/`"ln"` – Rohstrings im
  `libapp.so` gegenprüfen.
- **`salutation` muss int sein** (`0` = Herr). Ein String (`"Herr"`) → HTTP 500.
- **`dateOfBirth`** App-Format `dd.MM.yyyy`; `domesticMarket` = Markt-`id`.
- **`/api/*` gab zeitweise HTTP 500/Disconnect** (Server-seitig, transient);
  danach wieder normal. Retry/Refresh einplanen (macht die HA-Integration).
- **`addQuantity`-409** tritt auf, wenn die mitgeschickte `quantity` nicht der
  Server-Menge entspricht → immer den aktuellen Wert des Items senden.
- **Desktop-Link** `…/inapp/teile_einkaufsliste` zeigt nur „in der App öffnen";
  es ist ein reiner App-Link, kein Web-UI.

## Getestete Live-Kette

```
POST /api/login
GET  /api/shoppinglist/lists
POST /api/shoppinglist/list
POST /api/shoppinglist/item/update   (Kategorie + gtin + unit, Menge 6)
POST /api/shoppinglist/item/update   (Menge 6 -> 9)
POST /api/shoppinglist/item/update   (Umbenennen)
POST /api/shoppinglist/item/done
DELETE /api/shoppinglist/item/delete
```

Alle Schritte erfolgreich (siehe `moin_list.py`, `custom_components/moincard/api.py`).

## Noch offen / Ideen

- **Produktanreicherung:** per Namen ein Produkt/EAN suchen (mytime/OpenGTINDB)
  und automatisch `gtin` setzen, damit Scans auch für Freitext-Artikel matchen.
- **Mehrere Einkaufslisten** gezielt als Entity auswählbar machen (aktuell:
  eine Entity pro Liste, automatisch).
- **Kategorie-Auswahl / Vokabular-Verwaltung** im Options-Flow.
- **`sensor`** für „offene Artikel" / Anzahl.
- `/inapp/teile_einkaufsliste`-Flow testen (geteilte Listen importieren).

## Rechtliches

Inoffiziell, ohne Verbindung zu Bünting/MOIN CARD. Die API ist nicht öffentlich
dokumentiert und kann sich jederzeit ändern. Nutzung auf eigene Verantwortung;
Zugangsdaten werden im Klartext an die App-API gesendet (wie in der App selbst).
