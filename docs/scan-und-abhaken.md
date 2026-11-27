# Scan-Features, Abhaken & Teilen

Es gibt **zwei** leicht zu verwechselnde Scan-Funktionen.

## 1. „Einkaufsliste scannen" (Liste befüllen)

Handler: `_onScanShoppingListBarcodeEvent` in `shoppinglist_bloc.dart`.

```
Barcode scannen
  -> getMytimeProductImmediate(barcode)   # mytime.de Produkt-API
  -> getOpenGtinProduct(barcode)          # Fallback: OpenGTINDB
  -> mapMyTimeCategory(product)           # Kategorie aus Produktdaten
  -> addProductToShoppingList(product)    # Artikel wird HINZUGEFÜGT
  # oder, wenn kein Produkt gefunden:
  -> addBarcodeToShoppingList(barcode)    # Barcode wird als Name eingetragen
```

Ergebnis: der gescannte Artikel landet **auf der Liste** (Name/Kategorie/`gtin`),
kein Abhaken. Bei unbekanntem Barcode wird der Barcode-String als Artikelname
genommen.

## 2. Scan & Go (Kasse) – hier wird abgehakt

Handler: `_onScanBarcodeEvent` in `shopping_bloc.dart`.

```
getMytimeProduct(barcode)          # Produkt nachschlagen
addBarcodeToCart(barcode)          # in den virtuellen Warenkorb
getCurrentShoppingList()
markShoppingListItemWithCartItem(cartItem)   # passenden Listeneintrag abhaken
```

`markShoppingListItemWithCartItem` sucht per `firstWhereOrNull` den ersten
Listeneintrag, dessen **`gtin`** (Feld `field_7` des `ShoppingListItem`) gleich
der Produkt-EAN des Cart-Items ist **und** der noch nicht abgehakt ist. Der
Predicate liegt in der Closure `0x5902a8` in `libapp.so` (dekompiliert).

Pseudo:

```dart
final match = list.items.firstWhereOrNull(
  (item) => item.gtin == cartItem.product.ean && !item.done
);
if (match != null) markDone(match);
```

### Konsequenz für „Krombacher → Bier?"

**Nein.** Der Abgleich läuft über die **Produktidentität (GTIN/EAN)**, nicht
über die Kategorie. Ein frei eingetipptes `"Bier"` hat `gtin = null` und wird
durch das Scannen einer Krombacher-Flasche **nicht** abgehakt.

Abgehakt wird nur, wenn der Listeneintrag **dieselbe EAN** trägt – also z. B.
wenn der Artikel vorher per Scan/Angebot mit EAN übernommen wurde.

Findet die App keinen Treffer, erscheint:

> „Ich habe keinen passenden Artikel in deiner Einkaufsliste gefunden.
> Bitte hake selbst ab."

Es gibt **keine** Kategorie-/Synonym-/Marken-Logik (kein „Krombacher = Bier").

## Teilen von Listen

Deeplink (App-Link, autoVerify auf `/inapp/.*`):

```
https://www.moincard.de/inapp/teile_einkaufsliste?shoppingListId=<internalId>
```

Empfänger öffnen den Link → App lädt die geteilte Liste im „External"-Modus
(`ExternalListEditingStarted`, `LoadExternalShoppingListEvent`,
`getShoppingListWithId`, Zustand `externalShoppingListId`) und können sie
befüllen. Dafür wird kein eigener Endpoint benutzt, es läuft über dieselbe
`internalId`.

Auf dem Desktop zeigt die Seite nur „… eigentlich eine Seite innerhalb der App" –
die URL ist also ein reiner App-Link.
