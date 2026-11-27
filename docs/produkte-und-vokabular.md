# Produkte, Vokabular, EAN & Preise

Kurz: Die **Vorschlagsliste sind nur Namen + Kategorien**. Konkrete Produkte
mit **EAN/Preis** kommen aus anderen Quellen.

## Vokabular (Vorschläge / Autovervollständigung)

- `GET /api/shoppinglist/vocabulary/standardlist` → **326 Einträge**, 15 Kategorien.
- `GET /api/shoppinglist/vocabulary/list` → Standardliste **+** selbst angelegte
  Einträge (`selfCreated: true`).
- Zusätzlich als App-Asset gebündelt (Offline-Fallback):
  `assets/flutter_assets/assets/data/shoppinglistcache.json` (329 Einträge).

Eintrag:

```json
{ "id": 240, "category": "Alkohol", "name": "Bier", "selfCreated": false }
```

→ **kein EAN, kein Preis.** Nur Name + Kategorie.

Kategorien (15): `Alkohol`, `Backwaren`, `Fleisch, Fisch`,
`Frische, Milchprodukte`, `Getreideprodukte`, `Getränke`, `Haushalt`,
`Kaffee, Tee & Kakao`, `Koch-, Backzutaten`, `Konserven`, `Obst & Gemüse`,
`Pflege & Gesundheit`, `Süßwaren, Snacks`, `Tiefkühlprodukte`, `Tierbedarf`.

Wenn in der App ein **neuer Name** eingetippt wird, legt die App ihn im
persönlichen Vokabular an (`POST /api/shoppinglist/vocabulary/create`,
`selfCreated: true`) – siehe `addNameToShoppingListCache`.

## Konkrete Produkte (mit EAN/Preis)

### mytime.de Produkt-API

```
GET https://www.mytime.de/api/v1/mobile/product?product_gtin=<EAN>
```

Liefert u. a.:

- `productbasic`: `ean`, `sku`, `name`, `price`, `old_price`, `singlePrice`,
  `lowestPrice`, `bulk_price`, `deposit`, `weight`, `by_weight`, `cold`, `frozen`,
  `tierPrices`
- `tierPrices[]`: `price`, `grossPrice`, `netPrice`, `basePrice`, `currency`,
  `quantityFrom`, `taxRate`, ...
- `images[]`, `categoryName`, `description`

→ echte Produktdaten **inkl. EAN und Preis**, abgefragt per EAN.

### OpenGTINDB (Fallback)

```
GET https://opengtindb.org/?ean=<EAN>&cmd=query&queryid=017071973
```

Öffentliche EAN-Datenbank; wird in `getOpenGtinProduct` als Fallback benutzt.

### Angebote / Coupons

```
GET /api/portal/coupons
```

Liefert `evrCoupons[]` mit `evrId`, `title`, `shortDescription` (z. B.
„20-580-g-Beutel"), `image`, Gültigkeit. Das vollständige Offer-Modell kennt
zusätzlich Preis-Felder (`loyaltyprice`, `specialprice`, `loyaltypriceUnit`,
`specialpriceUnit`), `brand`, `image`, `evr*` je Stufe.

## Shopping-List-Item vs. Vokabular

Das **Item** hat ein `gtin`-Feld (EAN). Beim Scannen wird der Barcode direkt
hineingeschrieben (`addBarcodeToShoppingList` setzt `gtin` = Barcode). Ein
Frei-Text-Artikel hat `gtin/sku/imageUrl = null`.

| Quelle | Name | Kategorie | EAN | Preis |
| --- | --- | --- | --- | --- |
| Vokabular/Standardliste | ✅ | ✅ | ❌ | ❌ |
| Item (Freitext) | ✅ | (aus Vokabular) | ❌ | ❌ |
| Item (per Scan übernommen) | ✅ | ✅ | ✅ | ❌ |
| mytime-Produkt | ✅ | ✅ | ✅ | ✅ |
| Angebot/Coupon | ✅ | – | (`evr*`) | ✅ |

**Fazit:** Für „echte" Produkte mit EAN/Preis muss man den Barcode scannen
(→ mytime/OpenGTINDB) oder ein Angebot übernehmen. Die Einkaufslisten-Vorschläge
selbst sind reine Namen.
