"""
Moneda y clase de acciones de los estados frente a las de la cotización (etapa 11b).

Un ADR (TSM, ASML, NVO) cotiza en USD pero presenta sus estados en su moneda
(TWD, EUR, DKK) y por acción ordinaria; BRK-B cotiza la clase B y los estados
dan el BPA por acción de clase A. Sin reexpresarlos, el P/E, el DCF y el
EV/EBITDA mezclan unidades (TSM salía con P/E 5.1 y DCF +1909 %).

Aquí se reexpresan los estados de yfinance, en un solo punto, a la unidad del
precio:
  · moneda: tipo de cambio de Yahoo ("XXX=X" = unidades de XXX por 1 USD; los
    cruces pasan por el USD). Balance al CIERRE de la fecha del período;
    resultados y flujos al PROMEDIO de los cierres diarios del período (12 meses
    en un ejercicio, 3 en un trimestre). Sin tipo de cambio, el análisis se
    rechaza (CurrencyConversionError): nunca se mezclan monedas.
  · clase: factor = acciones de los estados / acciones de la clase que cotiza
    (capitalización / precio). Fuera de la tolerancia (config), el BPA se
    multiplica por el factor y los recuentos de acciones se dividen por él, así
    BPA × acciones = beneficio y todo lo "por acción" queda en la clase del precio.
Lo que no es un importe (recuentos de acciones, tasa impositiva) no se convierte
de moneda. Todo queda registrado (summary() -> data_provenance.currency).
"""
import math
import threading
from typing import Any, Dict, Optional, Tuple

from settings import cfg

_V = cfg("validation.currency")
_ADR = cfg("adr")


def official_factor(symbol: Optional[str]) -> Optional[Dict[str, Any]]:
    """Factor oficial de clase (config/adr.toml): acciones de los estados por título cotizado, con su fuente."""
    ent = (_ADR["factors"].get((symbol or "").upper()))
    return dict(ent) if ent is not None else None


def nearest_simple_ratio(x: float) -> Optional[float]:
    """La fracción simple (n o 1/n, n ≤ inferred_max_ratio) más cercana a `x` si está a ≤ inferred_tolerance."""
    if not x or x <= 0:
        return None
    n = round(x) if x >= 1 else round(1.0 / x)
    if not 1 <= n <= _ADR["inferred_max_ratio"]:
        return None
    cand = float(n) if x >= 1 else 1.0 / n
    return cand if abs(x / cand - 1.0) <= _ADR["inferred_tolerance"] else None


def _ratio_txt(f: float) -> str:
    return f"{f:g}" if f >= 1 else f"1/{round(1 / f)}"

# Subunidades de cotización (precio en peniques, etc.): moneda base y factor.
SUBUNITS = {"GBp": ("GBP", 0.01), "GBX": ("GBP", 0.01), "ZAc": ("ZAR", 0.01), "ILA": ("ILS", 0.01)}

STATEMENT_ATTRS = {
    "income_stmt": ("flow", 12), "cashflow": ("flow", 12), "balance_sheet": ("balance", None),
    "quarterly_income_stmt": ("flow", 3), "quarterly_cashflow": ("flow", 3),
    "quarterly_balance_sheet": ("balance", None),
}


# Etapa 11b: nombres alternativos de filas (emisores IFRS y variantes de Yahoo). Si falta la
# fila canónica, se crea desde la primera alternativa con dato. El resto del motor solo
# conoce el nombre canónico.
ROW_ALIASES = {
    "Operating Cash Flow": ("Cash Flow From Continuing Operating Activities",),
    "Capital Expenditure": ("Purchase Of PPE",),
    "Depreciation And Amortization": ("Depreciation Amortization Depletion", "Depreciation"),
    "Common Stock Dividend Paid": ("Cash Dividends Paid",),
}


