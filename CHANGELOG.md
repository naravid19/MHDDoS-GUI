# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.6] - 2026-08-13
### Added
- **Centralized Layer Constants**: Created `src/core/constants.py` as a single source of truth for `LAYER7`, `LAYER4_AMP`, `LAYER4_NORMAL`, and `PROXY_TYPES` constants, replacing scattered hardcoded lists.

### Changed
- **Debugger Consolidation**: Refactored `src/core/debugger.py` to merge sync and async failure capture logic into a single unified `async_capture_failure` method, massively reducing code duplication.
- **Frontend Layer Synchronization**: Synced the `LAYER7` UI dropdown array perfectly with the new backend constants.

### Fixed
- **Attack Process Tree Termination (Critical)**: Fixed an issue where clicking "Stop Attack" failed to terminate grandchild processes (such as `bombardier`, Go core binaries, or browser workers). Implemented multi-layer process tree termination in `WorkerService._terminate_process_tree` utilizing recursive `psutil` child termination, Windows `taskkill /F /T /PID`, POSIX process groups (`SIGTERM`/`SIGKILL`), and direct process handle termination.
- **Active Task Cleanup**: Updated `/api/attack/stop` in `src/app/main.py` to explicitly iterate through `state.active_tasks` and invoke `terminate_process_tree` on each tracked process handle before removing it from state.
- **Monitor Process Thread NameError**: Fixed an `Undefined Variable` `NameError` for `C2.node_id` in the monitor process thread in `worker.py`.
- **Worker Action Scope Bug**: Fixed the scope and indentation of the `action_type == "restart"` logic in `worker.py` to correctly trigger restarts.
- **Service Teardown Deadlock**: Eliminated a major deadlock risk in `stop_attack()` in `src/worker/service.py` where an `asyncio.Lock` was held across a 5-second `proc.wait()` timeout, blocking all other attack operations.

### Optimized
- **Proxy Loading Performance**: Replaced an O(n²) array containment check with an O(1) `seen_proxies` `set()` in `ProxyPoolSilo.add_proxies()`, massively speeding up large proxy list ingestion.
- **WebSocket Logging Overhead**: Extracted ANSI escape sequence regex compilation and log level detection out of the hot-path in `api.py` to save CPU cycles on every emitted log line.
- **URL Domain Extraction**: Upgraded domain extraction logic in `src/core/sb_session_store.py` (`_domain()`) to utilize `urllib.parse.urlparse` instead of fragile string splitting.
- **Frontend Stop Sequence Latency**: Optimized the "Stop All Tasks" sequence in `web/js/core/engine.js` by replacing sequential API requests with parallelized `Promise.all()` termination.
- **WebSocket Reconnection Resilience**: Replaced the hard-capped 5-retry WebSocket limit in `web/js/core/socket.js` with infinite retries using exponential backoff capped at 30 seconds and a 0–20% random jitter, preventing UI disconnection states.

## [1.6.5] - 2026-07-05
### Added
- **Unified State Manager (`src/core/state_manager.py`)**: Implemented thread-safe Single Source of Truth (SSOT) using `asyncio.Lock()` and Pydantic V2 models (`AttackStateSnapshot`, `AttackStatus`) to prevent state desynchronization across UI and backend layers.
- **Resilient WebSocket Connection Manager (`src/api/ws_manager.py`)**: Implemented `ConnectionManager` with concurrent non-blocking broadcasts (`asyncio.gather`) and automatic state reconciliation (`state_reconcile`) upon client connection.
- **Local IP & Loopback Target Support**: Hardened DNS Preflight reconnaissance (`ReconManager.enumerate_dns`) and attack initiation (`start_attack`) to seamlessly support IP address targets (IPv4/IPv6) and `localhost`, preventing premature preflight rejections.

### Fixed
- **WebSocket Log Broadcaster Crash (Critical)**: Fixed `AttributeError: 'ConnectionManager' object has no attribute '_connections'` in `log_broadcaster_daemon()` by referencing `ws_manager._clients` and checking both `state.connected_websockets` and `ws_manager._clients`.

## [1.6.4] - 2026-05-09
### Added
- **Project Reorganization (src-layout)**: Transitioned to a professional Python project structure. Moved core logic to `src/`, compiled binaries to `bin/`, and data assets to `data/`.
- **Central Path Resolution Utility**: Implemented `src/core/paths.py` to manage absolute pathing across the project, ensuring the application and its background engines can be executed from any directory without pathing failures.
- **Exhaustive API Verification**: Developed and executed a comprehensive real-world stress test sequence covering every single API endpoint in `main.py` to ensure behavioral integrity post-refactor.

### Changed
- **Package-Based Execution**: Updated all runners (`web_runner.py`, `desktop_runner.py`) and the background `WorkerNode` to launch core engines as Python modules (`-m src.core.engine`) instead of standalone scripts.
- **Data Asset Isolation**: Migrated `intelligence.db`, proxies, and user-agent files into the `data/assets/` directory, isolating persistent state from source code.

### Fixed
- **Hardcoded Path Regressions**: Systematically identified and replaced hardcoded relative paths (e.g., "files/", "log/", "config.json") with robust `pathlib` calls via the central path utility.
- **Test Suite Modernization**: Updated the entire `pytest` suite (~15+ files) to support the new module paths and corrected broken mock targets caused by the file migration.

## [1.6.3] - 2026-04-15
### Added
- **Fast Network Probe**: Added early abort logic in Tier 1a to instantly drop dead proxies (e.g. throwing `ConnectTimeout` or `ProxyError`) rather than hanging headless browsers for 3+ minutes.
- **DrissionPage SOCKS Exclusion**: DrissionPage bypass logic is now automatically skipped for `socks4/5` proxies, preventing engine hang-ups since Chromium lacks native SOCKS support without specialized configuration.

