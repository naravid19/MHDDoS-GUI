import asyncio
import time
import pytest
from src.worker.service import TokenBucketRateLimiter

@pytest.mark.asyncio
async def test_token_bucket_backoff_on_high_load():
    limiter = TokenBucketRateLimiter(rate=100.0, capacity=100)
    
    # Normal load
    delay_normal = await limiter.calculate_backoff(cpu_pct=40.0, ram_pct=50.0)
    assert delay_normal == 0.0
    
    # High load (CPU 88.4%, RAM 81.2%) -> Should backoff gracefully, NOT terminate workers
    delay_high = await limiter.calculate_backoff(cpu_pct=88.4, ram_pct=81.2)
    assert delay_high >= 0.05
    assert limiter.active_workers_scale == 1.0  # Keeps 100% workers active!

@pytest.mark.asyncio
async def test_token_bucket_acquire_non_blocking():
    # High rate and capacity, acquiring immediately should not block
    limiter = TokenBucketRateLimiter(rate=1000.0, capacity=10)
    start = time.monotonic()
    for _ in range(5):
        await limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1  # Fast execution

@pytest.mark.asyncio
async def test_token_bucket_exhaustion():
    # Low rate and capacity to trigger sleep when tokens are exhausted
    limiter = TokenBucketRateLimiter(rate=10.0, capacity=1)
    
    # First acquire consumes the token
    await limiter.acquire()
    assert limiter.tokens < 1.0
    
    # Second acquire should trigger wait since tokens are exhausted
    start = time.monotonic()
    await limiter.acquire()
    elapsed = time.monotonic() - start
    # refilling 1 token at rate=10.0 tokens/sec takes 0.1 seconds
    assert elapsed >= 0.08

@pytest.mark.asyncio
async def test_token_bucket_backoff_accumulation_and_capping():
    # Test that high load accumulates delay but caps it at 0.50
    limiter = TokenBucketRateLimiter(rate=100.0, capacity=100)
    
    # Initial delay is 0.0
    assert limiter.current_jitter_delay == 0.0
    
    # Let's mock asyncio.sleep within calculate_backoff so tests run fast
    # Wait, instead of mock, we can just run it since 11 calls will only accumulate up to 0.50.
    # Actually, we can temporarily patch asyncio.sleep. Or just use cpu_pct=90.0, which causes sleeps.
    # Since sleep will actually sleep, let's patch asyncio.sleep or run it directly.
    # Accumulating from 0 to 0.50 with +0.05 increments takes 10 calls:
    # 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.50
    # Running 11 calls with actual sleep might take:
    # 0.05+0.10+0.15+0.20+0.25+0.30+0.35+0.40+0.45+0.50+0.50 = 3.25 seconds.
    # Let's mock asyncio.sleep in the test to avoid delay in pytest suite.
    
    original_sleep = asyncio.sleep
    sleep_calls = []
    async def mock_sleep(delay):
        sleep_calls.append(delay)
        # do not actually sleep
        return
        
    import src.worker.service as service_module
    # We will patch asyncio.sleep inside src.worker.service.asyncio.sleep
    # Since we imported asyncio in src.worker.service, we can temporarily replace it.
    original_service_sleep = service_module.asyncio.sleep
    service_module.asyncio.sleep = mock_sleep
    
    try:
        for _ in range(12):
            await limiter.calculate_backoff(cpu_pct=90.0, ram_pct=50.0)
            
        assert limiter.current_jitter_delay == 0.50
        assert len(sleep_calls) == 12
        assert sleep_calls[0] == 0.05
        assert sleep_calls[-1] == 0.50
    finally:
        service_module.asyncio.sleep = original_service_sleep

@pytest.mark.asyncio
async def test_token_bucket_backoff_recovery():
    limiter = TokenBucketRateLimiter(rate=100.0, capacity=100)
    limiter.current_jitter_delay = 0.10
    
    # Normal/low load should decrease jitter delay by 0.02
    import src.worker.service as service_module
    original_service_sleep = service_module.asyncio.sleep
    async def mock_sleep(delay):
        pass
    service_module.asyncio.sleep = mock_sleep
    
    try:
        # 1st call: 0.10 - 0.02 = 0.08
        delay = await limiter.calculate_backoff(cpu_pct=40.0, ram_pct=50.0)
        assert delay == 0.08
        
        # 2nd call: 0.08 - 0.02 = 0.06
        delay = await limiter.calculate_backoff(cpu_pct=40.0, ram_pct=50.0)
        assert delay == 0.06
        
        # Recovery to 0.0
        for _ in range(4):
            delay = await limiter.calculate_backoff(cpu_pct=40.0, ram_pct=50.0)
        assert delay == 0.0
    finally:
        service_module.asyncio.sleep = original_service_sleep

@pytest.mark.asyncio
async def test_token_bucket_concurrent_requests():
    # rate=10.0, capacity=2
    # 10 requests total
    # 2 are immediate, 8 queue with incrementing sleeps.
    # Total time should be around 0.8 seconds (>= 0.7s)
    limiter = TokenBucketRateLimiter(rate=10.0, capacity=2)
    
    async def task():
        await limiter.acquire()
        
    start = time.monotonic()
    await asyncio.gather(*(task() for _ in range(10)))
    elapsed = time.monotonic() - start
    
    assert elapsed >= 0.7

