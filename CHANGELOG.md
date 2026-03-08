# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.6] - 2026-03-07

### Added
- **Tactical Recon Tools**: Integrated a suite of diagnostic tools (ICMP Ping, HTTP Status Check, and Geo-IP Recon) with a dedicated UI modal and automated host filling for rapid target analysis.
- **Config Modal Validation & UI**: Added robust input validation to the Proxy Harvest Configuration modal to prevent malformed URLs or invalid local file paths. Enhanced the UI with inline error notifications and hover tooltips detailing supported formats.
- **Local File Auto-Harvest Support**: Upgraded the `ProxyManager` to natively support reading proxy sources from absolute local file paths (e.g., `C:\path\to\proxies.txt`), bypassing network overhead for local assets.
- **Configurable Auto-Harvest Sources**: Added an "Edit Sources" modal to the UI, allowing users to define custom URLs and timeout rules for Auto-Harvest operations, with persistent storage in `config.json`.
- **MIXED Proxy Parsing**: Upgraded `ProxyManager` to support mixed-protocol proxy lists (e.g., `all.txt` containing `socks5://`, `http://`). Auto-Harvest can now parse and instantiate mixed proxy lists gracefully.
- **Hacker-Professional Hybrid UI (v1.0.6)**: Redesigned the dashboard with a technical aesthetic using **Fira Sans** and **Fira Code** typography, refined spacing, and improved accessibility.
- **UI State Machine**: Implemented a robust frontend state machine (`idle | starting | running | stopping`) to ensure precise control over attack sequences and prevent UI race conditions.
- **Health Monitoring**: Added a new `/api/health` endpoint for real-time backend readiness checks.
- **Enhanced Log Filtering**: Introduced granular log categories (`ALL`, `ATTACK`, `SYSTEM`, `ERROR`) with an optimized filtering engine.

### Changed
- **Comprehensive Code Refactoring**: Executed a massive architectural cleanup across the entire codebase (`api.py`, `start.py`, `web_gui.py`, `desktop_gui.py`) adopting strict Python 3.11+ Type Hinting, Pydantic V2 schemas, async `subprocess` management, and PEP-8 compliance via `black` and `ruff`.
- **API Hardening**: Refactored `api.py` to use a dedicated command-building engine with strict parameter validation and type enforcement.
- **Resource Protocol Alignment**: Removed the incompatible `HTTPS` proxy type from the UI and API to align with the core engine's capabilities.
- **Launcher Resilience**: Updated `web_gui.py` and `desktop_gui.py` to use absolute path resolution and correct working directories, enabling reliable execution from any location.

### Fixed
- **Metric Parsing & Scaling**: Fixed a critical bug in the JavaScript telemetry parser where non-numeric BPS strings (e.g., "-- B", "7.70 kB") caused `NaN` values and broke Chart.js rendering. Normalization now correctly scales units (kB, MB, GB) to Bytes.
- **UI Methods Parity**: Updated the frontend dropdown menu to include the complete set of 47 attack methods, perfectly aligning with the core backend engine (`start.py`) and official documentation.
- **Original Target Logging**: Decoupled Layer 7 and Layer 4 target resolution logic so that the live activity matrix now accurately displays the original target domain/URL entered by the user (rather than the resolved IP), while seamlessly using the resolved IP under the hood for engine operations.
- **BOT Method Formatting**: Resolved a critical string formatting bug in `start.py` that caused the `BOT` method to crash during execution.
- **L4 Hostname Resolution**: Fixed a variable reference error in the Layer 4 exception handler that led to crashes on unresolved hostnames.
- **Websocket Stability**: Improved connection management to proactively purge dead websocket clients, preventing memory leaks and stale broadcasts.

## [1.0.5] - 2026-03-07

### Added
- **Premium Enterprise Overhaul**: Re-engineered the UI with **Glassmorphism 2.0** aesthetics, featuring deep 24px backdrop blurs, precision 0.5px borders, and a refined Slate-950 color palette.
- **System Health Matrix**: Integrated a new header-level matrix displaying real-time system health (Engine Uplink, Proxy Sync, and Encryption Protocol).
- **Smoothed Visualization Engine**: Upgraded Chart.js to use cubic interpolation (0.45 tension) and area-fill gradients for fluid, professional-grade metric visualization.
- **Enterprise-Grade Typography**: Unified the interface with the Inter (UI) and JetBrains Mono (Data) font pairing for maximum readability.
- **Advanced Micro-Interactions**: Implemented fluid CSS transitions and micro-animations for button states, card hover effects, and collapsible resource sections.

### Changed
- **Terminology Standardization**: Fully unified all UI and log messages with industry-standard professional terminology (e.g., "Network Resources", "Activity Pipeline", "Launch Attack").
- **Metric Hub Optimization**: Enhanced information density by refining grid layouts and metric card typography.

### Fixed
- **API/Engine Synchronization**: Corrected terminology drift in log broadcasting between `api.py` and the frontend.
- **Log Highlighting Logic**: Refined the regex engine to properly categorize enterprise-standard status messages in the activity log.

## [1.0.4] - 2026-03-07

### Added
- **Dynamic Proxy Rotation (DNPR)**: Implemented a thread-safe `ProxyPool` and background `ReloadSentinel` in the core engine. Supports hot-swapping proxy lists from files or URLs every 15, 30, or 60 minutes without stopping the attack.
- **Advanced Resource UI**: Added a collapsible "Advanced Resource Settings" section in the sidebar for granular control over proxy auto-refresh logic.
- **Professional Terminology Overhaul**: Replaced abstract "cyber" labels with industry-standard terminology (e.g., "Target Configuration", "Network Resources", "System Activity Log") for improved usability.

### Changed
- **UI Density Optimization**: Refined the dashboard layout for higher information density and reduced cognitive load.
- **Improved Tooling Integration**: Enhanced the `handleProxyList` logic to natively support a wider range of external proxy list formats using robust regex patterns.

### Fixed
- **Proxy Staleness**: Resolved the issue where long-duration attacks (3+ hours) would lose efficiency due to dead proxies.
- **Input Persistence**: Fixed auto-saving logic for new advanced settings (Auto-Refresh toggle and Interval).

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