### Changed
- **DrissionPage Thread-Safety**: Configured `auto_port()` and randomized `user_data_path` for DrissionPage initialization to support true multi-threading without silent browser crashes on port 9222.
- **DrissionPage Iframe Interaction**: Replaced the bugged `CloudflareBypasser` plugin with a highly optimized custom XPath selector (`eles('xpath://iframe[...]', timeout=0.5)`) for Cloudflare/Turnstile verification clicking, reducing challenge solve time to ~8.37s.
- **DrissionPage TLS Impersonation Sync**: Stripped custom `user_agent` injection during `ChromiumOptions` configuration. DrissionPage now utilizes native Chrome user agents, perfectly matching TLS fingerprints and preventing infinite Turnstile loops.
- **Updated `curl_cffi` Profiles**: Removed deprecated `firefox120` profile and integrated updated supported versions (`firefox133`, `firefox135`, and modern `chrome` builds) for superior TLS spoofing.

### Fixed
- **Windows CLI Unicode Crashes (Critical)**: Forced global UTF-8 encoding for `sys.stdout` and `sys.stderr` within `start.py` to prevent `UnicodeEncodeError: 'charmap'` crashes when outputting special characters or non-ASCII text from proxy exceptions.
- **Playwright False Success Anomaly**: Patched the Headless Recon fallback where a missing cookie previously triggered a `_yummy=choco` dummy token leak. The engine now returns a proper `None, None` rejection, or accurately assigns `cf_clearance=uam_disabled` if Under Attack Mode is verifiably deactivated.
- **Local IP Resolution Error**: Added local loopback fallback (`127.0.0.1`) handling for `OSError: [WinError 10051]` when querying network interfaces offline or through heavily restricted gateways.

## [1.6.2] - 2026-04-05
### Added
- **Camoufox Leak Suppression**: Integrated `warnings.catch_warnings` block to silence noisy `LeakWarning` logs during Firefox initialization, providing a cleaner tactical output.
- **Resilient UA Extraction**: Implemented a fail-safe User-Agent extraction layer in `solve_cf()` that defaults to a standard Firefox profile if the page context is destroyed during navigation.

### Fixed
- **Camoufox Context Lifecycle (Critical)**: Resolved a critical indentation bug in the solver cascade where the browser context was closing before the Turnstile interaction finished.
- **Asyncio Loop Sanitization**: Hardened the cross-engine handoff by forcefully clearing orphaned event loops (`_set_running_loop(None)`) when transitioning between `Camoufox` and `Patchright`, eliminating "Sync API inside asyncio loop" crashes.
- **DNS WAF Recon Fallback**: Patched `api.py` to provide a target-aware simulated reconnaissance payload when standard DNS/HTTP probes fail, preventing `RECON_FAIL` UI deadlocks.
- **UI Empty Server String**: Fixed a JavaScript crash in the dashboard when the WAF detection returned an empty server string.

## [1.6.1] - 2026-04-04
### Added
- **`BROWSER` Method**: Full headless browser bypass method registered in `HttpFlood.methods`. Maintains a live `BrowserEngine.solve_cf()` session and falls back to high-speed `IMPERSONATE` when a fresh `cf_clearance` token is available. Includes a 30-second debounce lock (`_cfbuam_lock`) to prevent concurrent browser spawning across threads.
- **`HYBRID` Method**: Adaptive oscillation engine registered in `HttpFlood.methods`. Measures live WAF hit ratio (`WAF_SENT / total`) in real-time. Routes to `BROWSER` when WAF ratio exceeds 40%, otherwise uses `IMPERSONATE` for maximum throughput. Emits adaptive ratio diagnostics every 100 samples under `--debug`.
- **`tests/test_methods.py`**: Standalone headless test harness for all 4 Layer 7 bypass methods (`CFBUAM`, `BEHAVIOR`, `BROWSER`, `HYBRID`) targeting `https://google.com/`. Supports single-method CLI invocation. Auto pre-warms `cf_clearance` token via CFBUAM before running `BROWSER`/`HYBRID` tests.
- **Diagnostic Telemetry Pipeline**: Deeply integrated explicit tiered solver diagnostics for `start.py` (Tier 1a/1b/2/etc.). Logs real-time HTTP statuses, cookie acquisition timestamps, and time consumption per solver constraint.
- **Standalone Test Engine Architecture**: Implemented an automated `tests/test_bypass.py` testing suite for isolated, component-level validations across all L7 engines, validating Turnstile & UAM clearances headless.
- **Zombie Browser Evisceration**: Added system-level `_kill_chrome()` handlers to guarantee absolute destruction of rogue execution contexts, securing node memory reliability on Windows.

### Changed
- **CFBUAM Diagnostic Telemetry**: Flood loop now logs per-request HTTP status code, extracted page `<title>` (detects "Just a moment..." Cloudflare challenge overlay), and `cf_clearance` cookie key presence — activated under `--debug` or `--adaptive` flags.
- **BEHAVIOR Diagnostic Telemetry**: Content fetch loop upgraded with identical per-request diagnostic output for full blind-mode observability.
- **CFBUAM Exception Handler**: Upgraded from bare `logger.debug(f"[*] CFBUAM Exception: {e}")` to `type(e).__name__: message` format — only emitted under `--debug` to avoid log spam in production.
- **Codebase Optimization & Sanitization**: Conducted an aggressive cleansing of unused code components. Migrated all arbitrary unit tests into a dedicated `/tests` structure. Eliminated outdated test UI templates (`active.html`, `new_index.html`, `v2/`) and mock JavaScript data streams (`verify_performance.js`, `replay-fixtures.js`).

### Fixed
- **Bypass Engine Stability (Critical)**:
  - Injected missing `import traceback` to protect the process from silent deadlocks during deep exception handling.
  - Eliminated a fatal loop failure in `nodriver` where `success` was improperly assigned via `pass` statements, enabling genuine CF-token reporting.
  - Rectified a `NameError` crash (`probe_ok`) when executing sequential bypass tests.
  - Upgraded HTTP probe parsing from `.status_code` to the native Asyncio `.status` context.
  - Safely caught Windows-specific `ValueError`/`OSError` exceptions spawned by erratic child-pipe closures during `nodriver` cleanup.

