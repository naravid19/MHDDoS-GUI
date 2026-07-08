import pytest
from yarl import URL
from src.core.engine import promote_target_for_waf


def test_promote_target_for_waf() -> None:
    """Verify that CFB/BYPASS methods against HTTP port 80 are auto-promoted to HTTPS port 443 without explicit :80 port."""
    url, port = promote_target_for_waf("http://example.com:80/attack", "CFB", 80)
    assert url.startswith("https://")
    assert ":80/" not in url
    assert ":80" not in url
    assert URL(url).port == 443
    assert port == 443

    url_tls, port_tls = promote_target_for_waf("http://example.com", "TLS", 80)
    assert url_tls.startswith("https://")
    assert ":80" not in url_tls
    assert URL(url_tls).port == 443
    assert port_tls == 443

    # Direct UDP/TCP methods should NOT promote
    url_udp, port_udp = promote_target_for_waf("http://example.com:80", "UDP", 80)
    assert url_udp.startswith("http://")
    assert port_udp == 80
