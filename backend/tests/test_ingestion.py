"""Etapa 3: bugs de ingesta corregidos (uno por bloque) con datos sintéticos y
con los fixtures de prod/local."""
import json

import pytest

import fixture_backend as fb


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class _Session:
    def __init__(self, resp):
        self.resp = resp
        self.calls = []

    def get(self, url, params=None, **_kw):
        self.calls.append((url, params))
        return self.resp


@pytest.fixture
def fake_search(monkeypatch):
    import yf_adapter

    def install(status, payload):
        sess = _Session(_Resp(status, payload))
        monkeypatch.setattr(yf_adapter, "_ensure_session", lambda: None)
        monkeypatch.setattr(yf_adapter, "_session", sess)
        return sess
    return install


# ─────────────── bug (a): sector/industria desde la fuente en el plan B ───────────────
def test_search_profile_takes_exact_symbol_match(fake_search):
    import yf_adapter
    sess = fake_search(200, {"quotes": [
        {"symbol": "OBX", "sector": "Industrials", "industry": "X"},
        {"symbol": "O", "sector": "Real Estate", "industry": "REIT—Retail", "longname": "Realty Income"},
    ]})
    assert yf_adapter._search_profile("O") == {"sector": "Real Estate", "industry": "REIT—Retail",
                                               "name": "Realty Income"}
    assert "/v1/finance/search" in sess.calls[0][0] and sess.calls[0][1]["q"] == "O"


@pytest.mark.parametrize("status,payload", [
    (200, {"quotes": [{"symbol": "OBX", "sector": "Industrials"}]}),  # sin coincidencia exacta
    (401, {"finance": {"error": {"code": "Unauthorized"}}}),
    (200, {}),
])
def test_search_profile_returns_none_without_exact_match(fake_search, status, payload):
    import yf_adapter
    fake_search(status, payload)
    assert yf_adapter._search_profile("O") is None


@pytest.mark.parametrize("sym,sector", [("O", "Real Estate"), ("FCX", "Basic Materials"),
                                        ("NFLX", "Communication Services"), ("JPM", "Financial Services")])
def test_prod_plan_b_sector_comes_from_source(sym, sector, outputs_by_env):
    """En prod (plan B) el sector ya no depende de KNOWN_SECTORS."""
    a = outputs_by_env("prod")[sym][0]
    assert a["profile"]["sector"] == sector
    assert a["sector_info"]["mapped_sector"] != "Unknown"