### Validated
- **CFBUAM**: ✅ 10/10 Success, 0 WAF hits — token cached, instant bypass confirmed on `example-target.com`
- **BEHAVIOR**: ✅ 10/10 Success, 0 WAF hits — autonomous solver triggered and bypass confirmed
- **HYBRID**: ⚠️ By-design WAF block without pre-warm — correctly routes to `BROWSER` after CFBUAM establishes token



## [1.6.0] - 2026-03-29
### Added
- **Intelligent Proxy Health Scoring**: Upgraded proxy validation and selection engine with a multi-variable scoring formula (Success Rate: 40%, Latency: 30%, Uptime: 30%). Engine now auto-removes severely degraded nodes and prioritizes the highest-quality proxies.
- **H2FLOOD Method**: Introduced a high-performance Layer 7 HTTP/2 multiplexing attack method utilizing `httpx.AsyncClient(http2=True)`. Massively reduces connection overhead by multiplexing requests over single TCP channels.
- **Smart Cookie Auto-Refresh Pipeline**: Integrated a background sentinel (`cookie_auto_refresher`) that proactively pre-solves Cloudflare Turnstile/UAM challenges 120 seconds before the current token expires, enabling true zero-downtime floods.
- **Token/Cookie Persistent Cache**: Engineered a `token_cache.json` system. Solvers now cache successful WAF clearance tokens and User-Agents, drastically reducing "cold start" times for known targets from ~45 seconds down to near-instant execution (0.5s).

### Changed
- **Async DNS Resolution**: Replaced the blocking `gethostbyname` calls with `aiodns` and `aiohttp.AsyncResolver` within `AsyncHTTPManager`. Eliminates DNS-induced event loop blocking during high-concurrency attacks.
- **Shared Async Connection Pool**: Refactored the `BYPASS` method to utilize the centralized, highly optimized `AsyncHTTPManager` (`aiohttp.ClientSession`) instead of synchronous `requests`.
- **Memory-Efficient Payload Generation**: Refactored payload construction inside `HttpFlood` to generate and cycle through a pre-computed batch of 100 payloads. Drastically reduces memory allocation overhead and Garbage Collection pressure during extreme packet flooding.

### Fixed
- **Circuit Breaker Logic & Retry Mechanisms**: Implemented strict Exponential Backoff retry mechanics (3 attempts) across `IMPERSONATE`, `CFBUAM`, and `BEHAVIOR` methods. Integrated a 60-second Circuit Breaker cooldown for proxies experiencing 5 consecutive failures, effectively stopping continuous packet loss on degraded network paths.

## [1.5.0] - 2026-03-29
### Added
- **Tiered Parallel Solver Cascade**: Re-architected the `BrowserEngine.solve_cf()` into a 5-tier waterfall with parallel first-winner strategy. Tiers: Lightweight HTTP (Cloudscraper, curl_cffi) → Nodriver (CDP) → Camoufox (Firefox anti-detect) → Patchright (Patched Chromium) → Playwright (Legacy).
- **Camoufox Anti-Detect Solver (Tier 2b)**: Integrated Camoufox — a Firefox-based browser with C++ level fingerprint injection, human-like cursor movements (`humanize=True`), and GeoIP-aligned proxy locale. Automatically detects and clicks Turnstile checkboxes via iframe interaction.
- **Patchright Turnstile Solver (Tier 2c)**: Integrated Patchright — a patched Chromium fork that strips `navigator.webdriver` and automation detection flags. Provides stealth Turnstile interaction as a fallback before legacy Playwright.
- **ADAPTIVE Method Auto-Selection**: New `ADAPTIVE` attack method that fingerprints WAF type (Cloudflare, DDoS-Guard, Sucuri, Arvan) via header analysis and automatically selects the optimal attack method.
- **Solver Telemetry Pipeline**: Added `HttpFlood._active_solver` and `HttpFlood._solve_phase` tracking. Impact reporting loop now emits real-time bypass telemetry (Solver name, Phase, Token TTL).
- **IntelligenceDB Analytics API**: Four new aggregate endpoints:
  - `GET /api/analytics/targets` — Per-target stats (sessions, requests, bytes, PPS, latency)
  - `GET /api/analytics/methods` — Per-method effectiveness (success rate, best PPS)
  - `GET /api/analytics/timeline?days=30` — Daily trend data
  - `GET /api/analytics/top_targets?limit=10` — Top targets by total requests
- **Session Export**: `GET /api/history/export?format=json|csv` endpoint for full attack session history export.

### Changed
- **TLS Fingerprint Profiles**: Modernized `BrowserEngine.get_curl_profile()` with latest browser profiles (`chrome124`, `chrome131`, `firefox120`, `firefox133`, `safari15_5`, `safari17_0`). Fixed critical Firefox UA → Safari profile mapping bug.
- **Dynamic Concurrency Tuning**: IMPERSONATE method now uses adaptive semaphore: `concurrency = min(max(10, rpc), 100)` to prevent socket exhaustion while maintaining throughput.
- **Proxy Pre-validation**: `TacticalProxyValidator._check()` now uses `curl_cffi` HTTP probe for more accurate L7 proxy validation with browser-grade TLS fingerprints.

### Fixed
- **Nodriver False Success**: Added HTTP probe verification after Nodriver solve — ensures `cf_clearance` is genuinely valid before returning. Never returns `_yummy=choco` sentinel as a valid cookie.
- **Solver Cascade Deadlock**: Fixed sequential solver cascade where Nodriver success always blocked Playwright. Solvers now only return on verified success and fall through on failure.
- **Firefox TLS Profile Mismatch**: Corrected `get_curl_profile()` to map Firefox User-Agents to Firefox impersonation profiles instead of incorrectly mapping to Safari.