def add_row_aliases(df):
    """(df con las filas canónicas que faltaban, [(canónica, alternativa usada)])."""
    used = []
    if df is None or getattr(df, "empty", True):
        return df, used
    out = None
    for canon, alts in ROW_ALIASES.items():
        if canon in df.index and df.loc[canon].notna().any():
            continue
        alt = next((a for a in alts if a in df.index and df.loc[a].notna().any()), None)
        if alt is None:
            continue
        out = df.copy() if out is None else out
        out.loc[canon] = df.loc[alt]
        used.append((canon, alt))
    # FCF por definición si la fuente no lo da (OCF + capex, capex en negativo).
    cur = out if out is not None else df
    if ("Free Cash Flow" not in cur.index or not cur.loc["Free Cash Flow"].notna().any()) and \
            "Operating Cash Flow" in cur.index and "Capital Expenditure" in cur.index:
        out = cur.copy() if out is None else out
        out.loc["Free Cash Flow"] = cur.loc["Operating Cash Flow"] + cur.loc["Capital Expenditure"]
        used.append(("Free Cash Flow", "Operating Cash Flow + Capital Expenditure"))
    return (out if out is not None else df), used


class CurrencyConversionError(RuntimeError):
    """Estados en otra moneda y sin tipo de cambio: el análisis no se hace."""


def is_share_count(row: str) -> bool:
    return "Shares" in row or "Share Issued" in row


def is_not_amount(row: str) -> bool:
    """Filas que no son importes: recuentos de acciones y tasas."""
    return is_share_count(row) or "Tax Rate" in row


def is_per_share(row: str) -> bool:
    return "EPS" in row


def base_currency(cur: Optional[str]) -> Tuple[Optional[str], float]:
    """("GBp") -> ("GBP", 0.01); ("USD") -> ("USD", 1.0)."""
    if not cur:
        return None, 1.0
    return SUBUNITS.get(cur, (cur.upper(), 1.0))


def fx_symbol(cur: str) -> str:
    """Símbolo de Yahoo de la divisa frente al USD: "TWD=X" (TWD por 1 USD)."""
    return f"{cur}=X"


class FxRates:
    """Tipo de cambio diario `px` por 1 `fin` (cierres de Yahoo, ya cruzados vía USD)."""

    def __init__(self, fin: str, px: str, closes):
        self.fin, self.px = fin, px
        self.closes = closes.sort_index()   # pandas Series indexada por fecha (sin zona)

    def close_at(self, d) -> float:
        """Cierre en la fecha o el último anterior (fin de semana o festivo)."""
        import pandas as pd
        s = self.closes[self.closes.index <= pd.Timestamp(d)]
        if s.empty:
            raise CurrencyConversionError(
                f"sin tipo de cambio {self.fin}→{self.px} en {pd.Timestamp(d).date()} o antes")
        return float(s.iloc[-1])

    def average(self, start, end) -> float:
        """Promedio de los cierres diarios en (start, end]."""
        import pandas as pd
        s = self.closes[(self.closes.index > pd.Timestamp(start)) & (self.closes.index <= pd.Timestamp(end))]
        if len(s) < _V["min_fx_days"]:
            raise CurrencyConversionError(
                f"tipo de cambio {self.fin}→{self.px} incompleto entre {pd.Timestamp(start).date()} y "
                f"{pd.Timestamp(end).date()}")
        return float(s.mean())


def fetch_fx(fin: str, px: str, ticker_cls) -> FxRates:
    """Cierres diarios de Yahoo para el cruce fin→px. `ticker_cls` es yfinance.Ticker
    (inyectable: en los tests lo sustituye el replay de fixtures)."""
    import pandas as pd

    def _usd_per_unit(cur):   # "TWD=X" da TWD por USD: 1 TWD = 1/close USD
        if cur == "USD":
            return None
        h = ticker_cls(fx_symbol(cur)).history(period=_V["fx_history_period"], interval="1d", auto_adjust=False)
        if h is None or getattr(h, "empty", True) or "Close" not in h:
            raise CurrencyConversionError(f"Yahoo no devolvió el tipo de cambio {fx_symbol(cur)}")
        c = h["Close"].dropna()
        c = c[c > 0]
        if c.empty:
            raise CurrencyConversionError(f"Yahoo no devolvió el tipo de cambio {fx_symbol(cur)}")
        # Fecha del cierre tal cual (sin pasar por UTC: un cierre de Londres a las 00:00
        # de verano caería el día anterior). Sirve igual para Timestamps y para texto.
        idx = pd.to_datetime([str(x)[:10] for x in c.index])
        return pd.Series(1.0 / c.to_numpy(dtype=float), index=idx)

    try:
        f, p = _usd_per_unit(fin), _usd_per_unit(px)
    except CurrencyConversionError:
        raise
    except Exception as e:
        raise CurrencyConversionError(f"no se pudo descargar el tipo de cambio {fin}→{px}: {type(e).__name__}") from e
    if f is None:          # fin = USD: px por 1 USD = 1 / (USD por 1 px)
        s = 1.0 / p
    elif p is None:        # px = USD
        s = f
    else:                  # cruce vía USD
        df = pd.concat([f, p], axis=1, join="inner").dropna()
        s = df.iloc[:, 0] / df.iloc[:, 1]
    s = s[~s.index.duplicated(keep="last")]
    return FxRates(fin, px, s)


