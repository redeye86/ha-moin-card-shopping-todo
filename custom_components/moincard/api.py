"""Async API client for the MOIN CARD (MoinCard) shopping list API.

The endpoints and payloads were reverse-engineered from the Android app
``de.buenting.moincard`` 2.28.1 (Flutter/Dart 3.13.4) and verified against the
live API.  See the repository README for details.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .const import API_KEY, BASE_URL

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


class MoinCardError(Exception):
    """Base error."""


class MoinCardAuthError(MoinCardError):
    """Authentication/credentials invalid."""


class MoinCardConflictError(MoinCardError):
    """HTTP 409 - the item was modified concurrently (stale quantity)."""


class MoinCardApiError(MoinCardError):
    """Unexpected API response."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message


@dataclass(slots=True)
class ShoppingList:
    """A MOIN CARD shopping list with its items."""

    id: int
    name: str
    internal_id: str
    items: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> ShoppingList:
        lst = payload.get("shoppingList", payload)
        return cls(
            id=lst.get("id"),
            name=lst.get("name"),
            internal_id=lst.get("internalId"),
            items=list(payload.get("shoppingListItems") or []),
        )


def item_quantity(item: dict[str, Any]) -> int:
    try:
        return int(item.get("quantity") or 0)
    except (TypeError, ValueError):
        return 0


