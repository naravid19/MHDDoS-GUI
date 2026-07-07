# tests/test_telemetry_sync.py
import pytest
import time
from unittest.mock import patch
from src.api.ws_manager import TelemetryAggregator

def test_telemetry_aggregation_frame():
    aggregator = TelemetryAggregator(emit_interval=1.0)
    
    # Simulate rapid probe events (e.g. 50ms CFBUAM probes)
    for _ in range(20):
        aggregator.record_probe(status=403, is_waf=True, latency_ms=120)
        
    frame = aggregator.get_telemetry_frame(target="readtoon.com", method="CFB")
    assert frame["target"] == "readtoon.com"
    assert frame["counters"]["waf"] == 20
    assert frame["status"]["pps"] == 20
    assert "timestamp" in frame


def test_telemetry_various_probe_types():
    aggregator = TelemetryAggregator(emit_interval=1.0)
    
    # OK probes (200 status)
    aggregator.record_probe(status=200, latency_ms=50.0)
    aggregator.record_probe(status=200, latency_ms=70.0)
    
    # WAF probes (403 status or is_waf=True)
    aggregator.record_probe(status=403, latency_ms=10.0)
    aggregator.record_probe(status=200, is_waf=True, latency_ms=20.0)
    
    # Timeout probes (is_tmo=True)
    aggregator.record_probe(status=0, is_tmo=True, latency_ms=0.0)
    
    # Error probes (is_err=True or status >= 500)
    aggregator.record_probe(status=500, latency_ms=30.0)
    aggregator.record_probe(status=503, latency_ms=40.0)
    aggregator.record_probe(status=200, is_err=True, latency_ms=50.0)
    
    # Verify aggregator counts before getting frame
    assert aggregator.ok_count == 2
    assert aggregator.waf_count == 2
    assert aggregator.tmo_count == 1
    assert aggregator.err_count == 3
    assert aggregator.probe_count == 8
    
    # Get frame
    frame = aggregator.get_telemetry_frame(target="example.com", method="GET")
    
    # Verify frame content
    assert frame["target"] == "example.com"
    assert frame["method"] == "GET"
    assert frame["counters"]["ok"] == 2
    assert frame["counters"]["waf"] == 2
    assert frame["counters"]["tmo"] == 1
    assert frame["counters"]["err"] == 3
    
    # Total latency = 50 + 70 + 10 + 20 + 0 + 30 + 40 + 50 = 270
    # Average latency calculation: total_latency / max(probe_count, 1) = 270.0 / 8 = 33.75
    assert frame["status"]["latency_ms"] == 33.75
    
    # Verify fields reset
    assert aggregator.ok_count == 0
    assert aggregator.waf_count == 0
    assert aggregator.tmo_count == 0
    assert aggregator.err_count == 0
    assert aggregator.probe_count == 0
    assert aggregator.total_latency == 0.0


def test_telemetry_pps_and_bps_calculations():
    # Use mock to control time elapsed precisely
    start_time = 1000.0
    with patch("time.time", side_effect=[start_time, start_time + 2.0]):
        aggregator = TelemetryAggregator(emit_interval=1.0)
        
        # 10 probes over 2 seconds
        for _ in range(10):
            aggregator.record_probe(status=200, latency_ms=10.0)
            
        frame = aggregator.get_telemetry_frame(target="example.com", method="GET")
        
        # PPS = probe_count / elapsed = 10 / 2.0 = 5
        assert frame["status"]["pps"] == 5
        # bps_kb = pps * 5.8 = 5 * 5.8 = 29.0
        assert frame["status"]["bps_kb"] == 29.0


def test_telemetry_elapsed_time_minimum():
    start_time = 1000.0
    with patch("time.time", side_effect=[start_time, start_time + 0.5]):
        aggregator = TelemetryAggregator(emit_interval=1.0)
        
        # 10 probes over 0.5 seconds
        for _ in range(10):
            aggregator.record_probe(status=200, latency_ms=10.0)
            
        frame = aggregator.get_telemetry_frame(target="example.com", method="GET")
        
        # Since elapsed is max(0.5, 1.0) = 1.0
        # PPS = probe_count / 1.0 = 10 / 1.0 = 10
        assert frame["status"]["pps"] == 10


def test_telemetry_no_probes():
    aggregator = TelemetryAggregator(emit_interval=1.0)
    frame = aggregator.get_telemetry_frame(target="example.com", method="GET")
    assert frame["status"]["pps"] == 0
    assert frame["status"]["bps_kb"] == 0.0
    assert frame["status"]["latency_ms"] == 0.0
    assert frame["counters"]["ok"] == 0
    assert frame["counters"]["waf"] == 0
    assert frame["counters"]["err"] == 0
    assert frame["counters"]["tmo"] == 0
