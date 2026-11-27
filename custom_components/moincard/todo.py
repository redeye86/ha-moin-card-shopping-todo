"""todo platform for MOIN CARD shopping lists."""

from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import MoinCardConflictError, MoinCardError, ShoppingList, item_quantity
from .const import DOMAIN, MANUFACTURER
from .coordinator import MoinCardCoordinator

_LOGGER = logging.getLogger(__name__)

_QTY_RE = re.compile(r"^\s*(\d+)\s*[x×]\s*(.+)$", re.IGNORECASE)
_GTIN_RE = re.compile(r"(?:gtin|ean|ean13|ean8)\s*[:=]?\s*(\d{8,14})", re.IGNORECASE)
_GTIN_BARE_RE = re.compile(r"(?:^|[^\d])(\d{8,14})(?:[^\d]|$)")
_CATEGORY_RE = re.compile(r"(?:category|kategorie)\s*[:=]\s*([^·;\n]+)", re.IGNORECASE)
_UNIT_RE = re.compile(r"(?:unit|einheit|menge)\s*[:=]\s*([^·;\n]+)", re.IGNORECASE)


def parse_summary(summary: str | None) -> tuple[int, str]:
    """Return (quantity, name) from a summary like '3x Milch'."""
    text = (summary or "").strip()
    match = _QTY_RE.match(text)
    if match:
        return int(match.group(1)), match.group(2).strip()
    return 1, text


def format_summary(name: str, quantity: int) -> str:
    return f"{quantity}x {name}" if quantity and quantity > 1 else name


