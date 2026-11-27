"""Data update coordinator + vocabulary handling for MOIN CARD."""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MoinCardApi, MoinCardError, ShoppingList
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

VOCAB_TTL = timedelta(hours=6)


def _normalize(value: str) -> str:
    """Normalize an item name for matching (lower, no accents, single spaces)."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value


class Vocabulary:
    """Maps item names to categories using the MoinCard standard + user list."""

    def __init__(self) -> None:
        self._by_name: dict[str, str] = {}

    @property
    def size(self) -> int:
        return len(self._by_name)

    def load(self, entries: list[dict]) -> None:
        for entry in entries:
            name = (entry.get("name") or "").strip()
            category = entry.get("category")
            if name and category:
                self._by_name.setdefault(_normalize(name), category)

    def category_for(self, name: str) -> str | None:
        return self._by_name.get(_normalize(name))


class MoinCardCoordinator(DataUpdateCoordinator[dict[str, ShoppingList]]):
    """Polls all shopping lists of the account."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: MoinCardApi,
        entry: ConfigEntry,
    ) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=int(interval)),
            config_entry=entry,
        )
        self.api = api
        self.vocabulary = Vocabulary()
        self._vocab_loaded = None  # datetime of last load

    async def _async_update_data(self) -> dict[str, ShoppingList]:
        try:
            overviews = await self.api.async_get_lists()
        except MoinCardError as err:
            raise UpdateFailed(str(err)) from err

        result: dict[str, ShoppingList] = {}
        for overview in overviews:
            internal_id = overview.get("internalId")
            if not internal_id:
                continue
            try:
                result[internal_id] = await self.api.async_get_list(internal_id)
            except MoinCardError as err:
                raise UpdateFailed(str(err)) from err

        await self._async_ensure_vocabulary()
        return result

    async def _async_ensure_vocabulary(self) -> None:
        now = self.hass.loop.time()
        if (
            self._vocab_loaded is not None
            and (now - self._vocab_loaded) < VOCAB_TTL.total_seconds()
        ):
            return
        try:
            entries = await self.api.async_get_vocabulary()
            if not entries:
                entries = await self.api.async_get_standard_list()
            self.vocabulary.load(entries)
            self._vocab_loaded = now
            _LOGGER.debug("Loaded %s vocabulary entries", self.vocabulary.size)
        except MoinCardError as err:  # non fatal
            _LOGGER.warning("Could not load MoinCard vocabulary: %s", err)

    def category_for(self, name: str) -> str | None:
        return self.vocabulary.category_for(name)