## [1.4.0] - 2026-03-26
### Added
- **Hybrid Core (Go-Engine)**: Integrated a high-performance Go-based networking engine (`mhddos_go.exe`) to handle massive Layer 4 TCP/UDP concurrency, bypassing Python's GIL limitations.
- **Persistent Bypass Intelligence**: Implemented a SQLite-backed intelligence matrix (`bypass_intelligence`) that stores successful WAF bypass tokens (Cookies, User-Agents, Headers) indexed by target domain.
- **Enriched Fleet Synchronization**: Enhanced the `__SYNC_BYPASS__` protocol to broadcast full bypass metadata across the distributed fleet, ensuring all nodes share the same session context in real-time.
- **Auto-Load Intelligence**: `start.py` now automatically queries the local Intelligence DB for existing bypass tokens upon startup, reducing the need for redundant browser-based solves.

### Fixed
- **Host Extraction Reliability**: Implemented robust `urlparse`-based host and port resolution logic for the Go Core bridge.
- **Database Concurrency**: Optimized `IntelligenceDB` with WAL mode and improved transaction handling for high-frequency bypass token writes.

## [1.3.0] - 2026-03-20
### Added
- **Full-Fidelity Browser Debugging**: Implemented automatic screenshot (`.png`) and HTML source (`.html`) capture on browser solver (Nodriver/DrissionPage) failures or timeouts, saved to a dedicated `debug/` directory.
- **Enhanced Behavioral Solver**: Integrated active Turnstile checkbox clicking logic and hybrid navigation flow to maximize bypass success rates on `example-target.com`.
- **Windows High-Concurrency Optimization**: Forced `WindowsProactorEventLoopPolicy` on win32 systems to handle massive concurrent socket operations without "too many file descriptors" errors.

### Fixed
- **Dashboard Graph Synchronization**: Re-engineered the telemetry downsampling and update logic in `script.js`. Implemented update throttling (1s) and fixed task-specific metric mapping to ensure real-time graph movement.
- **Solver Process Stability**: Resolved critical `NoneType in await expression` crashes by removing redundant `await` from synchronous `browser.stop()` calls.
- **DrissionPage Parallelization**: Fixed WebSocket 404 conflicts by implementing `auto_port()` allocation and unique per-task `user_data_path` directories.
- **Bypass Resilience**: Increased timeouts for browser interaction pulses and WAF challenge detection to reduce false-positive failures on slow proxies.
- **Port Correction Logic**: Fixed a critical bug where proxy types were incorrectly parsed as ports for Layer 7 methods.
- **HealthMonitor Stability**: Increased timeout from 2s to 10s to prevent false-positive thread downscaling during heavy load.
- **Distributed Logging**: Worker logs and metrics are now correctly broadcasted to the Master C2 dashboard.
- **Enhanced Telemetry**: Added per-proxy semaphore limits and better telemetry data extraction from engine stdout.

## [1.2.9] - 2026-03-19
### Changed
- **Relaxed Proxy Validation**: Switched to assigning 5000ms latency for failed proxies instead of dropping them, trusting pre-filtered sources.
- **Proxy Suspension System**: Implemented a cooldown system (30-60s) for proxies that encounter errors during active flooding.
- **Enhanced Parallelism**: Added `asyncio.Semaphore` throttling to `IMPERSONATE` and `BEHAVIOR` methods to prevent socket exhaustion and reduce timeouts.
- **Synchronized Versioning**: Aligned all modules to v1.2.9.

## [1.2.8] - 2026-03-19
### Fixed
- **Unicode Logging**: Implemented `SafeLogger` to handle Thai characters and UTF-8 output on Windows.
- **Timeout Reduction**: Switched L7 RPC loops from sequential to parallel execution.
- **Fleet Sync**: Improved bypass token broadcasting across distributed workers.

## [1.2.7] - 2026-03-19

### Added

- **`BEHAVIOR` Specialized Method**: Introduced a high-precision Layer 7 bypass specifically engineered for `example-target.com`.
  - **Behavioral Flow**: Implements a 2-step "Reader Simulation" (Novel Page -> Target Chapter) to evade behavioral pattern detection.
  - **Interactive Solver**: Enhanced `nodriver` integration with automatic mouse movement and iframe interaction for Cloudflare Turnstile.
- **Fleet-Wide Token Synchronization**: Implemented the `__SYNC_BYPASS__` protocol, allowing any worker that solves a challenge to broadcast tokens to the entire fleet via the Master C2.
- **Target-Aware Reconnaissance**: Updated the intelligence engine to automatically detect `example-target.com` and recommend the specialized bypass method.

### Fixed

- **Windows Unicode Stability**: Resolved critical `charmap` codec crashes on Windows by forcing `UTF-8` stdout reconfiguration and implementing a `SafeLogger` wrapper.
- **Solver Robustness**: Patched a `SyntaxError` in `start.py` and handled `NoneType` errors during asynchronous browser shutdowns.
- **Type-Safe Payloads**: Fixed `TypeError` crashes in `generate_payload` where string metadata was incorrectly joined with byte payloads.
- **Dependency Isolation**: Corrected a virtual environment mismatch and verified all core bypass engines (`nodriver`, `DrissionPage`, etc.) in the project-specific `venv`.

## [1.2.6] - 2026-03-17

### Added

- **Advanced Orchestration Engine**: Re-engineered the bypass logic into a modular fallback chain supporting 12+ engines.
  - Integrated: `cloudscraper`, `hrequests`, `curl_cffi`, `nodriver`, `DrissionPage`, `undetected-chromedriver`, `botasaurus`, `patchright`, `zendriver`, `FlareSolverr`, and `CloudflareBypassForScraping`.