def parse_description(
    description: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Return (gtin, category, unit) parsed from a description."""
    if not description:
        return None, None, None
    gtin = None
    match = _GTIN_RE.search(description)
    if match:
        gtin = match.group(1)
    else:
        match = _GTIN_BARE_RE.search(description)
        if match:
            gtin = match.group(1)
    category = None
    match = _CATEGORY_RE.search(description)
    if match:
        category = match.group(1).strip()
    unit = None
    match = _UNIT_RE.search(description)
    if match:
        unit = match.group(1).strip()
    return gtin, category, unit


def format_description(
    category: str | None, gtin: str | None, unit: str | None
) -> str | None:
    parts: list[str] = []
    if category:
        parts.append(f"Kategorie: {category}")
    if unit:
        parts.append(f"Einheit: {unit}")
    if gtin:
        parts.append(f"EAN: {gtin}")
    return " · ".join(parts) or None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MoinCardCoordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    @callback
    def _add_new_lists() -> None:
        entities = []
        for internal_id in coordinator.data or {}:
            if internal_id in known:
                continue
            known.add(internal_id)
            entities.append(MoinCardTodoList(coordinator, entry, internal_id))
        if entities:
            async_add_entities(entities)

    _add_new_lists()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_lists))


class MoinCardTodoList(CoordinatorEntity[MoinCardCoordinator], TodoListEntity):
    """A MOIN CARD shopping list as a Home Assistant todo list."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(
        self,
        coordinator: MoinCardCoordinator,
        entry: ConfigEntry,
        internal_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._internal_id = internal_id
        self._attr_unique_id = f"{entry.entry_id}_{internal_id}"
        lst = self._shopping_list
        self._attr_name = lst.name if lst else "Einkaufsliste"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "MOIN CARD",
            "manufacturer": MANUFACTURER,
        }

    # -- helpers -----------------------------------------------------------
    @property
    def _shopping_list(self) -> ShoppingList | None:
        return (self.coordinator.data or {}).get(self._internal_id)

    def _item_by_uid(self, uid: str | None) -> dict[str, Any] | None:
        if uid is None:
            return None
        for item in self._shopping_list.items if self._shopping_list else []:
            if str(item.get("id")) == str(uid):
                return item
        return None

    @property
    def available(self) -> bool:
        return super().available and self._shopping_list is not None

    # -- state -------------------------------------------------------------
    @property
    def todo_items(self) -> list[TodoItem]:
        result = []
        for item in self._shopping_list.items if self._shopping_list else []:
            result.append(
                TodoItem(
                    uid=str(item["id"]),
                    summary=format_summary(item.get("name") or "", item_quantity(item)),
                    status=(
                        TodoItemStatus.COMPLETED
                        if item.get("done")
                        else TodoItemStatus.NEEDS_ACTION
                    ),
                    description=format_description(
                        item.get("category"), item.get("gtin"), item.get("unit")
                    ),
                )
            )
        return result

    # -- mutations ---------------------------------------------------------
    async def _guard(self, coro) -> ShoppingList | None:
        try:
            return await coro
        except MoinCardConflictError as err:
            await self.coordinator.async_request_refresh()
            raise HomeAssistantError(
                "Der Artikel wurde zwischenzeitlich geändert, bitte erneut versuchen."
            ) from err
        except MoinCardError as err:
            raise HomeAssistantError(str(err)) from err
        finally:
            await self.coordinator.async_request_refresh()

    async def async_create_todo_item(self, item: TodoItem) -> None:
        lst = self._shopping_list
        if lst is None:
            raise HomeAssistantError("Einkaufsliste ist nicht verfügbar.")
        quantity, name = parse_summary(item.summary)
        gtin, category, unit = parse_description(item.description)
        if not name:
            raise HomeAssistantError("Der Artikelname darf nicht leer sein.")
        if category is None:
            category = self.coordinator.category_for(name)
        await self._guard(
            self.coordinator.api.async_add_item(
                lst,
                name,
                quantity=quantity,
                category=category,
                gtin=gtin,
                unit=unit,
            )
        )
        # Register the (possibly new) name in the personal vocabulary so the
        # app can suggest it later - mirrors the app behaviour.
        if category is None:
            self.hass.async_create_task(self._register_vocabulary(name))

    async def _register_vocabulary(self, name: str) -> None:
        try:
            await self.coordinator.api.async_create_vocabulary_item(name, None)
        except MoinCardError:  # non fatal
            pass

    async def async_update_todo_item(self, item: TodoItem) -> None:
        lst = self._shopping_list
        if lst is None:
            raise HomeAssistantError("Einkaufsliste ist nicht verfügbar.")
        current = self._item_by_uid(item.uid)
        if current is None:
            await self.coordinator.async_request_refresh()
            raise HomeAssistantError("Artikel nicht gefunden (veralteter Stand).")

        # 1) content change (name / quantity / category / gtin / unit).
        if item.summary is not None or item.description is not None:
            name = current.get("name") or ""
            quantity = item_quantity(current)
            category = current.get("category")
            gtin = current.get("gtin")
            unit = current.get("unit")
            if item.summary is not None:
                quantity, name = parse_summary(item.summary)
            if item.description is not None:
                parsed_gtin, parsed_category, parsed_unit = parse_description(
                    item.description
                )
                gtin = parsed_gtin
                unit = parsed_unit
                if parsed_category is not None:
                    category = parsed_category

            if category is None:
                category = self.coordinator.category_for(name)

            if (
                name != (current.get("name") or "")
                or quantity != item_quantity(current)
                or category != current.get("category")
                or (gtin or None) != (current.get("gtin") or None)
                or (unit or None) != (current.get("unit") or None)
            ):
                await self._guard(
                    self.coordinator.api.async_update_item(
                        lst,
                        current,
                        name=name or current.get("name"),
                        quantity=quantity,
                        category=category,
                        gtin=gtin,
                        unit=unit,
                    )
                )
                current = self._item_by_uid(item.uid) or current
                if category is None:
                    self.hass.async_create_task(self._register_vocabulary(name))

        # 2) status change (done) - uses its own endpoint.
        if item.status is not None:
            done = item.status == TodoItemStatus.COMPLETED
            if done != bool(current.get("done")):
                await self._guard(
                    self.coordinator.api.async_set_done(lst, current, done)
                )

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        lst = self._shopping_list
        if lst is None:
            raise HomeAssistantError("Einkaufsliste ist nicht verfügbar.")
        for uid in uids:
            await self._guard(self.coordinator.api.async_delete_item(lst, int(uid)))