class StatementContext:
    """Cómo reexpresar los estados de un símbolo en la unidad de su cotización."""

    def __init__(self, symbol: str, price_currency: Optional[str], statement_currency: Optional[str],
                 currency_source: str, price_shares: Optional[float], ticker_cls):
        self.symbol = symbol
        self.price_currency_raw = price_currency
        px, px_unit = base_currency(price_currency)
        fin, fin_unit = base_currency(statement_currency)
        self.price_currency, self.statement_currency = px, fin
        # Importe de los estados -> unidad del precio (GBP -> GBp: × 100).
        self.subunit = fin_unit / px_unit
        self.currency_source = currency_source
        self.price_shares = price_shares
        self._ticker_cls = ticker_cls
        self.convert_currency = bool(px and fin and px != fin) or self.subunit != 1.0
        self.fx: Optional[FxRates] = None
        self.class_factor: Optional[float] = None
        self.class_detail: Optional[Dict[str, Any]] = None
        self.class_applied = False
        self.rates: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()
        self._class_done = False
        self._cache: Dict[str, Any] = {}
        self.row_aliases: Dict[str, list] = {}   # estado -> [(fila canónica, alternativa)]

    # ── preparación (una vez por fetch) ──
    def prepare_fx(self) -> None:
        if self.convert_currency and self.price_currency != self.statement_currency and self.fx is None:
            self.fx = fetch_fx(self.statement_currency, self.price_currency, self._ticker_cls)

    def prepare_class(self, raw_balance, raw_quarterly_balance=None) -> None:
        """Factor de clase con el último recuento de acciones de los estados."""
        with self._lock:
            if self._class_done:
                return
            self._class_done = True
            stmt_sh, when = None, None
            for df in (raw_quarterly_balance, raw_balance):
                if df is None or getattr(df, "empty", True):
                    continue
                for row in ("Ordinary Shares Number", "Share Issued"):
                    if row in df.index:
                        vals = [(c, v) for c, v in df.loc[row].items() if v == v and v]
                        if vals:
                            when, stmt_sh = vals[0]
                            break
                if stmt_sh:
                    break
            implied = (float(stmt_sh) / float(self.price_shares)) if (stmt_sh and self.price_shares) else None
            counts = ({"statement_shares": float(stmt_sh), "price_shares": float(self.price_shares),
                       "statement_shares_date": str(getattr(when, "date", lambda: when)())}
                      if implied is not None else {})
            official = official_factor(self.symbol)
            if official is not None:
                self._set_official(official, implied, counts)
                return
            if implied is None:
                self.class_detail = {"factor": None, "applied": False, "basis": None,
                                     "reason": "sin acciones de los estados o de la cotización"}
                return
            self._set_inferred(implied, counts)

    def _set_official(self, official: Dict[str, Any], implied: Optional[float], counts: Dict[str, Any]) -> None:
        """Fase 2b (T1): factor del depositario (config/adr.toml). El implícito solo comprueba: un desfase por encima
        de la tolerancia son recompras o emisiones entre el balance y la cotización, y se anota sin tocar el factor."""
        f = official["factor"]
        self.class_factor = f
        self.class_applied = not math.isclose(f, 1.0)
        self.class_detail = {"factor": f, "applied": self.class_applied, "basis": "oficial",
                             "official": dict(official), "implied": implied, **counts}
        if implied is None:
            return
        dev = implied / f - 1.0
        if abs(dev) > _ADR["implied_tolerance"]:
            px_in_stmt = counts["price_shares"] * f
            self.class_detail["implied_check"] = {
                "implied": implied, "deviation": dev, "price_shares_in_statement_class": px_in_stmt,
                "note": (f"recompras/emisiones desde el cierre: las acciones de la cotización ({px_in_stmt:,.0f} en "
                         f"la clase de los estados) son un {abs(1 / (1 + dev) - 1):.1%} "
                         f"{'menos' if dev > 0 else 'más'} que las del balance al "
                         f"{counts['statement_shares_date']} ({counts['statement_shares']:,.0f}); "
                         f"factor implícito {implied:.3f} frente al oficial {f:g}")}

    def _set_inferred(self, implied: float, counts: Dict[str, Any]) -> None:
        """Fase 2b (T1, propuesta pendiente de aprobación): emisor sin factor oficial en la tabla."""
        tol = _V["share_class_tolerance"]
        base = {"implied": implied, "tolerance": tol, **counts}
        if 1.0 / tol <= implied <= tol:
            self.class_factor, self.class_applied = implied, False
            self.class_detail = {"factor": implied, "applied": False, "basis": "misma_clase", **base}
            return
        snapped = nearest_simple_ratio(implied)
        if snapped is not None:
            self.class_factor, self.class_applied = snapped, True
            self.class_detail = {"factor": snapped, "applied": True, "basis": "inferido", **base,
                                 "note": f"factor inferido ({implied:.3f} ajustado a {_ratio_txt(snapped)}), sin "
                                         "verificar con el depositario"}
            return
        self.class_factor, self.class_applied = implied, True
        self.class_detail = {"factor": implied, "applied": True, "basis": "implicito", **base,
                             "note": f"factor implícito {implied:.3f} sin fracción simple a menos del "
                                     f"{_ADR['inferred_tolerance']:.0%}: puede llevar recompras o emisiones entre el "
                                     "balance y la cotización; sin verificar con el depositario"}

    @property
    def active(self) -> bool:
        return self.convert_currency or self.class_applied

    # ── conversión de un estado ──
    def convert(self, attr: str, df):
        """El estado `attr` en la moneda y la clase de la cotización (copia)."""
        if df is None or getattr(df, "empty", True) or attr not in STATEMENT_ATTRS or not self.active:
            return df
        with self._lock:
            if attr in self._cache:
                return self._cache[attr]
        import pandas as pd
        kind, months = STATEMENT_ATTRS[attr]
        out = df.astype("float64", copy=True) if all(str(t).startswith(("float", "int")) for t in df.dtypes) \
            else df.copy()
        amount_rows = [r for r in df.index if not is_not_amount(str(r))]
        # El BPA de Yahoo no siempre va en la clase de los recuentos: en BRK-B ya viene por
        # acción B mientras las acciones vienen en equivalentes A. Solo se reexpresa si está
        # en la clase de los estados (beneficio / BPA más cerca de sus acciones).
        eps_rows = ([r for r in df.index if is_per_share(str(r))]
                    if self.class_applied and self._eps_in_statement_class(df) else [])
        # Ídem para los recuentos: TSM da las acciones medias del estado de resultados ya en
        # ADR y las del balance en acciones ordinarias. Cada fila se juzga por su último valor.
        share_rows = ([r for r in df.index if is_share_count(str(r)) and self._in_statement_class(df.loc[r])]
                      if self.class_applied else [])
        used = {}
        for col in df.columns:
            rate = 1.0
            if self.convert_currency:
                if self.fx is not None:
                    d = pd.Timestamp(col)
                    rate = (self.fx.close_at(d) if kind == "balance"
                            else self.fx.average(d - pd.DateOffset(months=months), d))
                rate *= self.subunit
                used[str(pd.Timestamp(col).date())] = rate
            if rate != 1.0 and amount_rows:
                out.loc[amount_rows, col] = pd.to_numeric(df.loc[amount_rows, col], errors="coerce") * rate
            if self.class_applied:
                if eps_rows:
                    out.loc[eps_rows, col] = pd.to_numeric(out.loc[eps_rows, col], errors="coerce") * self.class_factor
                if share_rows:
                    out.loc[share_rows, col] = pd.to_numeric(df.loc[share_rows, col], errors="coerce") / self.class_factor
        with self._lock:
            if used:
                self.rates[attr] = used
            self._cache[attr] = out
        return out

    def _closer_to_statement(self, shares: float) -> bool:
        st_sh = (self.class_detail or {}).get("statement_shares")
        if not st_sh or not self.price_shares or not shares:
            return True
        return abs(math.log(abs(shares) / st_sh)) <= abs(math.log(abs(shares) / self.price_shares))

    def _in_statement_class(self, row) -> bool:
        vals = [float(v) for v in row.tolist() if v == v and v]
        return self._closer_to_statement(vals[0]) if vals else False

    def _eps_in_statement_class(self, df) -> bool:
        ni_row = next((r for r in ("Net Income Common Stockholders", "Net Income") if r in df.index), None)
        eps_row = next((r for r in ("Diluted EPS", "Basic EPS") if r in df.index), None)
        st_sh = (self.class_detail or {}).get("statement_shares")
        if ni_row is None or eps_row is None or not st_sh or not self.price_shares:
            return True
        for col in df.columns:
            try:
                ni, eps = float(df.at[ni_row, col]), float(df.at[eps_row, col])
            except (TypeError, ValueError):
                continue
            if ni == ni and eps == eps and ni and eps:
                return self._closer_to_statement(abs(ni / eps))
        return True

    def convert_amount(self, value: Optional[float], kind: str, end=None, months: int = 12) -> Optional[float]:
        """Un importe suelto de la fuente (financialData) en la moneda de la cotización."""
        if value is None or not self.convert_currency:
            return value
        import pandas as pd
        rate = 1.0
        if self.fx is not None:
            end = pd.Timestamp(end) if end is not None else self.fx.closes.index[-1]
            rate = self.fx.close_at(end) if kind == "balance" else self.fx.average(
                end - pd.DateOffset(months=months), end)
        return value * rate * self.subunit

    def summary(self) -> Dict[str, Any]:
        """Registro para data_provenance.currency y el informe."""
        out = {"statements": self.statement_currency, "price": self.price_currency_raw,
               "source": self.currency_source, "converted": bool(self.convert_currency),
               "share_class": self.class_detail}
        if self.row_aliases:
            out["row_aliases"] = {k: [f"{c} ← {a}" for c, a in v] for k, v in sorted(self.row_aliases.items())}
        if self.convert_currency:
            syms = [fx_symbol(c) for c in (self.statement_currency, self.price_currency) if c and c != "USD"]
            out.update({"fx_symbols": syms,
                        "method": "balance al cierre de la fecha del período; resultados y flujos al promedio de "
                                  "los cierres diarios del período",
                        "rates": self.rates})
            q = self.rates.get("quarterly_income_stmt") or {}
            if q:
                last4 = sorted(q)[-4:]
                out["ttm_rate"] = sum(q[d] for d in last4) / len(last4)
            if self.fx is not None and len(self.fx.closes):
                # Fase 2b: último cierre del cruce (importe de los estados → moneda del precio), para convertir
                # importes sueltos de hoy (el dividendo de la línea local, T2).
                out["spot_rate"] = {"date": str(self.fx.closes.index[-1].date()),
                                    "rate": float(self.fx.closes.iloc[-1]) * self.subunit}
            for attr in ("quarterly_balance_sheet", "balance_sheet"):
                b = self.rates.get(attr) or {}
                if b:
                    d = max(b)
                    out["balance_rate"] = {"date": d, "rate": b[d]}
                    break
        return out


def ratio_ok(x: Optional[float]) -> bool:
    return x is not None and not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))
