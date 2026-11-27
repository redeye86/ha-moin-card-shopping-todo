# Protokoll / API-Referenz

Basis-URL: `https://www.moincard.de`

Alle Endpunkte wurden aus `libapp.so` (Flutter/Dart-AOT) rekonstruiert und live
gegen die echte API verifiziert.

## Header

| Header | Wert | Wann |
| --- | --- | --- |
| `x-api-key` | `jsdirjgldd4453ldsjkfjfkeiweucxhjskdldoe` | immer |
| `accept` | `application/json` | immer |
| `content-type` | `application/json; charset=utf-8` | bei Body |
| `x-auth-token` | Token aus `/api/login` | alles außer Login |

Das ist exakt das, was `JsonClient._addHeaders` in der App setzt. Für
Scan-&-Go-Requests setzt die App zusätzlich `X-Shopper-Identifier`.

## Datenmodelle

### ShoppingList (Übersicht)

```json
{
  "id": 306336,
  "name": "Einkaufsliste",
  "internalId": "948ff9fa3096ca35bee014a0270ebaa7",
  "created": "2026-11-27 10:23:10",
  "lastModified": "2026-11-27 10:23:10"
}
```

- `id`: **numerisch** (wird im Item-Feld `shoppingListId` verwendet)
- `internalId`: **Hex-String** (wird im Request-Body `internalId` verwendet)

### ShoppingListItem

```json
{
  "id": 388314,
  "shoppingListId": 306336,
  "name": "Milch",
  "unit": null,
  "done": false,
  "sku": null,
  "selfCreated": true,
  "category": "Frische, Milchprodukte",
  "quantity": 1,
  "imageUrl": null,
  "gtin": null,
  "lastModified": "2026-11-27 10:23:17"
}
```

Feld-Bedeutung (Reihenfolge/Felder aus `ShoppingListItem.toJson`):

| Feld | Typ | Bedeutung |
| --- | --- | --- |
| `id` | int | Item-ID; `0` = neuer Artikel |
| `shoppingListId` | int | numerische Listen-`id` |
| `name` | string | Artikelname |
| `unit` | string? | Einheit |
| `done` | bool | abgehakt |
| `sku` | string? | Händler-SKU |
| `selfCreated` | bool | frei eingetragen (statt Standard/Vorschlag) |
| `category` | string? | Kategorie |
| `quantity` | int | Menge |
| `imageUrl` | string? | Bild |
| `gtin` | string? | EAN/GTIN (für Scan-Matching) |
| `lastModified` | string | nur in Response |

### Antwortform für Listen-Operationen

`list`, `create` und alle Item-Mutationen liefern:

```json
{ "shoppingList": { ... }, "shoppingListItems": [ ... ] }
```

## Endpunkte

### Login

```
POST /api/login
Body:  {"username": "<email>", "password": "<passwort>"}
200:   {"username": "...", "token": "...", "roles": ["ROLE_USER","ROLE_API"], "cardNumber": "..."}
401:   {"error": "Fehlerhafte Zugangsdaten."}
```

Der `token` wird als `x-auth-token` weiterverwendet.

### Kunde

```
GET  /api/customer            -> {customer...}   (404 [] wenn keiner existiert)
POST /api/customer            -> legt Kunde an / aktualisiert
GET  /api/customer/loyaltystatus
GET  /api/portal/shops        -> Liste der Märkte (id, city, zipcode, ...)
```

`POST /api/customer` Pflichtfelder (sonst 400 mit `Validation Failed`):
`salutation` (int, `0` = Herr), `name`, `firstName`, `street`, `streetNumber`,
`postal`, `city`, `dateOfBirth` (`dd.MM.yyyy`), `domesticMarket` (Markt-`id`),
`email`. → siehe [konto-einrichtung.md](konto-einrichtung.md).

### Einkaufslisten

```
GET    /api/shoppinglist/lists                      -> [ ShoppingList, ... ]
POST   /api/shoppinglist/list    {"internalId"}     -> {shoppingList, shoppingListItems}
POST   /api/shoppinglist/create  {"id":0,"name"}    -> {shoppingList, shoppingListItems}
POST   /api/shoppinglist/update  {"internalId","id","name"}   (umbenennen)
DELETE /api/shoppinglist/delete?internalId=<internalId>
```

### Artikel

```
POST   /api/shoppinglist/item/update
       {"internalId": "<hex>", "shoppingListItem": {...}, "addQuantity": <int>}

POST   /api/shoppinglist/item/done
       {"internalId": "<hex>", "shoppingListItem": {...}, "done": <bool>}

DELETE /api/shoppinglist/item/delete?internalId=<hex>&itemId=<id>
DELETE /api/shoppinglist/item/deleteAll?internalId=<hex>
```

#### `addQuantity`-Semantik (wichtig!)

Das Feld `quantity` **im Body** ist kein Zielwert, sondern die *erwartete
aktuelle* Menge (optimistisches Locking). `addQuantity` ist das **Delta**:

```
neue Menge = erwartete aktuelle Menge (quantity) + addQuantity
```

- **Neuer Artikel** (`id: 0`): das Serverergebnis ist `addQuantity`
  (die `quantity` im Body wird ignoriert).
- **Bestehender Artikel**: `quantity` **muss** der aktuellen Server-Menge
  entsprechen, sonst **HTTP 409**. Zielmenge → `addQuantity = ziel - aktuell`.
- Nur Name/Kategorie ändern → `quantity = aktuell`, `addQuantity = 0`.
- `item/done` prüft ebenfalls die `quantity` gegen den aktuellen Wert (sonst 409).

Beispiele (alle verifiziert):

```
# Neuer Artikel, Menge 6
{"shoppingListItem": {"id":0, ..., "quantity":6}, "addQuantity":6}      -> quantity 6

# Bestehend (aktuell 6) auf 9 setzen
{"shoppingListItem": {"id":<id>, ..., "quantity":6}, "addQuantity":3}   -> quantity 9

# Bestehend (aktuell 9), nur umbenennen
{"shoppingListItem": {"id":<id>, ..., "quantity":9}, "addQuantity":0}   -> quantity 9
```

### Vokabular (Vorschläge)

```
GET  /api/shoppinglist/vocabulary/list          -> [ {id,name,category,selfCreated}, ... ]
GET  /api/shoppinglist/vocabulary/standardlist  -> Standardliste (326 Einträge)
POST /api/shoppinglist/vocabulary/create        {"name","category","selfCreated"}
POST /api/shoppinglist/vocabulary/update
```

`vocabulary/list` = Standardliste + persönlich angelegte Einträge.

### Angebote / Coupons

```
GET /api/portal/coupons   -> {"evrCoupons": [ {evrId,title,shortDescription,image,...} ]}
```

## Fehler

| Code | Bedeutung |
| --- | --- |
| 400 | Validation fehlgeschlagen (JSON `{"detail": "..."}`) |
| 401 | Login fehlgeschlagen (`{"error": "Fehlerhafte Zugangsdaten."}`) |
| 403 | Token ungültig (`{"message": "Invalid credentials."}`) |
| 404 | u. a. `{"message":"Kunde nicht gefunden."}` wenn kein Kunden-Datensatz existiert |
| 409 | Konflikt beim `item/update` / `item/done` (stale `quantity`) |
| 500 | Serverfehler (in der Praxis gelegentlich transient) |

## Verifizierte Live-Kette

```
login -> get_lists -> get_list -> add_item(category+gtin) -> update(6->9)
      -> rename -> set_done -> delete
```

Ergebnis: siehe `moin_list.py` (PoC) und `custom_components/moincard/api.py`.
