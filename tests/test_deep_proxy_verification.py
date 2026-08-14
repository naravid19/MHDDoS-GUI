import asyncio
import pytest
from PyRoxy import Proxy, ProxyType
from src.core.engine import _check_proxy_async, TacticalProxy


@pytest.mark.asyncio
async def test_check_proxy_async_invalid_proxy_socket_garbage():
    """Test proxy verification against a socket returning invalid non-proxy response."""
    async def handle_client(reader, writer):
        await reader.read(100)
        writer.write(b"NOT_A_PROXY_PROTOCOL_RESPONSE\r\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()

    try:
        raw_proxy = Proxy(host, port, ProxyType.SOCKS5)
        result = await _check_proxy_async("target.test", raw_proxy, timeout=1.0)
        assert isinstance(result, TacticalProxy)
        assert result.is_protocol_verified is False
        assert result.latency_ms == 5000.0
        assert result.http_status == 0
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_check_proxy_async_invalid_socks4_socket():
    """Test SOCKS4 proxy verification against an invalid server response."""
    async def handle_client(reader, writer):
        await reader.read(100)
        writer.write(b"\xff\xff\x00\x00\x00\x00\x00\x00")  # Invalid SOCKS4 status
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()

    try:
        raw_proxy = Proxy(host, port, ProxyType.SOCKS4)
        result = await _check_proxy_async("target.test", raw_proxy, timeout=1.0)
        assert isinstance(result, TacticalProxy)
        assert result.is_protocol_verified is False
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_check_proxy_async_invalid_http_socket():
    """Test HTTP proxy verification against an invalid HTTP response (e.g. 500 status)."""
    async def handle_client(reader, writer):
        await reader.read(100)
        writer.write(b"HTTP/1.1 500 Internal Server Error\r\n\r\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()

    try:
        raw_proxy = Proxy(host, port, ProxyType.HTTP)
        result = await _check_proxy_async("target.test", raw_proxy, timeout=1.0)
        assert isinstance(result, TacticalProxy)
        assert result.is_protocol_verified is False
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_check_proxy_async_connection_close_immediately():
    """Test proxy verification against a server that closes connection immediately."""
    async def handle_client(reader, writer):
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()

    try:
        raw_proxy = Proxy(host, port, ProxyType.SOCKS5)
        result = await _check_proxy_async("target.test", raw_proxy, timeout=1.0)
        assert isinstance(result, TacticalProxy)
        assert result.is_protocol_verified is False
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_check_proxy_async_timeout():
    """Test proxy verification timing out on a hanging server."""
    async def handle_client(reader, writer):
        try:
            await asyncio.sleep(2.0)
        except (asyncio.CancelledError, Exception):
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()

    try:
        raw_proxy = Proxy(host, port, ProxyType.SOCKS5)
        result = await _check_proxy_async("target.test", raw_proxy, timeout=0.2)
        assert isinstance(result, TacticalProxy)
        assert result.is_protocol_verified is False
        assert result.latency_ms == 5000.0
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_check_proxy_async_valid_socks5():
    """Test SOCKS5 proxy verification with a valid mock server."""
    async def handle_client(reader, writer):
        data = await reader.read(3)
        if data == b"\x05\x01\x00":
            writer.write(b"\x05\x00")
            await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()

    try:
        raw_proxy = Proxy(host, port, ProxyType.SOCKS5)
        result = await _check_proxy_async("target.test", raw_proxy, timeout=1.0)
        assert isinstance(result, TacticalProxy)
        assert result.is_protocol_verified is True
        assert result.http_status == 200
        assert result.latency_ms < 5000.0
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_check_proxy_async_valid_socks4():
    """Test SOCKS4 proxy verification with a valid mock server."""
    async def handle_client(reader, writer):
        data = await reader.read(100)
        if len(data) >= 8 and data[:2] == b"\x04\x01":
            writer.write(b"\x00\x5a\x00\x00\x00\x00\x00\x00")
            await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()

    try:
        raw_proxy = Proxy(host, port, ProxyType.SOCKS4)
        result = await _check_proxy_async("target.test", raw_proxy, timeout=1.0)
        assert isinstance(result, TacticalProxy)
        assert result.is_protocol_verified is True
        assert result.http_status == 200
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_check_proxy_async_valid_http():
    """Test HTTP proxy verification with a valid CONNECT mock server."""
    async def handle_client(reader, writer):
        data = await reader.read(100)
        if b"CONNECT" in data:
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()

    try:
        raw_proxy = Proxy(host, port, ProxyType.HTTP)
        result = await _check_proxy_async("target.test", raw_proxy, timeout=1.0)
        assert isinstance(result, TacticalProxy)
        assert result.is_protocol_verified is True
        assert result.http_status == 200
    finally:
        server.close()
        await server.wait_closed()
