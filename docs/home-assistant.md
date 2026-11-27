# Home-Assistant-Integration

Ordner: `custom_components/moincard/`

## Architektur

```
config_flow.py   Login (E-Mail/Passwort) + Options (Poll-Intervall) + Reauth
      │
coordinator.py   MoinCardCoordinator: pollt alle Listen, hält Vocabulary
      │
api.py           MoinCardApi: async HTTP-Client + Modelle
      │
todo.py          MoinCardTodoList: ein todo-Entity pro Einkaufsliste
__init__.py      Setup + Service moincard.add_item
```

- **Ein `todo`-Entity pro MoinCard-Liste.** Entity-Name = Listen-Name
  (meist „Einkaufsliste"), `unique_id` = `entry_id + internalId`.
- Poll alle `scan_interval` Sekunden (Default 300) `GET /lists` und je Liste
  `POST /list`.
- Der Token wird bei `401/403` automatisch neu geholt (ein Retry).
- `409` beim Update → Coordinator wird aktualisiert und ein
  `HomeAssistantError` geworfen (Retry durch den Nutzer).

## Verhalten

### Anzeige (Lesen)

`TodoItem` je Artikel:

- `uid` = Item-`id`
- `summary` = `"Nx Name"` wenn `quantity > 1`, sonst nur `name`
- `status` = `completed` wenn `done`, sonst `needs_action`
- `description` = `"Kategorie: <cat> · EAN: <gtin> · Einheit: <unit>"` (nur
  vorhandene Teile)

### Anlegen

`summary` erlaubt ein Mengen-Präfix: `"3x Milch"` → `quantity=3`, `name="Milch"`.

Die **Kategorie** wird automatisch aus dem Vokabular bestimmt:
Name normalisieren (klein, ohne Akzente, einfache Leerzeichen) und in der
`Vocabulary` (Standardliste + persönliche Einträge) nachschlagen.

Ist kein Eintrag vorhanden, wird der Name – wie in der App – per
`vocabulary/create` im persönlichen Vokabular angelegt.

### EAN/GTIN

Das `todo`-Modell kennt kein eigenes EAN-Feld. Deshalb:

1. Über die **Beschreibung**:

   ```
   EAN: 4008165000016
   Kategorie: Getränke · EAN: 4008165000016
   ```

   Parser akzeptiert `gtin:`/`ean:` bzw. eine nackte 8–14-stellige Zahl,
   sowie `category:`/`kategorie:` und `unit:`/`einheit:`.

2. Über den **Service**:

   ```yaml
   service: moincard.add_item
   data:
     name: Krombacher Pils
     quantity: 6
     ean: "4008165000016"
     unit: Flasche
   ```

Mit gesetzter EAN kann der Artikel später beim Scan & Go über die GTIN
automatisch abgehakt werden. Ohne EAN (reiner Name) **nicht** (siehe
[scan-und-abhaken.md](scan-und-abhaken.md)).

### Ändern / Abhaken / Löschen

- Statuswechsel → `POST /item/done`
- Name/Menge/Kategorie/EAN → `POST /item/update`
- Löschen → `DELETE /item/delete`

Beim Update wird die aktuelle `quantity` als Body-`quantity` mitgeschickt und
die Differenz als `addQuantity` (siehe [protokoll.md](protokoll.md)) – das
macht `api.async_update_item` automatisch.

## Service `moincard.add_item`

| Feld | Pflicht | Beschreibung |
| --- | --- | --- |
| `name` | ✅ | Artikelname |
| `quantity` | – | Default 1 |
| `ean` | – | EAN/GTIN (für Scan-Matching) |
| `category` | – | sonst automatisch aus Vokabular |
| `unit` | – | Einheit |
| `list_id` | – | `internalId`/`id`/Name der Liste |
| `entry_id` | – | nur bei mehreren Konten nötig |

## Dateien

```
custom_components/moincard/
├── __init__.py        # Setup + Service
├── manifest.json      # iot_class: cloud_polling
├── const.py
├── api.py
├── coordinator.py
├── config_flow.py
├── todo.py
├── services.yaml
├── strings.json
└── translations/{de,en}.json
```

## Tests

```
tests/test_config_flow.py   Login-Flow (success / invalid_auth / cannot_connect / abort)
tests/test_todo.py          Setup, Anzeige, Anlegen(Kategorie/EAN), Abhaken, Löschen, Service
```

```bash
pytest tests/
ruff check custom_components/ tests/
```

Die Tests mocken die API; der reale `MoinCardApi` wurde zusätzlich live
verifiziert (siehe `moin_list.py` / `docs/protokoll.md`).

## Grenzen

- Kein `MOVE`/Sortieren (die API hat keine Item-Reihenfolge).
- Kein `sensor`/Button; Menu-Feld ist die `description` (kein eigenes Feld).
- Nur eine Liste pro `internalId`; mehrere Listen → mehrere Entities.