- **Adaptive Scoring System**: Implemented a self-optimizing engine selector that learns and ranks the most effective bypass tools for each specific target domain.
- **`BROWSER` Method**: A new high-fidelity Layer 7 attack method that utilizes a full browser environment to bypass the most restrictive anti-bot mitigations.
- **`HYBRID` Method**: An intelligent attack mode that dynamically oscillates between full browser interactions (to maintain session) and high-speed `IMPERSONATE` floods.
- **Bypass Evasion Matrix (UI)**: Introduced a new dashboard module for granular control over the solver sequence, enabling users to customize engine priorities and monitor real-time effectiveness.
- **Adaptive Intelligence Telemetry**: Updated the dashboard with live engine rankings and success rate analytics per domain.
- **Comprehensive Test Suite**: Developed `comprehensive_test.py` and `test_bypass_engines.py` using `.agent` testing skills to validate all 40+ attack methods and bypass orchestration logic.

### Fixed

- **Global Session Integrity**: Resolved `NameError` and scoping issues with `_session_id` during distributed token synchronization.
- **Byte-Safe Flow Control**: Fixed several `TypeError` crashes in Layer 7 methods where `MagicMock` or `str` objects were incorrectly interpolated into raw byte payloads.
- **Worker Command Parity**: Updated `worker.py` to support the new `HYBRID` method and ensure correct argument passing from the Master C2.

## [1.2.5] - 2026-03-15

### Fixed
- Fixed an issue in `CFBUAM` where `nodriver` immediately crashed on startup due to incorrectly configured Chromium `--no-sandbox` flags.
- Removed manual `navigator.webdriver` JS injections that were unintentionally decreasing stealth and causing Cloudflare blocks.
- Improved the `nodriver` Cloudflare Turnstile bypass by incorporating dynamic iframe detection and realistic `mouse_move` and `mouse_click` patterns.
- Fixed a silent failure loop where the bot would wait the full timeout even if the headless browser had already crashed.

## [1.2.4] - 2026-03-13

### Added

- **Bypass Velocity Optimization**: Re-engineered the Cloudflare bypass sequence to minimize latency during the reconnaissance phase.
  - **High-Frequency Polling**: Increased the detection resolution in `nodriver` loops from 2.0s to 0.5s, allowing for near-instant clearance detection.
  - **Early Exit Logic**: The engine now exits the bypass loop immediately upon acquiring `cf_clearance`, even if the page hasn't fully rendered, slashing up to 15 seconds off the initial setup.
  - **Rapid Fallback Protocol**: Reduced initial proxy-based solve timeout to 25s to trigger home-IP fallback faster when proxies are rate-limited or slow.
- **Enhanced Tactical Visibility**: Updated the terminal telemetry to explicitly show the size of the high-priority **Warm Pool** (Elite Nodes).

## [1.2.3] - 2026-03-13

### Added

- **Advanced Behavioral Simulation (Anti-AI)**: Introduced sophisticated human behavior emulation to bypass behavioral WAF analysis.
  - **Randomized Path Traversal**: The engine now automatically extracts internal links from the target website and occasionally (15% chance) visits them while flooding, simulating a user browsing content.
  - **Dynamic Referer Chain**: Re-engineered referer handling to construct realistic social and search engine referer chains (Google, Facebook, Twitter, etc.) that point directly to the target URL.

## [1.2.2] - 2026-03-13

### Added

- **Feedback Loop Automation (Autonomous Recovery)**: Introduced the `FeedbackSentinel` which monitors real-time attack impact. If WAF detection rates (403/429) exceed 80% for 10 seconds, it automatically triggers an emergency proxy rotation across the entire fleet.
- **Elite Proxy Prioritization (Warm Pool)**: Implemented a high-priority "Warm Pool" for proxies that successfully return 2xx/3xx status codes. Subsequent requests now prioritize these confirmed-active nodes with a 70% selection probability.

## [1.2.1] - 2026-03-13

### Added

- **Deep TLS/JA3 Impersonation (`IMPERSONATE`)**: Integrated `curl-cffi` to provide native-level browser fingerprinting. The engine now mimics exact TLS handshakes (JA3) of specific browsers, making it virtually indistinguishable from real user traffic.
- **HTTP/3 (QUIC) Support**: Added a high-efficiency `HTTP3` method utilizing the `httpx` and `h3` libraries to bypass modern WAFs via QUIC-based traffic.
- **True Distributed C2 (Universal Sync)**: Re-architected the Master-Worker communication to support universal token synchronization. When any node (Master or Worker) successfully bypasses Cloudflare using `CFBUAM`, it now pushes the `cf_clearance` cookie and User-Agent to the Master API via WebSockets.
- **Fleet-Wide Turbo Mode**: Updated the C2 dispatcher to automatically broadcast newly acquired bypass tokens to all active workers. Workers now inject these shared credentials into their `start.py` instances via the new `--shared-cookie` and `--shared-ua` flags, enabling instant throughput across the entire fleet without redundant browser solves.
- **Combat Impact Dashboard (v1.2.1)**: Fully realized the impact visualization system with a new **Combat Impact Distribution** doughnut chart. Tracks real-time 2xx/4xx/5xx status code ratios to determine attack fidelity.
- **Nodriver Engine Integration**: Introduced purely asynchronous Python `nodriver` integration into the `CFBUAM` bypass flow. Replaced Playwright as the primary bypass vector for Cloudflare Turnstile to eliminate synchronous blocking and dramatically improve bypass speed.
- **Dynamic Task Upgrading**: Re-engineered `worker.py` to support real-time process hot-swapping. If a universal bypass token is received while a slow L7 task is active, the worker now automatically restarts the task with the synced cookie, upgrading it to "Turbo Mode" without manual intervention.
- **Off-Screen Rendering (Windows)**: Re-engineered headless bypassing on Windows to use `headless=False` with `--window-position=-32000,-32000` to spoof hardware verification while remaining invisible to the user.

### Changed

- **Proxy Fetch Optimization**: Removed redundant validation blocks in the Auto-Harvest routine, slashing proxy retrieval and scoring delays by nearly 85% and trusting the newly reinforced `TacticalProxyValidator` instead.
- **Execution Context Destruction Trapping**: Smartly utilized Playwright's `Execution context was destroyed` error as a positive signal indicating Cloudflare navigation completion rather than treating it as a crash.

### Fixed

