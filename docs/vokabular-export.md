# Vokabular-Export (CSV / JSON / TXT)

Die komplette Vorschlagsliste (Standardliste + persönliche Einträge) liegt als
Datei im Repo – ideal, um sie einem Sprachagenten (z. B. HA Assist mit LLM) als
„bekannte Artikel" mitzugeben.

## Dateien

| Datei | Inhalt |
| --- | --- |
| `data/vocabulary.csv` | `id,name,category,selfCreated` – 326 Zeilen |
| `data/vocabulary.json` | strukturiert: `count`, `categories`, `items`, `names`, `by_category` |
| `data/vocabulary_names.txt` | nur die Namen, einer pro Zeile (für Slot-Listen/Prompts) |

Stand: **326 Einträge / 15 Kategorien**.

### `vocabulary.csv`

```csv
id,name,category,selfCreated
240,Bier,Alkohol,false
241,Champagner,Alkohol,false
...
```

### `vocabulary.json`

```json
{
  "count": 326,
  "categories": ["Alkohol", "Backwaren", "..."],
  "items": [{"id": 240, "name": "Bier", "category": "Alkohol", "selfCreated": false}],
  "names": ["Bier", "Champagner", "..."],
  "by_category": {"Alkohol": ["Bier", "Champagner", "..."]}
}
```

### `vocabulary_names.txt`

```
Bier
Champagner
Gin
...
```

## Neu ziehen (inkl. persönlicher Einträge)

Die Standardliste ist fix; persönliche Einträge wachsen mit der Nutzung. Neu
exportieren mit dem PoC:

```bash
export MOIN_USER='mail@example.com' MOIN_PASS='...'
python3 moin_list.py vocab --out data          # Standard + persönliche Einträge
python3 moin_list.py vocab --standard --out data   # nur Standardliste
```

## Nutzung mit einem Sprachagenten

Der Agent bekommt die **Namensliste** und den **gesprochenen Gegenstand**, gleicht
ab und fügt bei Treffer hinzu.

### A) HA Assist + LLM (empfohlen)

- Namensliste als Kontext/Prompt geben (`vocabulary_names.txt`) oder die
  Datei per Script laden.
- Der Agent matcht „Milch" → `Milch`, ruft dann:

  ```yaml
  action: moincard.add_item
  data:
    name: "{{ match.name }}"
    category: "{{ match.category }}"
  ```

- Alternativ direkt das `todo`-Entity des Agents nutzen (`todo.add_item`); die
  Integration setzt die Kategorie ohnehin automatisch aus dem Vokabular.

### B) Template/Automation ohne LLM

```yaml
variables:
  spoken: "Milch"
  # Namensliste aus dem JSON laden
  known: "{{ (states('input_text...') ) }}"  # oder per shell/rest
```

Da ein reiner Template-Abgleich in HA umständlich ist, bietet sich hier eher
ein kleines Skript (z. B. Node-RED oder ein `shell_command`) an, das die
JSON-Datei liest und den besten Treffer (normalisiert/unscharf) bestimmt, dann
`moincard.add_item` aufruft.

### C) Andere Agenten (eigener Bot)

Einfach `vocabulary.json` laden und normalisiert (klein, ohne Akzente) exakt
oder unscharf gegen `names` matchen; Treffer → Artikel via
`POST /api/shoppinglist/item/update` anlegen (oder `moincard.add_item`).

## Wichtig

- Das Vokabular enthält **nur Name + Kategorie**, **keine EAN**.
- Damit ein späterer **Scan (Scan & Go)** den Artikel automatisch abhakt, muss
  der Artikel eine **EAN** haben – die kommt nicht aus dem Vokabular, sondern
  aus dem Barcode-Lookup (mytime.de/OpenGTINDB) bzw. wird beim Anlegen
  mitgegeben (`moincard.add_item ... ean: "..."`).
