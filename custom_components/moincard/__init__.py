"""The MOIN CARD integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MoinCardApi, ShoppingList
from .const import DOMAIN
from .coordinator import MoinCardCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.TODO]

SERVICE_ADD_ITEM = "add_item"

ADD_ITEM_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
        vol.Required("name"): cv.string,
        vol.Optional("quantity", default=1): vol.All(int, vol.Range(min=1)),
        vol.Optional("ean"): cv.string,
        vol.Optional("category"): cv.string,
        vol.Optional("unit"): cv.string,
        vol.Optional("list_id"): cv.string,
    }
)


def _first_coordinator(hass: HomeAssistant) -> MoinCardCoordinator:
    for coordinator in hass.data.get(DOMAIN, {}).values():
        if isinstance(coordinator, MoinCardCoordinator):
            return coordinator
    raise HomeAssistantError("Keine MOIN CARD Instanz konfiguriert.")


def _coordinator_for(hass: HomeAssistant, entry_id: str | None) -> MoinCardCoordinator:
    if entry_id:
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
        if isinstance(coordinator, MoinCardCoordinator):
            return coordinator
        raise HomeAssistantError(f"Unbekannte entry_id: {entry_id}")
    return _first_coordinator(hass)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register integration level services."""
    hass.data.setdefault(DOMAIN, {})

    async def _async_add_item(call: ServiceCall) -> None:
        coordinator = _coordinator_for(hass, call.data.get("entry_id"))
        if not coordinator.data:
            await coordinator.async_request_refresh()

        target_list: ShoppingList | None = None
        wanted = call.data.get("list_id")
        for internal_id, shopping_list in (coordinator.data or {}).items():
            if wanted is None or wanted in (
                internal_id,
                str(shopping_list.id),
                shopping_list.name,
            ):
                target_list = shopping_list
                break
        if target_list is None:
            raise HomeAssistantError("Keine passende Einkaufsliste gefunden.")

        name = call.data["name"]
        category = call.data.get("category") or coordinator.category_for(name)
        await coordinator.api.async_add_item(
            target_list,
            name,
            quantity=call.data.get("quantity", 1),
            category=category,
            gtin=call.data.get("ean") or None,
            unit=call.data.get("unit") or None,
        )
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_ITEM, _async_add_item, schema=ADD_ITEM_SCHEMA
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MOIN CARD from a config entry."""
    api = MoinCardApi(
        async_get_clientsession(hass),
        entry.data["username"],
        entry.data["password"],
    )
    await api.async_login()

    coordinator = MoinCardCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
