import sys
from pathlib import Path

sys.path.append(str(Path.cwd()))

try:
    from PyRoxy import Proxy, ProxyType
    p = Proxy("1.1.1.1", 80, ProxyType.HTTP)
    print(f"Signature of open_socket: {p.open_socket.__doc__}")
    # Try to get more info via inspect
    import inspect
    print(f"Full signature: {inspect.signature(p.open_socket)}")
except Exception as e:
    print(f"Error: {e}")
