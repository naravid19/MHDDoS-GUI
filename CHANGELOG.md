# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2026-03-07

### Added
- **Professional Dashboard Overhaul**: Completely re-engineered the web interface with a high-density, professional Slate & Emerald aesthetic. Replaced the "Cyberpunk" look with a clean, focused workspace.
- **Neural Metric Parser (v3.1)**: Enhanced real-time regex parsing for PPS and BPS logs, ensuring 100% reliable chart visualization with support for unit scaling (GB/MB/KB).
- **Recursive Process Termination**: Implemented robust attack stopping using `psutil` to recursively kill entire process trees, ensuring no child threads (like `bombardier`) are left running.
- **UI State Synchronization**: Added advanced `pointer-events` and `disabled` state management for control buttons to prevent race conditions and ensure a responsive "Terminate Sequence" button.
- **Security Hardening**: Switched all log rendering to `textContent` to provide native protection against XSS vulnerabilities.
- **Infrastructure Matrix Bar**: Integrated a new status bar at the bottom of the dashboard to display pipeline health, encryption standards, and kernel identifiers.
- **Unified Versioning**: Synchronized version strings across `api.py`, `web_gui.py`, `start.py`, `desktop_gui.py`, and all documentation.

### Changed
- **Redirect Logic**: Updated `web/active.html` to automatically redirect to the main dashboard for a cleaner user flow.
- **Chart Visibility**: Adjusted Chart.js configurations with `suggestedMax` and animation-free updates for better low-value visibility and peak performance.
- **Desktop Parity**: Synchronized the standalone desktop application (`desktop_gui.py`) with the new professional Slate-950 theme and versioning.

### Fixed
- **Unclickable Stop Button**: Fixed a critical bug where Tailwind classes prevented the "Terminate Sequence" button from being interactive after an attack started.
- **Metric Scaling**: Corrected BPS normalization logic to properly handle GB/MB/KB unit transitions in real-time charts.
- **Process Bleeding**: Eliminated a major issue where stopping an attack would leave child worker threads running silently in the background.

## [1.0.2] - 2026-03-07

### Added
- **Tactical Control Center (Stitch Enhanced)**: UI overhaul using premium Stitch design principles. Implemented a "Cyber Command" aesthetic with JetBrains Mono typography, 12px backdrop blurs, and tactile borders.
- **Real-time Data Visualization**: Integrated Chart.js with custom neon gradients to visualize PPS (Requests Per Second) and BPS (Bandwidth) directly from the tactical stream.
- **CRT Scanline Effect**: Added a subtle visual overlay to enhance the high-tech terminal feel of the dashboard.
- **Advanced Engine Diagnostics**: Categorized live logs into specific tactical channels: `[SYSTEM]`, `[INTEL]`, `[DEPLOY]`, `[ERROR]`, and `[STATUS]`.
- **Full Method Parity**: Verified and synchronized all 57 attack methods from the core engine into the categorized GUI selection menu.

### Fixed
- **Metric Extraction**: Improved the Regex parser to handle ANSI-stripped telemetry data for precise real-time charting.
- **Dynamic Field Logic**: Re-engineered the visibility controller to correctly map technical requirements (Proxies, RPC, Reflectors) to specific attack vectors (L7, L4 Normal, L4 Amplification).
- **Backend Sync**: Shifted telemetry logging from DEBUG to INFO in `start.py` to ensure consistent data delivery to the GUI pipeline.

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
- **CLI Resilience**: Fixed an unhandled `ValueError` in `start.py` by ensuring thread configs are integers. Wrapped external components like `bombardier` safely to prevent crashes.
- **Proxy Resolution**: Fixed pathing bug in `All Proxy` dropdown mode that incorrectly referenced `proxies/all.txt` instead of `all.txt`.