class MoinCardApi:
    """Thin async wrapper around the MoinCard REST API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        base_url: str = BASE_URL,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._base_url = base_url.rstrip("/")
        self._token: str | None = None

    # -- low level ---------------------------------------------------------
    def _headers(self, auth: bool, content_type: bool) -> dict[str, str]:
        headers = {"x-api-key": API_KEY, "accept": "application/json"}
        if content_type:
            headers["content-type"] = "application/json; charset=utf-8"
        if auth and self._token:
            headers["x-auth-token"] = self._token
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: Any | None = None,
        auth: bool = True,
        _retry: bool = True,
    ) -> Any:
        url = path if path.startswith("http") else self._base_url + path
        headers = self._headers(auth, body is not None)
        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                json=body,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                text = await resp.text()
                status = resp.status
        except TimeoutError as err:  # pragma: no cover - network
            raise MoinCardApiError(0, "timeout") from err
        except aiohttp.ClientError as err:  # pragma: no cover - network
            raise MoinCardApiError(0, str(err)) from err

        if status in (401, 403) and auth and _retry:
            # Token expired -> login again and retry once.
            _LOGGER.debug("MoinCard token rejected (%s), re-authenticating", status)
            await self.async_login()
            return await self._request(method, path, body=body, auth=auth, _retry=False)

        if status == 409:
            raise MoinCardConflictError(text)
        if status >= 400:
            raise MoinCardApiError(status, text[:300])

        if not text.strip():
            return None
        try:
            import json

            return json.loads(text)
        except ValueError:
            return text

    # -- auth --------------------------------------------------------------
    async def async_login(self) -> str:
        data = await self._request(
            "POST",
            "/api/login",
            body={"username": self._username, "password": self._password},
            auth=False,
        )
        if not isinstance(data, dict) or not data.get("token"):
            raise MoinCardAuthError(f"no token in login response: {data!r}")
        self._token = data["token"]
        return self._token

    async def async_validate(self) -> None:
        """Log in and confirm the account is usable."""
        await self.async_login()
        await self.async_get_lists()

    # -- lists -------------------------------------------------------------
    async def async_get_lists(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/shoppinglist/lists")
        if isinstance(data, dict):
            data = data.get("lists") or data.get("data") or []
        return data or []

    async def async_get_list(self, internal_id: str) -> ShoppingList:
        data = await self._request(
            "POST", "/api/shoppinglist/list", body={"internalId": internal_id}
        )
        return ShoppingList.from_json(data or {})

    async def async_create_list(self, name: str) -> ShoppingList:
        data = await self._request(
            "POST", "/api/shoppinglist/create", body={"id": 0, "name": name}
        )
        return ShoppingList.from_json(data or {})

    async def async_delete_list(self, internal_id: str) -> None:
        await self._request(
            "DELETE", f"/api/shoppinglist/delete?internalId={internal_id}"
        )

    # -- vocabulary / suggestions -----------------------------------------
    async def async_get_vocabulary(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/shoppinglist/vocabulary/list")
        return data or []

    async def async_get_standard_list(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/shoppinglist/vocabulary/standardlist")
        return data or []

    async def async_create_vocabulary_item(
        self, name: str, category: str | None
    ) -> None:
        await self._request(
            "POST",
            "/api/shoppinglist/vocabulary/create",
            body={"name": name, "category": category, "selfCreated": True},
        )

    # -- items -------------------------------------------------------------
    @staticmethod
    def _item_payload(
        lst: ShoppingList,
        *,
        item_id: int,
        name: str,
        quantity: int,
        done: bool,
        category: str | None,
        gtin: str | None,
        unit: str | None,
        sku: str | None,
        self_created: bool = True,
        image_url: str | None = None,
    ) -> dict[str, Any]:
        return {
            "id": item_id,
            "shoppingListId": lst.id,
            "name": name,
            "unit": unit,
            "done": done,
            "sku": sku,
            "selfCreated": self_created,
            "category": category,
            "quantity": quantity,
            "imageUrl": image_url,
            "gtin": gtin,
        }

    async def async_add_item(
        self,
        lst: ShoppingList,
        name: str,
        *,
        quantity: int = 1,
        category: str | None = None,
        gtin: str | None = None,
        unit: str | None = None,
        sku: str | None = None,
    ) -> ShoppingList:
        """Add a new item.  For new items ``addQuantity`` is the quantity."""
        item = self._item_payload(
            lst,
            item_id=0,
            name=name,
            quantity=quantity,
            done=False,
            category=category,
            gtin=gtin,
            unit=unit,
            sku=sku,
        )
        data = await self._request(
            "POST",
            "/api/shoppinglist/item/update",
            body={
                "internalId": lst.internal_id,
                "shoppingListItem": item,
                "addQuantity": quantity,
            },
        )
        return ShoppingList.from_json(data or {})

    async def async_update_item(
        self,
        lst: ShoppingList,
        item: dict[str, Any],
        *,
        name: str | None = None,
        quantity: int | None = None,
        done: bool | None = None,
        category: str | None = None,
        gtin: str | None = None,
        unit: str | None = None,
    ) -> ShoppingList:
        """Update an existing item.

        The API is optimistic: the ``quantity`` field in the body must equal the
        server's current quantity, otherwise a 409 conflict is raised.  The
        delta is passed via ``addQuantity``.
        """
        current_qty = item_quantity(item)
        target_qty = current_qty if quantity is None else max(int(quantity), 1)
        payload = self._item_payload(
            lst,
            item_id=item["id"],
            name=item.get("name") if name is None else name,
            quantity=current_qty,
            done=item.get("done", False) if done is None else done,
            category=item.get("category") if category is None else category,
            gtin=item.get("gtin") if gtin is None else gtin,
            unit=item.get("unit") if unit is None else unit,
            sku=item.get("sku"),
            self_created=item.get("selfCreated", True),
            image_url=item.get("imageUrl"),
        )
        data = await self._request(
            "POST",
            "/api/shoppinglist/item/update",
            body={
                "internalId": lst.internal_id,
                "shoppingListItem": payload,
                "addQuantity": target_qty - current_qty,
            },
        )
        return ShoppingList.from_json(data or {})

    async def async_set_done(
        self, lst: ShoppingList, item: dict[str, Any], done: bool
    ) -> ShoppingList:
        payload = self._item_payload(
            lst,
            item_id=item["id"],
            name=item.get("name"),
            quantity=item_quantity(item),
            done=done,
            category=item.get("category"),
            gtin=item.get("gtin"),
            unit=item.get("unit"),
            sku=item.get("sku"),
            self_created=item.get("selfCreated", True),
            image_url=item.get("imageUrl"),
        )
        data = await self._request(
            "POST",
            "/api/shoppinglist/item/done",
            body={
                "internalId": lst.internal_id,
                "shoppingListItem": payload,
                "done": done,
            },
        )
        return ShoppingList.from_json(data or {})

    async def async_delete_item(
        self, lst: ShoppingList, item_id: int
    ) -> ShoppingList | None:
        data = await self._request(
            "DELETE",
            f"/api/shoppinglist/item/delete?internalId={lst.internal_id}&itemId={item_id}",
        )
        return ShoppingList.from_json(data or {}) if data else None

    async def async_delete_all_items(self, lst: ShoppingList) -> ShoppingList | None:
        data = await self._request(
            "DELETE",
            f"/api/shoppinglist/item/deleteAll?internalId={lst.internal_id}",
        )
        return ShoppingList.from_json(data or {}) if data else None
