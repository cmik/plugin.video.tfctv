# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Kodi (19+, Python 3) video add-on, `plugin.video.tfctv` ("iWantTFC"), that scrapes/calls the iWantTFC website and API (`api.iwanttfc.com`, `www.iwanttfc.com`). It is unofficial. There is no build system, linter, or test suite: the code only runs inside Kodi (it imports `xbmc`, `xbmcgui`, `xbmcaddon`, etc.), so it cannot be run standalone. Verify changes by reading Kodi's log (`~/Library/Logs/kodi.log` on macOS; enable the add-on's `debug` setting; `logger` in `resources/lib/libraries/logger.py` writes to it). Kodi runs its own installed copy in `~/Library/Application Support/Kodi/addons/plugin.video.tfctv/`, not this folder, so edits here have no effect until copied there (it is a plain copy, not a symlink).

`test_api.py` is a standalone scratch script (plain urllib + cookie file) for poking at the web API outside Kodi; it is gitignored along with `notes2`, `test_cookies.txt`, `API_MAP.md` and `REFACTORING_SUMMARY.md`. The `notes` file and `kodi.log` are untracked scratch files and may contain captured requests with credentials: never copy their contents anywhere.

Releases: bump `version` and `<news>` in `addon.xml`, add to `changelog.txt`, and regenerate `addon.xml.md5`.

## Architecture

Entry points (declared in `addon.xml`):
- `default.py`: plugin entry. Parses `sys.argv[2]` into params, then dispatches on an integer `mode` through one large `if/elif` chain. Mode constants live in `resources/config.py` (alongside base URLs, user agents, DB paths). Navigation modes call `resources/lib/indexers/navigator.py` (`navigator` class builds Kodi directory listings); action modes call `tfctv` functions directly. It also runs `resources/upgrade.py` (DB/settings migration) when `lastVersion` differs from the add-on version.
- `service.py`: background service started at Kodi startup: a local HTTP proxy (`ProxyHandler`, used for streaming with cookies/headers) and the library checker.

Source layer, `resources/lib/sources/`:
- `tfctv.py` is only a backwards-compatibility facade that re-exports everything from the `tfctv/` package. Callers do `from resources.lib.sources import tfctv` and use `tfctv.someFunction()`. When adding a function to a submodule, also export it in `tfctv.py` (and `tfctv/__init__.py` `__all__`) or callers won't see it.
- `tfctv/` modules: `api.py` (HTTP via urllib with a shared cookie jar/opener, `callServiceApi`/`callJsonApi`; call `reset_opener()` after cookie changes), `auth.py` (email/password and Facebook login against the iwanttfc API; the login flow was recently reworked), `user.py` (profile, subscription, devices, fingerprint/geo), `catalog.py` (shows, episodes, website home sections, my list, search; the largest module), `playback.py` (resolving media info and playing episodes/live streams), `library.py` (export to the Kodi library, NFO generation), `utils.py`.
- `tfctv.py.backup` is the pre-refactor monolith, kept only for reference.

Persistence: `resources/lib/models/` holds sqlite-backed models (`Model` base class; `shows`, `episodes`, `showcast`, `celebrities`, `history`, `library`) exposed as `showDB`, `episodeDB`, `libraryDB`, `castDB`. Caching goes through `resources/lib/libraries/cache.py`, `executioncache.py` and `resources/lib/cache/SimpleCache.py`. `resources/lib/libraries/control.py` wraps Kodi APIs (settings, dialogs, string lookup via `control.lang(id)`, paths); `trakt.py` is a new, uncommitted Trakt integration. Localized strings are in `resources/language/` and settings UI in `resources/settings.xml`.

The branch `nw_adapt_v3` is adapting the add-on to the new iWantTFC website/API (v3.0.0 beta). `API_MAP.md` (local) documents the endpoints used by each `tfctv/` module.

## Playback / DRM notes

Playback uses Widevine through `inputstream.adaptive`: `retrieveMediaInfo()` calls `POST /entitlement/playback/start/{id}` and returns an MPD URL plus an EZDRM license URL (short-lived JWT in `CustomData`, about 2 minutes). EZDRM returns a raw binary license, so `response_data` in the `license_key` must stay empty (not `JBlicense`). The request body must mirror the website's, including `deviceId`, otherwise the license token carries `deviceId: unknown` and EZDRM answers `ACCESS_DENIED` ("License update not successful (no keys)" in the log).

Environment requirement found while debugging: Kodi 21+ with the current Widevine CDM (4.10.3112.0 at the time). Kodi 20.1 crashes with SIGILL in `libwidevinecdm.dylib` (`VerifyCdmHost_0`) on that CDM, and the older CDM 4.10.2934.0 gets `ACCESS_DENIED`. Crash reports are in `~/Library/Logs/DiagnosticReports/Kodi-*.ips`.
