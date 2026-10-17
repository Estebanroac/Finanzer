"""F6: la búsqueda en Yahoo usa la sesión que crea `_ensure_session`, no una copia de antes (None en frío)."""
import main
import yf_adapter


class _Resp:
    status_code = 200

    def json(self):
        return {"quotes": [{"symbol": "ZZZ", "shortname": "Zeta", "quoteType": "EQUITY"}]}


class _Sess:
    def get(self, *a, **k):
        return _Resp()


def test_search_works_in_a_fresh_process(monkeypatch):
    monkeypatch.setattr(yf_adapter, "_session", None)
    monkeypatch.setattr(yf_adapter, "_ensure_session", lambda: setattr(yf_adapter, "_session", _Sess()))
    assert main._yahoo_search("zeta") == [{"ticker": "ZZZ", "name": "Zeta", "score": 50}]
