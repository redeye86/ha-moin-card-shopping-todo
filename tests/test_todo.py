"""Tests for the MOIN CARD todo platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.todo import DOMAIN as TODO_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.moincard.api import ShoppingList
from custom_components.moincard.const import DOMAIN

USER = "user@example.com"

ITEMS = [
    {
        "id": 10,
        "name": "Milch",
        "quantity": 2,
        "done": False,
        "category": "Frische, Milchprodukte",
        "gtin": None,
    },
    {
        "id": 11,
        "name": "Brot",
        "quantity": 1,
        "done": True,
        "category": None,
        "gtin": None,
    },
]

VOCAB = [{"name": "Milch", "category": "Frische, Milchprodukte"}]


def _make_list(items=None) -> ShoppingList:
    return ShoppingList(
        id=1, name="Einkaufsliste", internal_id="abc", items=items or []
    )


@pytest.fixture
def mock_api():
    with (
        patch(
            "custom_components.moincard.api.MoinCardApi.async_login",
            AsyncMock(return_value="token"),
        ),
        patch(
            "custom_components.moincard.api.MoinCardApi.async_get_lists",
            AsyncMock(
                return_value=[{"id": 1, "name": "Einkaufsliste", "internalId": "abc"}]
            ),
        ),
        patch(
            "custom_components.moincard.api.MoinCardApi.async_get_list",
            AsyncMock(return_value=_make_list(list(ITEMS))),
        ),
        patch(
            "custom_components.moincard.api.MoinCardApi.async_get_vocabulary",
            AsyncMock(return_value=list(VOCAB)),
        ),
    ):
        yield


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": USER, "password": "pw"},
        unique_id=USER,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _todo_entity_id(hass: HomeAssistant, needle: str = "einkaufsliste") -> str:
    for state in hass.states.async_all(TODO_DOMAIN):
        if needle in state.entity_id:
            return state.entity_id
    raise AssertionError(f"no todo entity matching {needle!r}")


async def test_setup_and_items(hass: HomeAssistant, mock_api) -> None:
    await _setup(hass)
    entity_id = _todo_entity_id(hass)

    state = hass.states.get(entity_id)
    assert state is not None
    # one of two items is completed -> one open item
    assert state.state == "1"

    result = await hass.services.async_call(
        TODO_DOMAIN,
        "get_items",
        {"entity_id": entity_id},
        blocking=True,
        return_response=True,
    )
    got = {i["summary"]: i for i in result[entity_id]["items"]}
    assert got["2x Milch"]["status"] == "needs_action"
    assert got["Brot"]["status"] == "completed"
    assert "Frische" in got["2x Milch"]["description"]


async def test_add_item_sets_category_from_vocabulary(
    hass: HomeAssistant, mock_api
) -> None:
    await _setup(hass)
    entity_id = _todo_entity_id(hass)

    add = AsyncMock(return_value=_make_list())
    with patch("custom_components.moincard.api.MoinCardApi.async_add_item", add):
        await hass.services.async_call(
            TODO_DOMAIN,
            "add_item",
            {"entity_id": entity_id, "item": "3x Milch"},
            blocking=True,
        )
        await hass.async_block_till_done()

    add.assert_awaited_once()
    _, kwargs = add.call_args
    assert kwargs["quantity"] == 3
    assert kwargs["category"] == "Frische, Milchprodukte"


async def test_add_item_with_ean_from_description(
    hass: HomeAssistant, mock_api
) -> None:
    await _setup(hass)
    entity_id = _todo_entity_id(hass)

    add = AsyncMock(return_value=_make_list())
    with patch("custom_components.moincard.api.MoinCardApi.async_add_item", add):
        await hass.services.async_call(
            TODO_DOMAIN,
            "add_item",
            {
                "entity_id": entity_id,
                "item": "Krombacher Pils",
                "description": "Kategorie: Getränke · EAN: 4008165000016",
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    _, kwargs = add.call_args
    assert kwargs["gtin"] == "4008165000016"
    assert kwargs["category"] == "Getränke"


async def test_update_item_done(hass: HomeAssistant, mock_api) -> None:
    await _setup(hass)
    entity_id = _todo_entity_id(hass)

    done = AsyncMock(return_value=_make_list())
    with patch("custom_components.moincard.api.MoinCardApi.async_set_done", done):
        await hass.services.async_call(
            TODO_DOMAIN,
            "update_item",
            {"entity_id": entity_id, "item": "10", "status": "completed"},
            blocking=True,
        )
        await hass.async_block_till_done()

    done.assert_awaited_once()
    assert done.call_args.args[2] is True


async def test_delete_item(hass: HomeAssistant, mock_api) -> None:
    await _setup(hass)
    entity_id = _todo_entity_id(hass)

    delete = AsyncMock(return_value=_make_list())
    with patch("custom_components.moincard.api.MoinCardApi.async_delete_item", delete):
        await hass.services.async_call(
            TODO_DOMAIN,
            "remove_item",
            {"entity_id": entity_id, "item": "10"},
            blocking=True,
        )
        await hass.async_block_till_done()

    delete.assert_awaited_once()
    assert delete.call_args.args[1] == 10


async def test_add_item_service(hass: HomeAssistant, mock_api) -> None:
    await _setup(hass)
    add = AsyncMock(return_value=_make_list())
    with patch("custom_components.moincard.api.MoinCardApi.async_add_item", add):
        await hass.services.async_call(
            DOMAIN,
            "add_item",
            {"name": "Krombacher Pils", "quantity": 6, "ean": "4008165000016"},
            blocking=True,
        )
        await hass.async_block_till_done()

    add.assert_awaited_once()
    _, kwargs = add.call_args
    assert kwargs["quantity"] == 6
    assert kwargs["gtin"] == "4008165000016"


async def test_vocabulary_list_is_readonly_catalog(
    hass: HomeAssistant, mock_api
) -> None:
    await _setup(hass)
    entity_id = _todo_entity_id(hass, "vokabular")

    result = await hass.services.async_call(
        TODO_DOMAIN,
        "get_items",
        {"entity_id": entity_id},
        blocking=True,
        return_response=True,
    )
    items = result[entity_id]["items"]
    assert [i["summary"] for i in items] == ["Milch"]
    assert "Frische" in items[0]["description"]

    # read-only catalog -> adding must fail
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            TODO_DOMAIN,
            "add_item",
            {"entity_id": entity_id, "item": "Neuer Artikel"},
            blocking=True,
        )