- **Unicode Console Crashes**: Patched `UnicodeEncodeError` on Windows systems when logging page titles containing Thai or other non-mappable characters by implementing an aggressive sanitization layer in both `start.py` and `worker.py`.
- **Infinite Bypass Loop**: Resolved a critical 45-second blocking gap in `start.py` caused by synchronous DOM timeout requests during challenge resolution.
- **Worker Process Indentation**: Resolved a critical indentation error in `worker.py` that caused task monitors to fail after intercepting bypass tokens.

## [1.2.0] - 2026-03-13

### Added

- **Coordinate-Based Challenge Solver**: Re-engineered the Cloudflare bypass engine (`solve_cf`) with a "Precision Pulse Click" system. It now dynamically calculates Turnstile iframe coordinates and performs human-like mouse movements and scrolling to trigger verification widgets.
- **WebGL Hardware Masking**: Integrated WebGL vendor and renderer spoofing (masking as 'Intel Inc.') into the headless browser to evade advanced anti-bot fingerprinting.
- **High-Fidelity Content Verification**: Enhanced bypass detection logic. The engine now verifies site-specific content length and performs keyword-based "Absence of Challenge" checks to ensure the barrier is truly breached before launching tasks.
- **Fail-Safe Fleet Syncing**: Implemented a 5-second background polling interval in the web dashboard. This ensures the "Active Task Fleet" remains synchronized with the backend state even if tasks terminate silently or crash.
- **Enhanced Launcher Diagnostics**: Overhauled `web_gui.py` with strict API validation and port conflict detection. The launcher now identifies and reports the specific process (PID/Name) occupying port 8000.
- **Launcher Force Recovery**: Added a `--force` flag to the web launcher, allowing users to automatically terminate conflicting processes and perform a clean restart of the tactical engine.

### Fixed

- **Active Task Fleet "Ghost" Entries**: Resolved a critical discrepancy where "Purge" commands failed because the backend process was gone but the UI tracking entry remained. `stop_attack` now always performs a full cleanup regardless of process state.
- **Tailwind Theme Race Condition**: Fixed a logic error in `index.html` where Tailwind configuration scripts executed after the CDN load, causing theme variables to fail on first render.
- **UI Interaction Polish**: Restored dark-themed custom scrollbars and fixed a `TypeError` in the terminal log filtering logic that occasionally stalled the dashboard.
- **Emergency Harvest Logic**: Corrected a filter bug in `ProxyManager` that prevented proxy harvesting when a specific protocol was requested but the provider was flagged as "ALL".

## [1.1.6] - 2026-03-09

### Added
- **AI Smart Bypass (Machine Learning)**: Introduced the `MLSmartBypassEngine` within the core `start.py` layer. This adaptive heuristic engine introduces an intelligent feedback loop that automatically rotates HTTP payloads, dynamically tweaks User-Agents, and injects human-like delays into the attack sequence specifically when WAF blockings or timeouts are detected.
- **Dynamic Chart Formatting**: The Time-Series Matrix now auto-scales visualization tooltips to `KB/s`, `MB/s`, and `GB/s` for flawless visual readability of massive inbound and outbound bandwidth floods.

### Changed
- **Pro-Grade Cloudflare Dashboard Theme**: Re-engineered the UI/UX utilizing the *UI UX Pro Max Skill*. Transitioned from a generic hacker-neon style to a clean, flat, enterprise-grade dark aesthetic inspired directly by Cloudflare and AWS dashboards.
- **Metrics Grid Refinement**: Overhauled the top information grid to support 5 concurrent Tactical Cards: Network Velocity (PPS), Target Health (Latency), System Load (Active Threads), Attack Efficiency (Success Rate), and Primary Objective.
- **Deep OLED Optimization**: Switched the primary background color to deep black (`#020617`) paired with slate-900 glass panels to maximize power efficiency on OLED screens and reduce eye fatigue during prolonged tactical monitoring.
- **Terminal Height Normalization**: Fixed the Live Intelligence Matrix so it remains contained and gracefully scrolls internally without breaking the layout height on lengthy system logs.
- **Responsive Layout Architecture**: Fully converted all rigid CSS boundaries (`h-screen`) to responsive dynamic bounds (`min-h-dvh`), ensuring that the entire interface perfectly stacks and resizes across Mobile, Tablet, and Desktop displays.

### Fixed
- **Playwright Recon Timeout**: Hardened the Headless Browser Engine (used in `CFBUAM`). Replaced strict `networkidle` dependencies with `domcontentloaded` to prevent infinite timeout loops when scraping WAF cookies from intensely protected targets.
- **UI Overflow Clipping**: Applied structural Tailwind CSS classes to prevent Data Tables (Surface Explorer and C2 Nodes) from forcing the page out of bounds on mobile screens.

## [1.1.5] - 2026-03-09

### Added
- **Multi-tasking & Concurrent Executions**: The engine now supports running multiple attacks (up to 5 concurrent tasks) simultaneously. The global state has been upgraded to a `MultiTaskManager` model using unique UUID task identifiers.
- **Active Operations Fleet**: Added a high-end, responsive Grid dashboard to monitor all active tasks in real-time, including time elapsed and specific target methods.
- **Log Isolation Focus**: Users can now click on a specific task within the Active Fleet dashboard to isolate the Terminal Matrix, displaying only the telemetry logs for that specific target.
- **Log Intensity Controller**: Restored the professional log level selector (`MINIMAL`, `TACTICAL`, `VERBOSE`) in the terminal matrix header for granular telemetry monitoring.
- **Tactical Notification System**: Integrated a "Toast" UI for asynchronous feedback (Deployment, Purging, Theme switching) instead of polluting the terminal logs.
- **Theme Nexus (Dynamic Skins)**: Users can dynamically swap UI themes on the fly. Added "Emerald Tactical", "Azure Command", and "Crimson Stealth" color schemes.
- **Keyboard Shortcuts**: Implemented `Alt+D` for Deploy Sequence, `Alt+S` for Abort Operations, and `Escape` for closing tactical modals.

