# MOIN CARD für Home Assistant

Custom Integration, die die **Einkaufsliste der MOIN CARD App**
(`de.buenting.moincard`) als Home-Assistant-`todo`-Liste bereitstellt – inkl.
automatischer **Kategorie** aus dem MoinCard-Vokabular und optionaler
**EAN/GTIN**, damit ein späterer Scan (Scan & Go) den Artikel automatisch
abhakt.

## Dokumentation

Ausführliche Notizen (API-Protokoll, App-Analyse, Scan/Abbaken, Vokabular,
Konto-Einrichtung, HA-Integration, Erkenntnisse) liegen in [`docs/`](docs/README.md).

## Funktionen

- `todo`-Entities: eine pro MoinCard-Einkaufsliste (Hauptliste heißt meist
  „Einkaufsliste“).
- Zusätzlich ein **read-only `todo`-Entity „Vokabular“** als Produktkatalog
  (Name + Kategorie) für Sprach-/LLM-Agenten.
- Anzeige der **Menge** als `Nx Name` (`2x Milch`).
- **Kategorie wird automatisch** aus dem MoinCard-Vokabular (Standardliste +
  persönliche Einträge) gesetzt.
- **EAN/GTIN** optional über die Beschreibung (`EAN: 4008165000016`) oder den
  Service `moincard.add_item` → Artikel matcht danach beim Scan über die EAN.
- Neue Artikelnamen werden im persönlichen Vokabular der App angelegt
  (wie in der App selbst).
- Service `moincard.add_item` für Automationen (Name, Menge, EAN, Kategorie).

## Vokabular-Export (CSV/JSON)

Die Artikel-Vorschläge (Standardliste + persönliche Einträge, 326 Namen /
15 Kategorien) liegen unter [`data/`](data/) (siehe
[docs/vokabular-export.md](docs/vokabular-export.md)):

- `data/vocabulary.csv` – `id,name,category,selfCreated`
- `data/vocabulary.json` – strukturiert (`names`, `by_category`, ...)
- `data/vocabulary_names.txt` – nur Namen, einer pro Zeile

Neu ziehen: `python3 moin_list.py vocab --out data`

## Installation (HACS / manuell)

1. Ordner `custom_components/moincard` nach `<config>/custom_components/`
   kopieren.
2. Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen → „MOIN CARD“**
   und mit E-Mail + Passwort anmelden.

## Verwendung

Über die Integration werden `todo.*`-Entities angelegt. Diese können direkt im
HA-Dashboard, per Sprachassistent oder per Automation genutzt werden.

### EAN mitgeben (damit der Scan matcht)

In der Beschreibung des Todo-Items:

```
EAN: 4008165000016
```

oder gemischt mit Kategorie:

```
Kategorie: Getränke · EAN: 4008165000016
```

### Service

```yaml
service: moincard.add_item
data:
  name: Krombacher Pils
  quantity: 6
  ean: "4008165000016"
  unit: Flasche
```

### Automation-Beispiel

```yaml
automation:
  - alias: "Freitag Bier auf die Liste"
    triggers:
      - trigger: time
        at: "16:00:00"
    conditions:
      - condition: time
        weekday: [fri]
    actions:
      - action: moincard.add_item
        data:
          name: Krombacher Pils
          quantity: 6
          ean: "4008165000016"
```

## Hintergrund

Die API wurde aus der Android-App `de.buenting.moincard` 2.28.1
(Flutter/Dart 3.13.4) rekonstruiert und verifiziert:

| Zweck                | Request                                                        |
| -------------------- | -------------------------------------------------------------- |
| Login                | `POST /api/login {username,password}` → `token`                |
| Listen               | `GET /api/shoppinglist/lists`                                  |
| Liste laden          | `POST /api/shoppinglist/list {internalId}`                     |
| Liste anlegen        | `POST /api/shoppinglist/create {id:0,name}`                    |
| Artikel hinzufügen   | `POST /api/shoppinglist/item/update {internalId,shoppingListItem,addQuantity}` |
| Artikel abhaken      | `POST /api/shoppinglist/item/done {internalId,shoppingListItem,done}` |
| Artikel löschen      | `DELETE /api/shoppinglist/item/delete?internalId=&itemId=`     |
| Vokabular            | `GET /api/shoppinglist/vocabulary/list` / `.../standardlist`   |

Header: `x-api-key: <fest>`, `x-auth-token: <token>`, `accept: application/json`.

> Hinweis: `addQuantity` ist ein **Delta**; das Feld `quantity` im
> `shoppingListItem` muss der aktuellen Server-Menge entsprechen (sonst HTTP
> 409). Das Plugin berücksichtigt das automatisch.

## Entwicklung / Tests

```bash
python -m venv .venv && . .venv/bin/activate
pip install homeassistant pytest-homeassistant-custom-component
pytest tests/
ruff check custom_components/ tests/
```

Die Tests mocken die API (`tests/test_todo.py`, `tests/test_config_flow.py`).
Der API-Client selbst (`api.py`) wurde zusätzlich live gegen die echte API
verifiziert (Login, Liste, Hinzufügen inkl. Kategorie/EAN, Menge, Umbenennen,
Abhaken, Löschen).

## Dateien

```
custom_components/moincard/
├── __init__.py        # Setup + Service moincard.add_item
├── manifest.json
├── const.py
├── api.py             # async API-Client (Login, Listen, Items, Vokabular)
├── coordinator.py     # Polling + Vocabulary (Name -> Kategorie)
├── config_flow.py     # Login-Flow + Optionen + Reauth
├── todo.py            # todo-Entity (Menge, Kategorie, EAN)
├── services.yaml
├── strings.json
└── translations/{de,en}.json
```

## Haftungsausschluss

Inoffiziell, ohne Verbindung zu Bünting/MOIN CARD. Nutzung auf eigene
Verantwortung.
