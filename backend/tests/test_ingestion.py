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


# ─────────────── bug (b): año previo en el plan B (Piotroski) ───────────────
@pytest.mark.parametrize("sym", fb.TICKERS)
def test_prod_plan_b_has_prior_year_for_piotroski(sym, outputs_by_env):
    """El plan B ejecuta el enriquecimiento con los estados del ejercicio anterior."""
    pf = outputs_by_env("prod")[sym][0]["piotroski_f"]
    assert pf["fiscal_year"].startswith("FY") and " vs FY" in pf["fiscal_year"]
    assert "Sin datos de acciones históricas" not in pf["details"]["no_dilution"]["detail"]
    assert "Sin datos" not in pf["details"]["roa_improved"]["detail"]


def test_prod_plan_b_prior_year_values_come_from_statements(fixture_store):
    """_prior_year de NFLX en prod = columna FY2024 de los estados de yfinance."""
    import yf_adapter
    st = fb.FixtureStore(fb.fixtures_dir("prod"))
    st.load("NFLX")
    inc = fb.obj_to_df(st.yf["NFLX"]["income_stmt"])
    with fb.replay(fb.fixtures_dir("prod")) as store:
        fb.run_analysis("NFLX", store)
        prior = dict(yf_adapter._cache["NFLX"][1]["_prior_year"])
    assert prior["_fiscal_year"] == "2024"
    assert prior["revenue"] == pytest.approx(float(inc.loc["Total Revenue"].iloc[1]))


# ─────────────── bug (c): acciones en circulación y misma base en buyback ───────────────
@pytest.mark.parametrize("env", ["local", "prod"])
def test_nflx_no_dilution_uses_ordinary_shares(env, outputs_by_env):
    """NFLX recompró (4.28 -> 4.22B en circulación): no hay dilución."""
    a = outputs_by_env(env)["NFLX"][0]
    assert a["piotroski_f"]["details"]["no_dilution"]["passed"] is True


@pytest.mark.parametrize("env", ["local", "prod"])
def test_buyback_yield_same_fiscal_basis(env, outputs_by_env, fixture_store):
    """buyback = (FY previo − FY actual) / FY previo, ambos Ordinary Shares Number."""
    bs = fb.obj_to_df(fixture_store.yf["NFLX"]["balance_sheet"])
    cur, prev = (float(bs.loc["Ordinary Shares Number"].iloc[i]) for i in (0, 1))
    km = outputs_by_env(env)["NFLX"][0]["key_metrics"]
    assert km["buyback_yield"] == pytest.approx((prev - cur) / prev, rel=1e-9)
    assert 0 < km["buyback_yield"] < 0.03
