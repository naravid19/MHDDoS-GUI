import asyncio
import sys
from pathlib import Path
from socket import AF_INET, SOCK_STREAM

sys.path.append(str(Path.cwd()))

try:
    from PyRoxy import Proxy, ProxyType
    PROXIES_AVAILABLE = True
except ImportError:
    PROXIES_AVAILABLE = False

async def simulate_scoring():
    if not PROXIES_AVAILABLE:
        print("PyRoxy not found")
        return
    
    # Use 1.1.1.1:80 as a dummy proxy to test the logic
    proxy = Proxy("1.1.1.1", 80, ProxyType.HTTP)
    print(f"[*] Simulating scoring for {proxy}...")
    
    try:
        # This is what TacticalProxyValidator._check does now:
        s = await asyncio.to_thread(proxy.open_socket, AF_INET, SOCK_STREAM)
        print(f"[+] Success! Socket opened: {s}")
        if s:
            s.close()
    except Exception as e:
        print(f"[-] Failure! open_socket failed: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_scoring())
