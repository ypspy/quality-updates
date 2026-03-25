import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import editor.source_fetch as sf


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/a",
    ],
)
def test_rejects_non_http_schemes(url: str):
    with pytest.raises(ValueError):
        sf.validate_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://10.0.0.1/",
        "http://[::ffff:10.0.0.1]/",
        "http://172.16.0.1/",
        "http://192.168.0.1/",
        "http://169.254.1.1/",
        "http://[fe80::1]/",
        "http://0.0.0.0/",
    ],
)
def test_rejects_loopback_private_and_unspecified(url: str):
    with pytest.raises(ValueError):
        sf.validate_url(url)


def test_port_policy_allows_only_80_and_443(monkeypatch):
    # Hermetic DNS for hostname resolution.
    monkeypatch.setattr(sf.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))])

    assert sf.validate_url("https://example.com/").port is None
    assert sf.validate_url("https://example.com:443/").port == 443
    assert sf.validate_url("http://example.com:80/").port == 80

    with pytest.raises(ValueError):
        sf.validate_url("https://example.com:8080/")


def test_rejects_userinfo_trick():
    with pytest.raises(ValueError):
        sf.validate_url("http://good.com@127.0.0.1/")


def test_rejects_redirect_chain_to_localhost(monkeypatch):
    # Unit-test hop validation without making network calls.
    # NOTE: validate_url() resolves DNS; mock it to keep tests hermetic.
    monkeypatch.setattr(
        sf.socket,
        "getaddrinfo",
        lambda host, port, **k: [(2, 1, 6, "", ("93.184.216.34", port or 0))],
    )
    with pytest.raises(ValueError):
        sf.validate_redirect_chain(
            [
                "https://example.com/a",
                "http://127.0.0.1/",
            ]
        )


def test_validate_url_is_hermetic_via_getaddrinfo_mock(monkeypatch):
    # Avoid relying on real DNS/network: validate_url() calls socket.getaddrinfo.
    def fake_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        assert host == "example.com"
        # sockaddr[0] is IP string; pick a public IP.
        return [(2, 1, 6, "", ("93.184.216.34", port or 0))]

    monkeypatch.setattr(sf.socket, "getaddrinfo", fake_getaddrinfo)
    out = sf.validate_url("https://example.com/a")
    assert out.hostname == "example.com"


def test_fetch_url_sets_trust_env_false(monkeypatch):
    class FakeResp:
        status_code = 200
        headers = {"content-type": "text/html"}

        def iter_content(self, chunk_size=8192):
            yield b"ok"

        def close(self):
            pass

    class FakeSession:
        def __init__(self):
            self.trust_env = True
            self.cookies = type("C", (), {"clear": lambda _self: None})()
            self.last_trust_env = None

        def get(self, *args, **kwargs):
            self.last_trust_env = self.trust_env
            return FakeResp()

    fake = FakeSession()
    monkeypatch.setattr(sf.requests, "Session", lambda: fake)
    # Also avoid DNS
    monkeypatch.setattr(sf.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))])
    sf.fetch_url("https://example.com/")
    assert fake.last_trust_env is False


def test_fetch_url_rejects_redirect_to_localhost(monkeypatch):
    # Simulate a safe URL redirecting to localhost, no real network.
    class FakeResp:
        def __init__(self, status, location=None):
            self.status_code = status
            self.headers = {}
            if location is not None:
                self.headers["location"] = location

        def iter_content(self, chunk_size=8192):
            return iter(())

        def close(self):
            pass

    calls = {"n": 0}

    class FakeSession:
        def __init__(self):
            self.trust_env = True
            self.cookies = type("C", (), {"clear": lambda _self: None})()

        def get(self, url, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return FakeResp(302, "http://127.0.0.1/")
            return FakeResp(200)

    monkeypatch.setattr(sf.requests, "Session", lambda: FakeSession())
    monkeypatch.setattr(sf.socket, "getaddrinfo", lambda host, port, **k: [(2, 1, 6, "", ("93.184.216.34", port or 0))])
    with pytest.raises(ValueError):
        sf.fetch_url("https://example.com/")


def test_fetch_url_enforces_max_redirects(monkeypatch):
    class FakeResp:
        def __init__(self, status, location=None):
            self.status_code = status
            self.headers = {}
            if location is not None:
                self.headers["location"] = location

        def iter_content(self, chunk_size=8192):
            return iter(())

        def close(self):
            pass

    class FakeSession:
        def __init__(self):
            self.trust_env = True
            self.cookies = type("C", (), {"clear": lambda _self: None})()

        def get(self, url, **kwargs):
            # Always redirect to another safe URL
            return FakeResp(302, "https://example.com/next")

    monkeypatch.setattr(sf.requests, "Session", lambda: FakeSession())
    monkeypatch.setattr(sf.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))])
    with pytest.raises(ValueError):
        sf.fetch_url("https://example.com/", max_redirects=0)


def test_fetch_url_enforces_max_bytes(monkeypatch):
    class FakeResp:
        status_code = 200
        headers = {"content-type": "text/html"}

        def iter_content(self, chunk_size=8192):
            yield b"a" * 10
            yield b"b" * 10

        def close(self):
            pass

    class FakeSession:
        def __init__(self):
            self.trust_env = True
            self.cookies = type("C", (), {"clear": lambda _self: None})()

        def get(self, url, **kwargs):
            return FakeResp()

    monkeypatch.setattr(sf.requests, "Session", lambda: FakeSession())
    monkeypatch.setattr(sf.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))])
    with pytest.raises(ValueError):
        sf.fetch_url("https://example.com/", max_bytes=8)

