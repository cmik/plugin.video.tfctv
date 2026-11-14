# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Kodi (19+, Python 3) video add-on, `plugin.video.tfctv` ("iWantTFC"), that scrapes/calls the iWantTFC website and API (`api.iwanttfc.com`, `www.iwanttfc.com`). It is unofficial. There is no build system or linter, and the only tests (`tests/`) cover the models, user data and catalog seed with a faked `control` module: the rest of the code only runs inside Kodi (it imports `xbmc`, `xbmcgui`, `xbmcaddon`, etc.), so it cannot be run standalone. Verify changes by reading Kodi's log (`~/Library/Logs/kodi.log` on macOS; enable the add-on's `debug` setting; `logger` in `resources/lib/libraries/logger.py` writes to it). Kodi runs its own installed copy in `~/Library/Application Support/Kodi/addons/plugin.video.tfctv/`, not this folder, so edits here have no effect until copied there (it is a plain copy, not a symlink).

`test_api.py` is a standalone scratch script (plain urllib + cookie file) for poking at the web API outside Kodi; it is gitignored along with `notes2`, `test_cookies.txt`, `API_MAP.md` and `REFACTORING_SUMMARY.md`. The `notes` file and `kodi.log` are untracked scratch files and may contain captured requests with credentials: never copy their contents anywhere.

Releases: bump `version` and `<news>` in `addon.xml`, add to `changelog.txt`, and regenerate `addon.xml.md5`.

## Architecture

Entry points (declared in `addon.xml`):
- `default.py`: plugin entry. Parses `sys.argv[2]` into params, then dispatches on an integer `mode` through one large `if/elif` chain. Mode constants live in `resources/config.py` (alongside base URLs, user agents, DB paths). Navigation modes call `resources/lib/indexers/navigator.py` (`navigator` class builds Kodi directory listings); action modes call `tfctv` functions directly. It also runs `resources/upgrade.py` (DB/settings migration) when `lastVersion` differs from the add-on version.
- `service.py`: background service started at Kodi startup: a local HTTP proxy (`ProxyHandler`, used for streaming with cookies/headers) and the library checker.

Source layer, `resources/lib/sources/`:
- `tfctv/` is a package: callers do `from resources.lib.sources import tfctv` and use `tfctv.someFunction()`. `tfctv/__init__.py` star-imports its submodules; when adding a function, make sure it is public (no leading underscore) in its submodule.
- `tfctv/` modules: `api.py` (HTTP via urllib with a shared cookie jar/opener, `callServiceApi`/`callJsonApi`; call `reset_opener()` after cookie changes), `auth.py` (email/password and Facebook login against the iwanttfc API; the login flow was recently reworked), `user.py` (profile, subscription, devices, fingerprint/geo), `catalog.py` (shows, episodes, my list, search, catalog refresh; it re-exports what moved out of it), `graphql.py` (the website GraphQL calls), `formatters.py` (assets to add-on structures), `rails.py` (website collections and rails), `db.py` (the `showDB`/`episodeDB`/`castDB` instances), `playback.py` (resolving media info and playing episodes/live streams), `library.py` (export to the Kodi library, NFO generation), `utils.py`.

Persistence: `resources/lib/models/` holds sqlite-backed models (`Model` base class; `shows`, `episodes`, `showcast`, `celebrities`, `history`, `library`) exposed as `showDB`, `episodeDB`, `libraryDB`, `castDB`. Caching goes through `resources/lib/libraries/cache.py`, `executioncache.py` and `resources/lib/cache/SimpleCache.py`. `resources/lib/libraries/control.py` wraps Kodi APIs (settings, dialogs, string lookup via `control.lang(id)`, paths); `trakt.py` is a new, uncommitted Trakt integration. Localized strings are in `resources/language/` and settings UI in `resources/settings.xml`.

User data is kept apart from the catalog: `userdata.db` (`models/userdata.py`: `MYLIST`, `STATS` = views/rating/votes of shows and episodes, `META`). `Show`/`Episode` add these fields to what they read (`_applyUserData`) and route `update()` of `mylist`/`views`/`rating`/`votes` to it; `set()` never writes them in the catalog databases. The catalog databases (shows, episodes, celebrities) are a cache that can be refreshed, reset or replaced. Previous versions stored My List and the counters in the catalog columns: `UserData.importLegacy()` moves them once (upgrade, and before a catalog reset).

Cast (`models/showcast.py`, table `SHOW_CAST` with a `SOURCE` column): `getShow` stores the cast the API gives (`replaceApiCast`, source `api`, rewritten at each refresh) and `getCast` returns it followed by the actors only the old catalog knew (source `legacy`). The legacy links are `resources/data/legacy_cast.json`, built by `.github/scripts/build_legacy_cast.py` from the old databases (matched to the current shows by title) and merged once at upgrade (`libraries/legacycast.py`, which also purges the rows stored before `SOURCE` existed).

Catalog seed (`resources/lib/libraries/seed.py`): on a first installation or an update from a version < 3 (`seedReason`), `tools.importDBFiles()` downloads `catalog-seed.zip` + `manifest.json` from the GitHub release tagged `catalog-seed` (setting `catalogSeedURL`), checks sha256 and the databases, keeps the replaced ones as `.bak`, remaps My List by title if ids changed, then starts `catchUpCatalog` in the background (loads the shows that are new since the seed). Build and publish a seed from a profile whose catalog was loaded (Reload Catalog Cache with episodes):

    python3 .github/scripts/build_seed.py "$HOME/Library/Application Support/Kodi/userdata/addon_data/plugin.video.tfctv" /tmp/seed
    gh release create catalog-seed /tmp/seed/catalog-seed.zip /tmp/seed/manifest.json --title "Catalog seed" --notes "..."   # first time
    gh release upload catalog-seed /tmp/seed/catalog-seed.zip /tmp/seed/manifest.json --clobber                              # next ones

Tests (outside Kodi, run in CI): `python -m unittest discover -s tests`.

The branch `nw_adapt_v3` is adapting the add-on to the new iWantTFC website/API (v3.0.0 beta). `API_MAP.md` (local) documents the endpoints used by each `tfctv/` module.

## Playback / DRM notes

Playback uses Widevine through `inputstream.adaptive`: `retrieveMediaInfo()` calls `POST /entitlement/playback/start/{id}` and returns an MPD URL plus an EZDRM license URL (short-lived JWT in `CustomData`, about 2 minutes). EZDRM returns a raw binary license, so `response_data` in the `license_key` must stay empty (not `JBlicense`). The request body must mirror the website's, including `deviceId`, otherwise the license token carries `deviceId: unknown` and EZDRM answers `ACCESS_DENIED` ("License update not successful (no keys)" in the log).

Environment requirement found while debugging: Kodi 21+ with the current Widevine CDM (4.10.3112.0 at the time). Kodi 20.1 crashes with SIGILL in `libwidevinecdm.dylib` (`VerifyCdmHost_0`) on that CDM, and the older CDM 4.10.2934.0 gets `ACCESS_DENIED`. Crash reports are in `~/Library/Logs/DiagnosticReports/Kodi-*.ips`.
