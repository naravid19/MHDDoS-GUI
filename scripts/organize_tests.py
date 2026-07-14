# scripts/organize_tests.py
import os
import shutil
from pathlib import Path

# Paths
TESTS_ROOT = Path("tests")
BYPASS_DIR = TESTS_ROOT / "bypass"
NETWORK_DIR = TESTS_ROOT / "network"
API_WORKER_DIR = TESTS_ROOT / "api_worker"
ATTACK_DIR = TESTS_ROOT / "attack"
PERFORMANCE_DIR = TESTS_ROOT / "performance"

# Ensure directories exist
for directory in [BYPASS_DIR, NETWORK_DIR, API_WORKER_DIR, ATTACK_DIR, PERFORMANCE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
    # Add an __init__.py so Python treats it as a package if needed (good practice)
    init_file = directory / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

# Categorization mapping
FILE_MAPPING = {
    # 1. Bypass & Scraping Engines (Tiers 0-4)
    "test_flaresolverr_tier0.py": BYPASS_DIR,
    "test_tier0_preflight.py": BYPASS_DIR,
    "test_waterfall_tier1.py": BYPASS_DIR,
    "test_waterfall_tier2.py": BYPASS_DIR,
    "test_waterfall_tier3.py": BYPASS_DIR,
    "test_waterfall_tier4.py": BYPASS_DIR,
    "test_waterfall_imports.py": BYPASS_DIR,
    "test_waterfall_master.py": BYPASS_DIR,
    "test_all_engines.py": BYPASS_DIR,
    "test_bypass_engines.py": BYPASS_DIR,
    "test_bypass_engines_visual.py": BYPASS_DIR,
    "test_engine_botasaurus_css.py": BYPASS_DIR,
    "test_cf.py": BYPASS_DIR,
    "test_cfb_cascade.py": BYPASS_DIR,
    "test_turnstile_solver.py": BYPASS_DIR,
    "test_waf_bypass_tiers.py": BYPASS_DIR,
    "test_waf_auto_promotion.py": BYPASS_DIR,

    # 2. Network & Proxy Management
    "test_proxy_guard.py": NETWORK_DIR,
    "test_proxy_scoring.py": NETWORK_DIR,
    "test_proxy_validator_async.py": NETWORK_DIR,
    "test_proxy_concurrency.py": NETWORK_DIR,
    "test_proxy_debug.py": NETWORK_DIR,
    "test_proxy_err.py": NETWORK_DIR,
    "test_cfbuam_circuit_breaker.py": NETWORK_DIR,
    "test_concurrency_limiter.py": NETWORK_DIR,
    "test_debugger_proxy_filter.py": NETWORK_DIR,
    "test_engine_latency.py": NETWORK_DIR,

    # 3. Core App, Worker & API State
    "test_api_integration.py": API_WORKER_DIR,
    "test_api_ws_sync.py": API_WORKER_DIR,
    "test_state_manager.py": API_WORKER_DIR,
    "test_ui_state_machine.py": API_WORKER_DIR,
    "test_ws_manager.py": API_WORKER_DIR,
    "test_worker_service.py": API_WORKER_DIR,
    "test_worker_service_buffered.py": API_WORKER_DIR,
    "test_worker_termination.py": API_WORKER_DIR,
    "test_telemetry_pipeline.py": API_WORKER_DIR,
    "test_telemetry_sync.py": API_WORKER_DIR,
    "test_persistence.py": API_WORKER_DIR,
    "test_runtime_stability.py": API_WORKER_DIR,
    "test_terminal_filtering.py": API_WORKER_DIR,

    # 4. Attack & CLI Builder
    "test_methods.py": ATTACK_DIR,
    "test_new_methods.py": ATTACK_DIR,
    "test_l7_methods.py": ATTACK_DIR,
    "test_command_builder.py": ATTACK_DIR,
    "test_preflight.py": ATTACK_DIR,
    "test_ua.py": ATTACK_DIR,
    "test_os_aware_scaler.py": ATTACK_DIR,
    "test_signature.py": ATTACK_DIR,
    "test_paths.py": ATTACK_DIR,

    # 5. Performance & Stress Scripts (non-pytest)
    "comprehensive_perf_test.py": PERFORMANCE_DIR,
    "comprehensive_test.py": PERFORMANCE_DIR,
    "comprehensive_waterfall_test.py": PERFORMANCE_DIR,
    "deep_stress_debug_test.py": PERFORMANCE_DIR,
    "detailed_test.py": PERFORMANCE_DIR,
    "perf_pipeline_test.py": PERFORMANCE_DIR,
    "real_world_test.py": PERFORMANCE_DIR,
    "bypass_script.py": PERFORMANCE_DIR,
    "parse_logs.py": PERFORMANCE_DIR,
    "patch_test.py": PERFORMANCE_DIR,
}

# Perform the file moves
print("[*] Organizing test files...")
moved_count = 0
for filename, target_dir in FILE_MAPPING.items():
    src_path = TESTS_ROOT / filename
    if src_path.exists():
        dest_path = target_dir / filename
        print(f"  -> Moving: {src_path} -> {dest_path}")
        shutil.move(str(src_path), str(dest_path))
        moved_count += 1

print(f"[+] Moved {moved_count} files successfully.")

# Update pytest.ini
PYTEST_INI = Path("pytest.ini")
if PYTEST_INI.exists():
    print("[*] Updating pytest.ini configuration...")
    content = """[pytest]
asyncio_mode = auto
pythonpath = .
testpaths =
    tests/core
    tests/bypass
    tests/network
    tests/api_worker
    tests/attack
"""
    PYTEST_INI.write_text(content, encoding="utf-8")
    print("[+] pytest.ini updated successfully.")
else:
    print("[!] pytest.ini not found!")
