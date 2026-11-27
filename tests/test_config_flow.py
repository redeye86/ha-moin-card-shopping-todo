"""Tests for the MOIN CARD config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.moincard.api import MoinCardApiError, MoinCardAuthError
from custom_components.moincard.const import DOMAIN

USER = "a@b.de"


async def test_user_flow_success(hass: HomeAssistant) -> None:
    with patch("custom_components.moincard.config_flow._validate", AsyncMock()):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"username": USER, "password": "pw"}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"MOIN CARD ({USER})"
    assert result["data"]["username"] == USER


async def test_user_flow_invalid_auth(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.moincard.config_flow._validate",
        AsyncMock(side_effect=MoinCardAuthError("nope")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"username": USER, "password": "bad"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.moincard.config_flow._validate",
        AsyncMock(side_effect=MoinCardApiError(500, "boom")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"username": USER, "password": "pw"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_already_configured(hass: HomeAssistant) -> None:
    MockConfigEntry(domain=DOMAIN, data={"username": USER}, unique_id=USER).add_to_hass(
        hass
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch("custom_components.moincard.config_flow._validate", AsyncMock()):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"username": USER, "password": "pw"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
