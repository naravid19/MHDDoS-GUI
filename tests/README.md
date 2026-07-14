# MHDDoS-GUI Test Suite Guidelines

This directory houses the comprehensive test suite for the MHDDoS-GUI desktop and web application. It has been reorganized to support modular, isolated, type-safe, and highly concurrent execution without side-effects or network dependencies.

---

## 📂 Test Organization

Tests are grouped into directories based on functional responsibility:

| Directory | Primary Purpose | Key Test Files |
|:---|:---|:---|
| `core/` | Unit testing of core library classes, state managers, and version detections | `test_chrome_version.py`, `test_token_manager.py`, `test_proxy_validator.py` |
| `bypass/` | Cloudflare and Turnstile bypass solver engine waterfall logic unit/integration tests | `test_all_engines.py`, `test_turnstile_solver.py`, `test_flaresolverr_tier0.py` |
| `network/` | Proxy rotation, proxy scoring, proxy pool validation, and circuit-breaker logic | `test_proxy_guard.py`, `test_cfbuam_circuit_breaker.py`, `test_proxy_concurrency.py` |
| `api_worker/` | FastAPI backend endpoints, WebSockets, background worker service execution, telemetry aggregation, and state synchronization | `test_api_integration.py`, `test_worker_service.py`, `test_ui_state_machine.py` |
| `attack/` | Command line string generation, OS-aware scaling logic, paths, and DNS preflights | `test_command_builder.py`, `test_new_methods.py`, `test_os_aware_scaler.py` |
| `performance/` | Performance logic, queue saturation, and CPU/memory accounting | `test_performance_logic.py` |

---

## ⚡ Mocking & Isolation Guidelines (Critical for AI & CI)

When writing or modifying tests, you **must** adhere to these architectural rules to prevent global interpreter contamination, test ordering failures, or network rate-limiting.

### 1. Token Cache Isolation (`tests/conftest.py`)
MHDDoS-GUI writes successfully bypassed cookies to a local token cache file at `data/assets/token_cache.json` to avoid re-running heavy browser solvers.
* **Problem**: Cached tokens cause subsequent test cases to hit cache logic and bypass the actual solver code path.
* **Solution**: The global `clean_token_cache` fixture (configured as `autouse=True` in `tests/conftest.py`) automatically deletes `token_cache.json` and clears the in-memory cache between *every single test run*. Do not attempt to write custom cache clear logic inside individual test files.

### 2. Import-Time Networking Side-Effects
Third-party engines like `hrequests` perform automated HTTP requests to GitHub during module imports to retrieve compiled binaries. This causes pytest collection to crash if the network is rate-limited or restricted.
* **Rule**: Always mock missing or network-active imports (e.g. `hrequests`, `zendriver`, `cloudflare_bypass_for_scraping`) at module scope in a conditional import helper:
  ```python
  import sys
  from unittest.mock import MagicMock
  
  # Stub imports before loading core engines
  def _mock_if_missing(name):
      if name not in sys.modules:
          sys.modules[name] = MagicMock()
          
  _mock_if_missing("hrequests")
  _mock_if_missing("zendriver")
  ```

### 3. Global `sys.modules` Cleanliness
Overriding modules dynamically (e.g., swapping `DrissionPage` or `camoufox` with a mock) can pollute the global Python runtime, causing unrelated tests in subsequent test suites to fail.
* **Rule**: Never mutate `sys.modules` globally. Wrap package overrides in context-bounded `patch.dict('sys.modules', ...)` blocks:
  ```python
  from unittest.mock import patch, MagicMock
  
  mock_drission = MagicMock()
  with patch.dict('sys.modules', {'DrissionPage': mock_drission}):
      # Execute test code that imports DrissionPage
      ...
  ```

### 4. Zero-Network / Mock Targets
Tests must execute completely offline.
* Do not configure real target URLs (`yarl.URL("https://example.com")`). Use `unittest.mock.MagicMock` stubbed with attributes like `.host`, `.port`, and `.human_repr()` instead.
* Mock `HttpFlood.open_connection()` with `AsyncMock` to prevent actual socket connection attempts when validating network loop states.
* Mock `BrowserEngine.solve_cf` to return predefined cookie strings (`"cf_clearance=ok", "UA"`) to simulate bypass conditions.

### 5. Loop State Safety
Avoid referencing closed event loops in non-async tests. The state manager (`src/core/state_manager.py`) uses `main_loop.call_soon_threadsafe(...)` to synchronize challenge status.
* If testing non-async code that accesses state managers, ensure the `main_loop` checks `not is_closed()` before dispatching events.

---

## 🛠️ Testing Reference

### Run the entire suite
```bash
python -m pytest -v
```

### Run tests in a specific folder
```bash
python -m pytest tests/bypass -v
```

### Run a single test file
```bash
python -m pytest tests/network/test_cfbuam_circuit_breaker.py -v
```

### Run a single test case
```bash
python -m pytest tests/bypass/test_all_engines.py::test_tier0_flaresolverr_api_success -v
```
