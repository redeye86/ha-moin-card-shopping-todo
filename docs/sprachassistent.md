# Sprach-/LLM-Agent: Vokabular als Liste

Idee: Die „gefundenen" Artikel (Standardliste + persönliche Einträge) liegen als
**eigene, schreibgeschützte `todo`-Liste** in Home Assistant. Der Agent bekommt
diese Liste + den gesprochenen Gegenstand, gleicht ab und fügt bei Treffer hinzu.

## Die zwei Entities

| Entity | Rolle |
| --- | --- |
| `todo.moin_card_vokabular` | **Katalog** aller bekannten Produkte (Name + Kategorie). Read-only. |
| `todo.moin_card_einkaufsliste` | die echte MOIN CARD Einkaufsliste (schreibbar) |

Der Katalog wird automatisch aus `GET /api/shoppinglist/vocabulary/list`
(Standardliste + persönliche Einträge) gebaut – aktuell **326 Einträge**.

## Agent-Flow

```
Sprachbefehl: "Füge Milch zur Einkaufsliste hinzu"
  1. Katalog lesen:      todo.get_items  -> todo.moin_card_vokabular
  2. Abgleichen:         gesprochenen Gegenstand -> Katalog-Eintrag (Name + Kategorie)
  3. Bei Treffer:        todo.add_item    -> todo.moin_card_einkaufsliste
                         (oder Service moincard.add_item mit name+category)
```

### Warum `moincard.add_item` statt `todo.add_item`?

`moincard.add_item` setzt zusätzlich die Kategorie automatisch aus dem Vokabular
und legt neue Namen im persönlichen Vokabular an:

```yaml
action: moincard.add_item
data:
  name: "{{ match_name }}"
  category: "{{ match_category }}"
  ean: "{{ match_ean | default(omit) }}"   # nur falls bekannt
```

`todo.add_item` genügt aber auch – die Integration füllt die Kategorie selbst.

## Override-Muster (wie bei der Laden-Zuordnung)

Genau wie bei deiner Store-Zuordnung (AI ordnet zu, Liste `item -> geschäft`
overridden) kannst du eine **Override-Liste** voranstellen:

```
spoken term  ->  kanonischer Katalog-Name
```

Der Agent prüft **zuerst** die Override-Liste und fällt sonst auf das
Vokabular zurück. Die Override-Liste kann eine normale HA-`todo`-Liste sein,
deren Einträge z. B. `Krombacher = Bier` heißen (Name = gesprochen, Beschreibung
= kanonisch) – oder ein `input_text`/Template/Node-RED-Mapping.

### Beispiel-Ablauf mit Override

```
"Krombacher"  -> Override-Liste: "Krombacher" = "Bier"
              -> kein Override -> Vokabular-Match (unscharf): "Krombacher Pils" o.ä.
              -> Treffer -> moincard.add_item(name="Bier", category="Alkohol")
```

## Beispiel: LLM-Agent (HA Assist + OpenAI/Anthropic/Ollama)

Systemprompt-Auszug:

> Du hilfst beim Einkauf. Die verfügbaren Artikel stehen in der To-do-Liste
> „MOIN CARD Vokabular" (`todo.moin_card_vokabular`); lies sie mit
> `todo.get_items`. Wenn der Nutzer einen Artikel nennt, suche den
> bestpassenden Eintrag (Groß-/Kleinschreibung, Akzente, Wortteile ignorieren).
> Bei Treffer füge ihn mit `moincard.add_item` (Name + Kategorie) zur Liste
> `todo.moin_card_einkaufsliste` hinzu. Konsultiere zuvor die Override-Liste
> `<deine Liste>`. Findest du nichts, frage nach.

## Beispiel: Automation ohne LLM

```yaml
automation:
  - alias: "MOIN CARD: per Sprache hinzufügen"
    triggers:
      - trigger: conversation
        command:
          - "füge {item} zur einkaufsliste hinzu"
          - "{item} auf die einkaufsliste"
    actions:
      - action: moincard.add_item
        data:
          name: "{{ trigger.slots.item }}"
```

## Wichtig

- Der Katalog enthält **nur Name + Kategorie, keine EAN**. Für automatisches
  **Abhaken per Scan (Scan & Go)** braucht der Artikel eine **EAN** → beim
  Anlegen mitgeben (`moincard.add_item ... ean: "..."`).
- Der Katalog ist **schreibgeschützt**; Änderungen macht man im persönlichen
  Vokabular der App (oder über die Override-Liste).
- Katalog aktuell halten: die Integration lädt das Vokabular periodisch (TTL 6 h)
  und beim Neustart. Alternativ als Datei siehe
  [vokabular-export.md](vokabular-export.md).