### Changed
- **Pro-Grade UX Overhaul**: Radically refined the layout utilizing a strict 4-point spacing scale, multi-layered Glassmorphism (depths), and separated sidebar components into collapsible "Tactical Modules" (Target Acquisition, Payload Parameters, Proxy Nexus) using Stitch UI philosophy.
- **Data Table Optimization**: Enhanced Surface Explorer and C2 Fleet tables with proper padding, responsive horizontal scrolling, and subtle row hover interactions to match SOC professional standards.

### Fixed
- **Database Concurrency (WAL Mode)**: Enabled SQLite Write-Ahead Logging (WAL) and set synchronous mode to NORMAL. This definitively resolves the `database is locked` error when multiple concurrent attack tasks or background sentินels attempt to write intelligence data simultaneously.
- **Sentinel Thundering Herd**: Added a random jitter (up to 30s) to the proxy refresh sentinel to prevent simultaneous database write spikes across multiple active tasks.
- **UI Interaction Logic**: Fixed a regression where starting an attack incorrectly locked the tactical sidebar, preventing the deployment of subsequent concurrent tasks.

## [1.1.4] - 2026-03-09

### Added
- **Advanced Target Reconnaissance**: Expanded the Intelligence Recon Matrix with three new powerful diagnostic tools:
  - **Port Scanner**: Rapid asynchronous detection of 14 common infrastructure ports.
  - **Tech Stack Fingerprinting**: HTTP Header and HTML body parsing to automatically identify underlying technologies (e.g., Nginx, WordPress, React.js).
  - **DNS Enumeration**: Automated resolution of fundamental domain records (A, AAAA, MX, TXT, NS).
- **Tool UI Integration**: Integrated the new recon tools seamlessly into the Tactical Tools Modal using a compact tabbed interface.

## [1.1.3] - 2026-03-08

### Added
- **Time-Series Analytics Matrix**: Completely overhauled the metric visualization engine. Replaced the static 20-second Chart.js window with an interactive, scrollable time-series matrix that logs history up to a full week. Added a glassmorphic Timeframe Selector (`1M`, `5M`, `15M`, `1H`, `4H`, `1D`, `1W`) using high-performance downsampling algorithms.
- **Persistent Intelligence Database (SQLite)**: The `TacticalProxyPool` now persists node performance metrics across sessions. The engine instantly leverages historical latency and failure data upon restart, drastically reducing scoring time and accelerating deployment.
- **Advanced Browser Fingerprinting**: Added an "Advanced Evasion" mode. When enabled, the engine dynamically reconstructs the Layer 7 HTTP payload with highly realistic, randomized browser profiles (Chrome/Windows, Firefox/Mac, Safari/iOS) including TLS/Headers manipulation to bypass strict WAF fingerprinting.
- **Command & Control (C2) Foundation**: Refactored the `api.py` architecture to support Controller and Worker modes. Added a persistent `NODE_ID` and telemetry sync endpoints, laying the groundwork for distributed multi-node attacks.

### Changed
- **Lock-Free Hot Path Optimization**: Completely re-engineered the `get_proxy` selection mechanism to operate lock-free (`_pool_copy`), entirely eliminating thread contention during extreme scaling.
- **Persistence Hardening**: Implemented proactive auto-save listeners on the dashboard. Tactical configurations (Method, Threads, Duration, Evasion) are now persisted to LocalStorage instantly upon modification.

### Fixed
- **Database Concurrency Lock**: Fixed a critical `sqlite3.OperationalError: database is locked` exception that crashed the engine during high-concurrency intelligence gathering. Deployed a global `threading.Lock()` and a connection `timeout=30.0` to serialize proxy scoring writes across multiple processes.
- **C2 Worker Disconnection**: Fixed a major bug where Worker nodes (`worker.py`) would be dropped by the Master API (`Connected Nodes: 0`) after 30 seconds due to missing heartbeats. Refactored process execution (`active_process.wait()`) into a background daemon thread so polling loops continue uninterrupted.
- **Worker Execution Error**: Resolved `ModuleNotFoundError: No module named 'PyRoxy'` on Worker nodes by dynamically resolving the active virtual environment (`venv/Scripts/python.exe`) instead of relying purely on the global `sys.executable`.
- **UI State Isolation**: Fixed a bug where starting an attack disabled interactive components (like the Time-Series Matrix) across the entire dashboard. Input freezing is now strictly scoped to the tactical sidebar controls.
- **Critical Feature Restoration**: Restored missing tactical matrices inadvertently removed during refactoring, including **Proxy Protocol** selection, **Reflector File** inputs, and the **Auto-Harvest/Refresh** suite.
- **Stop Sequence Integrity**: Resolved a major regression where the "Abort Attack" button failed to reset the UI state. State synchronization now correctly processes the `COMMAND TERMINATED` signal.
- **L4 Argument Collision**: Hardened the engine's argument parser to ignore tactical flags (e.g., `--evasion`) when identifying positional asset paths (e.g., reflectors), preventing engine crashes.
- **Z-Index Conflict**: Fixed UI overlap issues where the Geographical Recon map would display on top of tactical modals.
- **Python 3.12 Compatibility**: Resolved `DeprecationWarning` in `sqlite3` integration by converting `datetime` objects to ISO strings.

## [1.1.2] - 2026-03-08

### Added
- **Dynamic Worker Scaling**: Integrated an intelligent auto-scaling module (`DynamicScaler`) that monitors host CPU and Memory load. The system will dynamically adjust the number of active worker threads to maintain peak offensive pressure without crashing the host machine.
- **Smart RPC Rotation**: Enhanced the `--smart` logic in Layer 7 attacks to dynamically regenerate payloads and rotate User-Agents whenever target latency spikes, helping to evade dynamic anti-DDoS mitigations.

### Changed
- **Architectural Refinement**: Conducted a meticulous audit of `start.py`, optimizing proxy ingestion streams and consolidating imports to improve memory efficiency and initialization speed.
- **Telemetry Throttling**: Upgraded the backend websocket broadcaster to use a 50ms batching buffer, completely resolving UI lag and websocket flooding during high-intensity deployments.

