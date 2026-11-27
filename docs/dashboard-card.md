# Dashboard-Card & Automation

> Entity-ID anpassen: nach dem Einrichten heißt das Entity meist
> `todo.moin_card_einkaufsliste` (Gerät „MOIN CARD" + Listenname). Prüfe die
> genaue ID unter **Entwicklerwerkzeuge → Zustände** (Filter `todo.`).

## 1. Einfach (eingebaute Karte)

```yaml
type: todo-list
entity: todo.moin_card_einkaufsliste
title: 🛒 Einkaufsliste
```

Damit kannst du direkt Artikel eintippen und abhaken. Die **Kategorie** wird
automatisch aus dem MoinCard-Vokabular ergänzt.

## 2. Erweitert (Titel, Zähler, „Erledigte entfernen")

```yaml
type: vertical-stack
cards:
  - type: todo-list
    entity: todo.moin_card_einkaufsliste
    title: 🛒 Einkaufsliste
  - type: horizontal-stack
    cards:
      - type: button
        name: Erledigte entfernen
        icon: mdi:trash-can-outline
        show_state: false
        tap_action:
          action: perform-action
          perform_action: todo.remove_completed_items
          target:
            entity_id: todo.moin_card_einkaufsliste
      - type: button
        name: Liste leeren
        icon: mdi:playlist-remove
        show_state: false
        tap_action:
          action: perform-action
          perform_action: script.moincard_clear_list
```

Alle Artikel löschen (Script, da `todo.remove_item` nur einzelne Einträge kennt):

```yaml
script:
  moincard_clear_list:
    alias: "MOIN CARD: Liste leeren"
    mode: single
    sequence:
      - repeat:
          for_each: "{{ state_attr('todo.moin_card_einkaufsliste','items') or [] }}"
          sequence:
            - action: todo.remove_item
              target:
                entity_id: todo.moin_card_einkaufsliste
              data:
                item: "{{ repeat.item.uid }}"
```

## 3. Schnell-Eingabe mit EAN (Helper + Script + Karte)

Ermöglicht das Eintragen von Name **und** EAN, damit der Artikel später beim
Scan & Go automatisch abgehakt wird.

### Helper (Einstellungen → Geräte & Dienste → Helfer → Text)

```yaml
# configuration.yaml (alternativ per UI anlegen)
input_text:
  moincard_artikel:
    name: MOIN CARD neuer Artikel
    max: 100
  moincard_ean:
    name: MOIN CARD EAN (optional)
    max: 20
```

### Script

```yaml
script:
  moincard_add_item:
    alias: "MOIN CARD: Artikel hinzufügen"
    mode: single
    sequence:
      - variables:
          name: "{{ states('input_text.moincard_artikel') | trim }}"
          ean: "{{ states('input_text.moincard_ean') | trim }}"
      - condition: template
        value_template: "{{ name | length > 0 }}"
      - choose:
          - conditions: "{{ ean | length > 0 }}"
            sequence:
              - action: moincard.add_item
                data:
                  name: "{{ name }}"
                  ean: "{{ ean }}"
        default:
          - action: moincard.add_item
            data:
              name: "{{ name }}"
      - action: input_text.set_value
        target: { entity_id: input_text.moincard_artikel }
        data: { value: "" }
      - action: input_text.set_value
        target: { entity_id: input_text.moincard_ean }
        data: { value: "" }
```

### Karte

```yaml
type: entities
title: Artikel hinzufügen
icon: mdi:cart-plus
entities:
  - entity: input_text.moincard_artikel
    name: Artikel
  - entity: input_text.moincard_ean
    name: EAN (optional)
  - type: button
    name: Hinzufügen
    icon: mdi:plus-circle
    tap_action:
      action: perform-action
      perform_action: script.moincard_add_item
```

## 4. Automation-Beispiele

### Freitags Bier (mit EAN → scan-bar)

```yaml
automation:
  - alias: "Freitag: Bier auf die MOIN CARD Liste"
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
          unit: Flasche
```

### Aus einer Einkaufsliste-Zeile (mehrere Artikel)

```yaml
    actions:
      - action: moincard.add_item
        data:
          name: Milch
          quantity: 2
      - action: moincard.add_item
        data:
          name: Brot
      - action: moincard.add_item
        data:
          name: Äpfel
```

### Wöchentlich die Liste leeren

```yaml
automation:
  - alias: "Sonntag: MOIN CARD Liste leeren"
    triggers:
      - trigger: time
        at: "19:00:00"
    conditions:
      - condition: time
        weekday: [sun]
    actions:
      - action: todo.remove_completed_items
        target:
          entity_id: todo.moin_card_einkaufsliste
```

## 5. Optional: Mushroom (falls installiert)

```yaml
type: custom:mushroom-template-card
primary: Einkaufsliste
secondary: >-
  {{ state_attr('todo.moin_card_einkaufsliste','items')
     | selectattr('status','eq','needs_action') | list | count }} offen
icon: mdi:cart
tap_action:
  action: navigate
  navigation_path: /todo
```

## Hinweise

- Die Kategorie kommt automatisch aus dem Vokabular – kein Feld nötig.
- Ohne `ean` matcht der Scan (Scan & Go) den Artikel **nicht**; mit `ean` wird er
  beim Scannen automatisch abgehakt.
- `moincard.add_item` legt neue Namen zusätzlich im persönlichen Vokabular der
  App an (wie die App selbst).
