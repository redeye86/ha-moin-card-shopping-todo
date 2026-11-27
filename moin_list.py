#!/usr/bin/env python3
"""MOIN-CARD Einkaufslisten-PoC.

Reverse-engineered aus der Android-App de.buenting.moincard 2.28.1
(Flutter/Dart 3.13.4, libapp.so via blutter dekompiliert).

Basis-URL (AppUrls.moincardBaseUrl): https://www.moincard.de

Endpunkte:
  POST /api/login                     {"username","password"}
                                      -> {"token": "...", "username": "..."}
  GET  /api/shoppinglist/lists        -> [{"id","name","internalId"}, ...]
  POST /api/shoppinglist/list         {"internalId": <internalId>}
                                      -> {"shoppingList": {...},
                                          "shoppingListItems": [item, ...]}
  POST /api/shoppinglist/create       {"id": 0, "name": <name>}
                                      -> {"shoppingList": {...}, "shoppingListItems": []}
  POST /api/shoppinglist/item/update  {"internalId": <internalId>,
                                       "shoppingListItem": {item},
                                       "addQuantity": <int>}
  POST /api/shoppinglist/item/done    {"internalId", "shoppingListItem", ...}

  Wichtig:
  - Die Liste hat eine numerische `id` (z.B. 306336) UND einen Hex-String
    `internalId` (z.B. "948ff9fa..."). Im Request-Body wird `internalId`
    (String) verwendet, im Item-Feld `shoppingListId` aber die numerische `id`.
  - Ein neues Item hat `id: 0`; der Server vergibt die echte id.
  - Fehlt der Kunden-Datensatz (customerId null), antwortet /api/shoppinglist/*
    mit 404 "Kunde nicht gefunden." -> siehe Hinweis unten.

Item-Felder (ShoppingListItem.toJson):
  id (int), shoppingListId (int), name (str), unit (str),
  done (bool), sku (str), selfCreated (bool), category (str),
  quantity (int), imageUrl (str), gtin (str)

Hinweis Kunde anlegen (falls Account noch keinen Kunden hat):
  POST /api/customer mit u.a. salutation (int, 0=Herr), name, firstName,
  street, streetNumber, postal, city, dateOfBirth ("dd.MM.yyyy"),
  domesticMarket (Markt-id aus GET /api/portal/shops), email.
  -> 201 Created, vergibt customerId + digitale cardnumber.

Feste Header laut JsonClient._addHeaders:
  x-api-key: jsdirjgldd4453ldsjkfjfkeiweucxhjskdldoe
  accept: application/json
  content-type: application/json; charset=utf-8
  x-auth-token: <token aus /api/login>

Aufruf:
  export MOIN_USER='mail@example.com'
  export MOIN_PASS='geheim'
  python3 moin_list.py lists
  python3 moin_list.py create "Einkaufsliste"   # falls noch keine existiert
  python3 moin_list.py show
  python3 moin_list.py show --list-id 306336
  python3 moin_list.py add "Milch" "Brot" "Eier"
  python3 moin_list.py add --qty 3 "Bananen"
  python3 moin_list.py addfile einkauf.txt      # eine Zutat pro Zeile
  python3 moin_list.py --raw lists              # volle Serverantwort anzeigen

`add` legt automatisch eine "Einkaufsliste" an, falls noch keine existiert.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = "https://www.moincard.de"
API_KEY = "jsdirjgldd4453ldsjkfjfkeiweucxhjskdldoe"
TIMEOUT = 30


class ApiError(RuntimeError):
    def __init__(self, status, url, body):
        super().__init__(f"HTTP {status} for {url}: {body[:300]}")
        self.status = status
        self.url = url
        self.body = body


class MoinClient:
    def __init__(self, base_url: str = BASE_URL, debug: bool = False):
        self.base_url = base_url.rstrip("/")
        self.debug = debug
        self.token: str | None = None

    # -- low level ---------------------------------------------------------
    def _request(self, method: str, path: str, body=None, auth: bool = True):
        url = path if path.startswith("http") else self.base_url + path
        data = None
        headers = {
            "x-api-key": API_KEY,
            "accept": "application/json",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["content-type"] = "application/json; charset=utf-8"
        if auth and self.token:
            headers["x-auth-token"] = self.token
        if self.debug:
            print(f">>> {method} {url}", file=sys.stderr)
            if body is not None:
                print(f"    body: {json.dumps(body, ensure_ascii=False)}", file=sys.stderr)

        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            raise ApiError(e.code, url, raw) from None
        except urllib.error.URLError as e:
            raise ApiError(0, url, str(e.reason)) from None

        if self.debug:
            print(f"<<< {raw[:500]}", file=sys.stderr)
        if not raw.strip():
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def get(self, path, auth: bool = True):
        return self._request("GET", path, auth=auth)

    def post(self, path, body=None, auth: bool = True):
        return self._request("POST", path, body=body, auth=auth)

    # -- API ---------------------------------------------------------------
    def login(self, username: str, password: str) -> str:
        resp = self.post("/api/login", {"username": username, "password": password}, auth=False)
        if not isinstance(resp, dict) or not resp.get("token"):
            raise ApiError(0, "/api/login", f"kein Token in Antwort: {resp!r}")
        self.token = resp["token"]
        return self.token

    def lists(self):
        resp = self.get("/api/shoppinglist/lists")
        if isinstance(resp, dict):  # falls der Server {lists:[...]} liefert
            resp = resp.get("lists", resp.get("data", resp))
        return resp or []

    def resolve_list(self, selector=None, create: bool = True, name: str = "Einkaufsliste"):
        """Liefert den Listen-Eintrag {id, name, internalId} der Hauptliste.

        selector: falls gesetzt, wird die Liste mit dieser internalId (oder id) gewaehlt.
        create:   legt eine "Einkaufsliste" an, falls noch keine existiert.
        """
        entries = self.lists()
        if selector is not None:
            for e in entries:
                if str(e.get("internalId")) == str(selector) or str(e.get("id")) == str(selector):
                    return e
            return {"id": selector, "name": name, "internalId": selector}
        if entries:
            for e in entries:
                if (e.get("name") or "").lower() == name.lower():
                    return e
            return entries[0]
        if not create:
            raise RuntimeError("Keine Einkaufsliste im Account vorhanden.")
        return self.create_list(name)

    def create_list(self, name: str = "Einkaufsliste"):
        """Legt eine neue Liste an (id=0, Server vergibt id/internalId)."""
        resp = self.post("/api/shoppinglist/create", {"id": 0, "name": name})
        return resp.get("shoppingList", resp) if isinstance(resp, dict) else resp

    def show_list(self, list_entry):
        if isinstance(list_entry, dict):
            internal = list_entry.get("internalId")
        else:
            internal = list_entry
        return self.post("/api/shoppinglist/list", {"internalId": internal})

    def add_item(self, list_entry, name: str, quantity: int = 1):
        # internalId ist der Hex-String der Liste, shoppingListId die numerische id.
        if isinstance(list_entry, dict):
            internal = list_entry.get("internalId")
            numeric_id = list_entry.get("id")
        else:
            internal = list_entry
            numeric_id = list_entry
        item = {
            "id": 0,
            "shoppingListId": numeric_id,
            "name": name,
            "unit": None,
            "done": False,
            "sku": None,
            "selfCreated": True,
            "category": None,
            "quantity": quantity,
            "imageUrl": None,
            "gtin": None,
        }
        body = {
            "internalId": internal,
            "shoppingListItem": item,
            "addQuantity": quantity,
        }
        return self.post("/api/shoppinglist/item/update", body)


def _print_lists(lists):
    if not lists:
        print("(keine Listen)")
        return
    for e in lists:
        if isinstance(e, dict):
            print(f"  internalId={e.get('internalId'):<10} id={e.get('id'):<10} {e.get('name')}")


def _print_items(resp):
    lst = resp.get("shoppingList", {}) if isinstance(resp, dict) else {}
    items = resp.get("shoppingListItems", []) if isinstance(resp, dict) else []
    print(f"Liste: {lst.get('name', '?')} (internalId={lst.get('internalId', '?')}, "
          f"{len(items)} Einträge)")
    for it in items:
        mark = "x" if it.get("done") else " "
        print(f"  [{mark}] {it.get('quantity')}x {it.get('name')}  (id={it.get('id')})")


def main():
    p = argparse.ArgumentParser(description="MOIN-CARD Einkaufslisten-PoC")
    p.add_argument("--raw", action="store_true", help="Rohantwort ausgeben")
    p.add_argument("--debug", action="store_true", help="HTTP-Requests/Responses loggen")
    p.add_argument("--base-url", default=os.environ.get("MOIN_BASE_URL", BASE_URL))
    p.add_argument("--user", default=os.environ.get("MOIN_USER"))
    p.add_argument("--password", default=os.environ.get("MOIN_PASS"))

    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("lists")
    sp_show = sub.add_parser("show")
    sp_show.add_argument("--list-id", default=None)
    sp_add = sub.add_parser("add")
    sp_add.add_argument("--list-id", default=None)
    sp_add.add_argument("--no-create", action="store_true",
                        help="keine Liste anlegen, falls noch keine existiert")
    sp_add.add_argument("--qty", type=int, default=1)
    sp_add.add_argument("items", nargs="+")
    sp_file = sub.add_parser("addfile")
    sp_file.add_argument("--list-id", default=None)
    sp_file.add_argument("--qty", type=int, default=1)
    sp_file.add_argument("file")
    sp_create = sub.add_parser("create")
    sp_create.add_argument("name", nargs="?", default="Einkaufsliste")

    args = p.parse_args()

    if not args.user or not args.password:
        print("Fehler: MOIN_USER / MOIN_PASS (oder --user/--password) setzen.", file=sys.stderr)
        return 2

    client = MoinClient(args.base_url, debug=args.debug)
    try:
        client.login(args.user, args.password)
    except ApiError as e:
        print(f"Login fehlgeschlagen: {e}", file=sys.stderr)
        return 1

    try:
        if args.cmd == "lists":
            data = client.lists()
            if args.raw:
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                _print_lists(data)

        elif args.cmd == "create":
            entry = client.create_list(args.name)
            print(f"Liste angelegt: {entry.get('name')} "
                  f"(id={entry.get('id')}, internalId={entry.get('internalId')})")

        elif args.cmd == "show":
            entry = client.resolve_list(args.list_id)
            resp = client.show_list(entry)
            if args.raw:
                print(json.dumps(resp, indent=2, ensure_ascii=False))
            else:
                _print_items(resp)

        elif args.cmd == "add":
            entry = client.resolve_list(args.list_id, create=not args.no_create)
            for name in args.items:
                resp = client.add_item(entry, name, args.qty)
                print(f"+ {args.qty}x {name} -> ok")
            if args.raw:
                print(json.dumps(resp, indent=2, ensure_ascii=False))

        elif args.cmd == "addfile":
            entry = client.resolve_list(args.list_id)
            with open(args.file, encoding="utf-8") as fh:
                names = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
            for name in names:
                client.add_item(entry, name, args.qty)
                print(f"+ {args.qty}x {name}")
    except ApiError as e:
        print(f"API-Fehler: {e}", file=sys.stderr)
        if e.status == 500:
            print("Hinweis: 500 kann heißen, dass der Aufruf aus dieser "
                  "Netzwerk-Umgebung/Region blockiert wird, oder dass die "
                  "Nutzlast nicht passt.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
