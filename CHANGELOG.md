# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-03-07

### Added
- **UI Improvements**: Removed redundant version strings from the live terminal display in the frontend for a cleaner, more professional look. 

### Fixed
- **Version Consistency**: Updated version numbers to `1.0.1` consistently across the entire project (Web GUI footer, Desktop GUI title, and CLI outputs).
- **Code Quality**: Applied extensive Python Type Hinting (`-> None`, `Optional`, `subprocess.Popen`) and improved exception handling to `desktop_gui.py` and `web_gui.py` to match the strict professional standards of the main API server.
- **CLI Initialization**: Resolved a `NameError` crash in `start.py` by correctly parsing required arguments natively in Layer 7 methods.
- **SSL Context**: Suppressed redundant `DeprecationWarning`s for `ssl.OP_NO_TLSv1` by correctly assigning `minimum_version = ssl.TLSVersion.TLSv1_2` instead of using deprecated boolean flags.
- **Proxy URLs**: Replaced `PyRoxy` with a custom native Regex parser in `start.py` to correctly parse proxy formats from online lists (like `monosans/proxy-list`), resolving false empty results.
- **Backend Stability**: Fixed a global variable overwrite bug in `api.py` that incorrectly forced `all.txt` as a proxy file when proxy-type "All Proxies" was selected, overriding user URLs.
- **Code Quality**: Applied extensive Python Type Hinting (`-> None`, `Dict`, etc.) across all core Engine Methods (Layer 7 & Layer 4) and FastAPI endpoints inside `api.py` to meet strict AI Agent standards (`Python Pro`, `FastAPI Expert`).
- **Dependencies**: Upgraded heavily outdated `requests`, `urllib3`, `chardet`, and `PySocks` packages in VENV, fixing `RequestsDependencyWarning`.

## [1.0.0] - 2026-03-07

### Added

- **MHDDoS-GUI Release**: Created a powerful dual-architecture GUI (Web Dashboard and Desktop App) for MHDDoS.
- **Frontend**: Designed a modern, glassmorphism UI using React/Vite aesthetics via Tailwind CSS. Added real-time log terminal, proxy selection file browser, responsive layouts, all 57 attack methods categorized, auto-saving memory, and a dynamic contextual UI (hides irrelevant inputs based on attack layer).
- **Backend (API)**: Implemented FastAPI backend to manage subprocesses (`start.py`) and stream logs via WebSockets.
- **Proxy System**: Added support for fetching proxies entirely in-memory directly from HTTP/HTTPS URLs continuously without cluttering local storage.

### Fixed

- **App Stability**: Prevented crashes and race conditions by preventing overlapping attacks from being spammed on the GUI. Fixed `AttributeError` tracebacks on DDoS termination.
- **CLI Resilience**: Fixed an unhandled `ValueError` in `start.py` that would crash if thread configs were entered as non-integers, replacing it with a clean fallback. Wrapped external subprocess components (e.g. `bombardier`) safely to prevent thread bleeding and silent crashes.
- **Proxy Resolution**: Fixed pathing bug in `All Proxy` dropdown mode that incorrectly referenced `proxies/all.txt` instead of `all.txt`.
