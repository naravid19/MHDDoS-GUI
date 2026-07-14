import asyncio
import sys
from pathlib import Path

# Add current dir to sys.path to from src.core import engine as start.py components if needed
sys.path.append(str(Path.cwd()))

try:
    from PyRoxy import Proxy, ProxyType
    PROXIES_AVAILABLE = True
except ImportError:
    PROXIES_AVAILABLE = False
    print("PyRoxy not found")

async def test_proxy():
    if not PROXIES_AVAILABLE:
        return
    
    # Test with a known public proxy or just check if the method exists
    p = Proxy("1.1.1.1", 80, ProxyType.HTTP)
    print(f"Testing proxy: {p}")
    try:
        # family=2 (AF_INET), type=1 (SOCK_STREAM), timeout=5
        s = p.open_socket(2, 1, 5)
        print(f"Socket opened: {s}")
        if s:
            s.close()
    except Exception as e:
        print(f"open_socket failed: {e}")

if __name__ == "__main__":
    if PROXIES_AVAILABLE:
        asyncio.run(test_proxy())
