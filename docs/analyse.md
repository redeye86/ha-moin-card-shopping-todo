# App-Analyse / Decompiling

## Artefakt

- Datei: `MOIN-CARD_2.28.1_APKPure.xapk` (XAPK = ZIP mit Base-APK + Splits)
- Package: `de.buenting.moincard`, Version 2.28.1 (VersionCode 3302)
- Splits: `de.buenting.moincard.apk` (base), `config.arm64_v8a.apk` (nativer Code),
  `config.de.apk`, `config.en.apk`, `config.xxhdpi.apk`
- Es ist eine **Flutter-App** (Dart-AOT in `lib/arm64-v8a/libapp.so`).

## Dart-/Flutter-Version

- `libflutter.so` enthält: `3.13.4 (stable) (Tue Sep 15 01:01:15 2026 -0700) on "android_arm64"`
  → **Dart 3.13.4**.
- Dart 3.13 vereint die AOT-Snapshots: statt der vier Symbole
  `_kDartVmSnapshotData` / `_kDartVmSnapshotInstructions` /
  `_kDartIsolateSnapshotData` / `_kDartIsolateSnapshotInstructions` gibt es nur
  noch **`_kDartSnapshotData`** und **`_kDartSnapshotText`** (plus
  `_kDartSnapshotBuildId`).

## Dekompilieren mit blutter

[blutter](https://github.com/worawit/blutter) liest `libapp.so`/`libflutter.so`
und erzeugt Assembler (`asm/`), `pp.txt`, `objs.txt` und ein Frida-Skript.

Ablauf:

1. `git clone https://github.com/worawit/blutter`
2. Patch **PR #230** ("Support Dart 3.13.x unified AOT snapshots") anwenden –
   ohne ihn scheitert der Loader mit `ELF: Cannot find Dart VM Snapshot Data`,
   weil er die alten 4 Symbole erwartet. Der Patch bringt u. a. über
   `BLUTTER_DART_SINGLE_SNAPSHOT` / Symbol-Fallback `_kDartSnapshotData` bei.
3. blutter lädt den passenden Dart-SDK-Quellcode (`3.13.4` als Git-Tag) und
   baut daraus eine Dart-VM-Bibliothek (nur `runtime`, `tools`,
   `third_party/double-conversion`).
4. blutter selbst wird gegen diese Bibliothek gebaut und liest `libapp.so`.

### Toolchain-Hürden (Debian-Container, kein root)

- `cmake`, `ninja`, `pyelftools`, `requests` per `pip`.
- `libicu-dev` + `libcapstone-dev` + `pkgconf` als `.deb` heruntergeladen und
  lokal entpackt (`dpkg-deb -x` → eigenes Prefix).
- Die ICU-`.so`-Symlinks zeigten „ins Leere" → verlinkte versionierte
  Symlinks auf die System-.so. Ohne das linkt der Blutter-Static-Link gegen
  `libicuuc.a` und scheitert an `icudt76_dat`.
- Ergebnis: `bin/blutter_dartvm3.13.4_android_arm64`.

### Bekanntes Artefakt

Der PR-Patch hat einen kleinen Bug in der String-Auflösung: manche Strings
zeigen im Decompile nur `"n"`/`"ln"` (z. B. Methodenname `markShoppingListItemWithCartItem`
→ `n`). Die Rohstrings im `libapp.so` sind aber korrekt und wurden per
`strings`/`grep -a` gegengelesen.

## Wichtige Klassen/Pfade in der App

| Pfad (`package:...`) | Zweck |
| --- | --- |
| `moincard_shared/repository/repository.dart` | die zentrale API-Schicht (`Repository`) |
| `moincard_shared/repository/json_client.dart` | HTTP-Client, Header, Auth |
| `moincard_shared/shoppinglist/shoppinglist_bloc.dart` | Einkaufslisten-Logik |
| `moincard_shared/shopping/shopping_bloc.dart` | Scan & Go / Cart |
| `moincard_shared/common/utils.dart` | `AppUrls`, Basis-URLs, User-Agent |
| `moincard_shared/model/shoppinglist*.dart` | Modelle (`toJson`/`fromJson`) |

## Basis-URLs aus `AppUrls`

```dart
moincardBaseUrl    = "https://www.moincard.de"
combiBaseUrl       = "https://www.combi.de"
familaBaseUrl      = "https://www.famila-nordwest.de"
moincardWebBaseUrl = "https://www.moincard.de/inapp/"
```

Test-/Staging-Hosts tauchen als Strings auf: `test.moincard.de`, `test.combi.de`,
`test.mytime.de`.

## AndroidManifest (Auszug)

App-Links (autoVerify) auf `www.moincard.de` für:
- `/register/.*`
- `/secure/recover/user/password/.*`
- `/inapp/.*`  ← u. a. `/inapp/teile_einkaufsliste?shoppingListId=...`

## Reproduzieren

```bash
unzip MOIN-CARD_*.xapk -d xapk/
unzip xapk/config.arm64_v8a.apk 'lib/arm64-v8a/*' -d libs/
# blutter (siehe oben) bauen, dann:
python blutter.py libs/lib/arm64-v8a out/
```