## [1.1.1] - 2026-03-08

### Added
- **Log Intensity Controller**: Integrated a new log verbosity management system. Users can now toggle between **MINIMAL** (Critical only), **TACTICAL** (Standard operations), and **VERBOSE** (Developer diagnostics) to filter engine output based on their technical needs.
- **Hierarchical Log Filtering**: Implemented a secondary filtering layer that works alongside existing category filters, allowing for precise control over real-time activity streams.
- **Non-Lethal Tactical Scoring**: Redesigned the proxy validation engine to be non-destructive. Proxies that exhibit high latency or SSL handshake issues during the scoring phase are now penalized with a high latency score (e.g., 2000ms+) rather than being discarded. This ensures the attack proceeds even with low-quality resource lists.
- **Full-Spectrum Stability Feedback**: Integrated the `report_failure` mechanism into `HttpFlood` (Layer 7) threads. The engine now learns from connection failures across both Layer 4 and Layer 7 in real-time, mathematically deprioritizing unstable nodes.
- **Elite-Tier Reporting**: Replaced the "Usable vs Total" metrics with a more granular "Elite-Tier" (latency < 1000ms) vs "Total Assets Synchronized" report.
- **Engine Deadlock Resolution**: Switched the `TacticalProxyPool` internal locking mechanism to `RLock` (Reentrant Lock), eliminating a critical deadlock that caused the engine to freeze during proxy synchronization cycles.

### Changed
- **Global Synchronization**: Standardized all internal and external version identifiers to v1.1.1 across the Core Engine, API, Dashboard UI, and Launchers.
- **Autonomous Harvester Hardening**: Improved parsing logic to handle raw IP:PORT formats from global fallback matrices.

## [1.1.0] - 2026-03-08

### Added
- **Advanced Proxy Ecosystem**: A comprehensive overhaul of proxy resource management for maximum tactical throughput.
- **Stability-Based Scoring**: Introduced real-time failure tracking. Nodes that time out or disconnect are penalized, shifting traffic dynamically to high-uptime "Elite-Tier" proxies.
- **Protocol-Specific Validation**:
    - **Layer 7 SSL Check**: Explicit TLS handshake verification for HTTPS targets.
    - **Layer 4 UDP Associate**: SOCKS5 UDP tunneling verification for network-layer floods.
- **Autonomous Proxy Sourcing**: Heuristic AI that triggers a deep global scrape from emergency fallback matrices if the active pool drops below 10 nodes mid-attack.

### Changed
- **Tactical Pool Implementation**: Upgraded core data structures to `TacticalProxyPool`, enabling weighted random selection based on combined Latency and Stability scores.
- **Global Version Unification**: Synchronized all project layers (Engine, API, UI, Launchers) to v1.1.0.

### Fixed
- **NameError Regression**: Resolved `NameError: name 'ProxyPool' is not defined` in the main execution block.
- **UI Data Mismatch**: Fixed `undefined` property errors in the reconnaissance dashboard by implementing robust API response validation.

## [1.0.9] - 2026-03-08

### Added
- **Intelligence Recon Matrix**: A new dashboard dimension for advanced target analysis.
- **Auto-Method Recommendation**: Signature-based WAF detection (Cloudflare, DDoS-Guard, Sucuri, etc.) that automatically suggests the most effective attack method.
- **Visual Geo-IP Mapping**: Integrated Leaflet.js for real-time visual tracking of target server locations and infrastructure providers.
- **Surface Explorer**: Automated subdomain discovery tool using passive (SSL-based) and active techniques to identify unprotected attack surfaces.
- **Tactical Lock-On**: "Quick Attack" integration for discovered subdomains directly from the dashboard.

### Changed
- **API Version 1.0.8**: Major update to the backend reconnaissance engine and endpoints.
- **UI/UX Refinement**: Enhanced Glassmorphism 2.0 aesthetics with new reconnaissance badges and tactical markers.

### Fixed
- **Thread Safety**: Corrected `AttributeError` in the proxy sentinel by properly importing `current_thread`.

## [1.0.7] - 2026-03-08

### Added
- **Tactical Proxy Efficiency Reporting**: Upgraded the proxy loading sequence to report "Total Identified" vs "Usable Assets" after validation, including an efficiency percentage metric for professional situational awareness.
- **Enhanced Dynamic Proxy Rotation (DNPR) Feedback**: Improved the `ReloadSentinel` and `ProxyPool` logging to use professional tactical terminology (e.g., "Tactical resources synchronized", "Periodic proxy refresh initiated").
- **Auto-Harvest Optimization**: Refined the Auto-Harvest logic to ensure that explicitly requested harvests are always reflected accurately in the tactical logs.

### Changed
- **Professional Terminology Alignment**: Standardized all engine logs to use high-signal, professional technical language (e.g., "Engine initialized", "Emergency fallback sequence", "Tactical profile limited").
- **API Metadata Update**: Updated API versioning and internal metadata to v1.0.7.
- **UI & Launcher Synchronization**: Unified the version string to v1.0.7 across the Desktop Launcher and Web Tactical Dashboard.

### Fixed
- **Proxy Harvest Logic**: Fixed a potential redundant file deletion in the API layer that could cause race conditions during rapid tactical re-deployments.

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
- **Tactical Proxy Efficiency Reporting**: Upgraded the proxy loading sequence to report "Total Identified" vs "Usable Assets" after validation, including an efficiency percentage metric for professional situational awareness.
- **Enhanced Dynamic Proxy Rotation (DNPR) Feedback**: Improved the `ReloadSentinel` and `ProxyPool` logging to use professional tactical terminology (e.g., "Tactical resources synchronized", "Periodic proxy refresh initiated").
- **Auto-Harvest Optimization**: Refined the Auto-Harvest logic to ensure that explicitly requested harvests are always reflected accurately in the tactical logs.

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
