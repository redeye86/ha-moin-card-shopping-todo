# Konto einrichten (Kunden-Datensatz)

Die Einkaufsliste hängt an einem **Kunden-Datensatz**, nicht nur am Login.
Ein reines Web-Portal-Konto (nur E-Mail/Passwort) liefert bei
`GET /api/shoppinglist/lists`:

```
404 {"message":"Kunde nicht gefunden."}
```

Erkennbar an `GET /api/customer` → `[]` bzw.
`GET /api/customer/loyaltystatus` → `"customerId": null, "cardnumber": null`.

In der App entsteht der Kunde über die Registrierung/Profildaten. Über die API
lässt er sich so anlegen:

## `POST /api/customer`

Pflichtfelder (Validierungsfehler kommen als `400 {"detail": "..."}`):

| Feld | Typ | Hinweis |
| --- | --- | --- |
| `salutation` | **int** | `0` = Herr (wird serverseitig z. B. zu `2` normalisiert) |
| `name` | string | Nachname |
| `firstName` | string | Vorname |
| `street` | string | Straße |
| `streetNumber` | string | Hausnummer |
| `postal` | string | PLZ |
| `city` | string | Ort |
| `dateOfBirth` | string | Format `dd.MM.yyyy` |
| `domesticMarket` | int | Markt-`id` aus `GET /api/portal/shops` |
| `email` | string | muss zur Anmeldung passen |

Beispiel:

```bash
curl -X POST https://www.moincard.de/api/customer \
  -H "x-api-key: jsdirjgldd4453ldsjkfjfkeiweucxhjskdldoe" \
  -H "accept: application/json" \
  -H "content-type: application/json; charset=utf-8" \
  -H "x-auth-token: <TOKEN>" \
  -d '{"salutation":0,"name":"Schulte","firstName":"Test",
       "street":"Teststrasse","streetNumber":"1","postal":"49624","city":"Loeningen",
       "dateOfBirth":"01.01.1990","domesticMarket":1250074,
       "email":"redeyeschulte@googlemail.com"}'
# -> 201 Created
```

Antwort (gekürzt):

```json
{
  "customerId": 618992,
  "salutation": 2,
  "name": "Schulte",
  "cardnumber": "9873204116607",   // digitale Karte wird vergeben
  "domesticMarket": 1250074,
  "email": "...",
  "registerSource": 2
}
```

Danach vorhanden:

- `GET /api/customer` → das Kundenobjekt
- `GET /api/shoppinglist/lists` → `[]` (noch keine Liste)

## Liste anlegen

```bash
curl -X POST https://www.moincard.de/api/shoppinglist/create \
  -H "x-auth-token: <TOKEN>" ... \
  -d '{"id":0,"name":"Einkaufsliste"}'
# -> {"shoppingList":{"id":306336,"internalId":"948f...","name":"Einkaufsliste"}, "shoppingListItems":[]}
```

## Reihenfolge

```
login
  -> (falls nötig) POST /api/customer        # Kunde anlegen
  -> POST /api/shoppinglist/create (id=0)    # Liste anlegen (falls keine existiert)
  -> POST /api/shoppinglist/item/update      # Artikel
```

## Hinweise

- `salutation` als **String** (z. B. `"Herr"`) führt zu **HTTP 500** – es muss
  eine **int** sein. Wertebereich: `0` gültig; `3+` → 400 („Bitte wählen Sie
  eine Anrede aus").
- `dateOfBirth` als ISO-Datum (`1990-01-01`) ist möglich, das App-Format ist
  aber `dd.MM.yyyy`.
- Ohne `domesticMarket` kein Anlegen (Markt-Pflicht).
