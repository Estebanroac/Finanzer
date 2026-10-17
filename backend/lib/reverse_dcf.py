"""
DCF inverso (preparación de la fase 3; F3_DISENO_METODO §2, decisión D3).

Responde "¿qué crecimiento exige el precio actual?": resuelve el crecimiento anual g* del FCF por acción con el que el
valor del DCF iguala el precio.

Conectado al motor en la fase 3 (T3, main.py): lectura con las tasas base (lib/base_rates) como referencia principal
y el crecimiento propio de los ingresos por acción como segunda (F3_DISENO §8.1).

Misma estructura que el DCF directo (financial_ratios.dcf_multi_stage con decay_type="step"):
  · años 1..(fade_start − 1): crecimiento g*;
  · años fade_start..years: convergencia LINEAL de g* al terminal (el año `years` crece ya al terminal);
  · valor terminal de Gordon sobre el FCF del año `years` × (1 + g terminal), descontado al año `years`;
  · puente al equity: valor de la empresa por acción − deuda neta por acción (como el DCF-FCFF del motor).
Con los valores de config (5 + 5 años) la convergencia ocupa los años 6–10, como pide §2.2.

Ningún número inventado: cada caso que no tiene respuesta devuelve un estado explícito con su motivo
(`no_aplica`, `fuera_de_rango`, `sin_convergencia`). Los parámetros viven en config/valuation.toml [reverse_dcf].
"""
from typing import Any, Dict, List, Optional, Sequence

from settings import cfg

OK, NOT_APPLICABLE, OUT_OF_RANGE, NO_CONVERGENCE = "ok", "no_aplica", "fuera_de_rango", "sin_convergencia"
CHEAP, IN_PRICE, DEMANDING, VERY_DEMANDING = "barata", "en_precio", "exigente", "muy_exigente"
NO_CONTRAST, NO_DATA = "sin_contraste", "sin_dato"


def _defaults(terminal_growth, years, fade_start, bounds):
    dcf = cfg("valuation.dcf")
    if terminal_growth is None:
        terminal_growth = dcf["terminal_growth"]
    if years is None:
        years = dcf["high_growth_years"] + dcf["transition_years"]
    if fade_start is None:
        fade_start = dcf["high_growth_years"] + 1
    if bounds is None:
        bounds = cfg("valuation.reverse_dcf.growth_bounds")
    return terminal_growth, years, fade_start, tuple(bounds)


def growth_path(g: float, terminal_growth: float, years: int, fade_start: int) -> List[float]:
    """Crecimiento de cada año 1..years: g hasta fade_start − 1 y luego lineal hasta el terminal en el año `years`."""
    fade_years = years - fade_start + 1
    return [g if year < fade_start else g - (g - terminal_growth) * (year - fade_start + 1) / fade_years
            for year in range(1, years + 1)]


def equity_value_per_share(g: float, fcf_per_share_base: float, wacc: float, terminal_growth: float, years: int,
                           fade_start: int, net_debt_per_share: float = 0.0) -> float:
    """Valor del equity por acción con crecimiento g (etapa explícita + terminal de Gordon − deuda neta)."""
    pv, fcf = 0.0, fcf_per_share_base
    for year, gy in enumerate(growth_path(g, terminal_growth, years, fade_start), start=1):
        fcf *= 1 + gy
        pv += fcf / (1 + wacc) ** year
    terminal_value = fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    return pv + terminal_value / (1 + wacc) ** years - net_debt_per_share


def _result(state, reason, assumptions, **kw) -> Dict[str, Any]:
    out = {"state": state, "reason": reason, "side": None, "g_star": None, "iterations": 0,
           "reconstructed_value": None, "relative_error": None, "growth_path": None, "assumptions": assumptions}
    out.update(kw)
    return out


def implied_growth(price: Optional[float], fcf_per_share_base: Optional[float], wacc: Optional[float],
                   terminal_growth: Optional[float] = None, years: Optional[int] = None,
                   fade_start: Optional[int] = None, bounds: Optional[Sequence[float]] = None,
                   net_debt_per_share: float = 0.0) -> Dict[str, Any]:
    """Crecimiento anual g* del FCF por acción que hace que el valor del DCF iguale el precio (bisección).

    Devuelve un dict con `state` (ok | no_aplica | fuera_de_rango | sin_convergencia), `reason`, `side`
    (inferior | superior si queda fuera de rango), `g_star`, `iterations`, `reconstructed_value` (el valor del DCF
    con g*, que iguala el precio dentro de la tolerancia), `relative_error`, `growth_path` y `assumptions`.
    """
    T = cfg("valuation.reverse_dcf")
    terminal_growth, years, fade_start, bounds = _defaults(terminal_growth, years, fade_start, bounds)
    lo, hi = bounds
    if not 1 <= fade_start <= years + 1 or not lo < hi:
        raise ValueError(f"estructura inválida: years={years}, fade_start={fade_start}, bounds={bounds}")
    assumptions = {"price": price, "fcf_per_share_base": fcf_per_share_base, "net_debt_per_share": net_debt_per_share,
                   "wacc": wacc, "terminal_growth": terminal_growth, "years": years, "fade_start": fade_start,
                   "bounds": [lo, hi]}

    if price is None or price <= 0:
        return _result(NOT_APPLICABLE, "sin precio positivo con el que comparar", assumptions)
    if fcf_per_share_base is None or fcf_per_share_base <= 0:
        return _result(NOT_APPLICABLE, "sin flujo positivo que proyectar (FCF por acción base ≤ 0 o sin dato)",
                       assumptions)
    if wacc is None or wacc <= terminal_growth:
        return _result(NOT_APPLICABLE, "WACC sin dato o ≤ crecimiento terminal: el valor terminal no está definido",
                       assumptions)

    def gap(g):
        return equity_value_per_share(g, fcf_per_share_base, wacc, terminal_growth, years, fade_start,
                                      net_debt_per_share) - price

    # La bisección exige que el valor crezca con g en todo el rango: se comprueba en una malla.
    n = T["monotonicity_points"]
    mesh = [gap(lo + (hi - lo) * i / (n - 1)) for i in range(n)]
    if any(b <= a for a, b in zip(mesh, mesh[1:])):
        return _result(NO_CONVERGENCE, "el valor del DCF no crece con g en todo el rango: la bisección no es válida",
                       assumptions)

    tol = T["value_tolerance"] * price

    def solved(g, iterations):
        value = gap(g) + price
        return _result(OK, None, assumptions, g_star=g, iterations=iterations, reconstructed_value=value,
                       relative_error=abs(value - price) / price,
                       growth_path=growth_path(g, terminal_growth, years, fade_start))

    f_lo, f_hi = mesh[0], mesh[-1]
    if abs(f_lo) <= tol:
        return solved(lo, 0)
    if abs(f_hi) <= tol:
        return solved(hi, 0)
    if f_lo > 0:
        return _result(OUT_OF_RANGE, f"el precio exige un crecimiento del FCF por acción menor que {lo:+.0%} anual",
                       assumptions, side="inferior")
    if f_hi < 0:
        return _result(OUT_OF_RANGE, f"el precio exige un crecimiento del FCF por acción mayor que {hi:+.0%} anual: "
                                     "no es reconciliable con un crecimiento razonable", assumptions, side="superior")

    iterations = 0
    while hi - lo > T["growth_tolerance"] and iterations < T["max_iterations"]:
        iterations += 1
        mid = (lo + hi) / 2
        if gap(mid) < 0:
            lo = mid
        else:
            hi = mid
    out = solved((lo + hi) / 2, iterations)
    if out["relative_error"] > T["value_tolerance"]:
        return _result(NO_CONVERGENCE, f"sin convergencia en {iterations} iteraciones", assumptions,
                       iterations=iterations)
    return out


def classify_implied_growth(g_star: Optional[float], achieved_growth: Optional[float],
                            band_pp: Optional[float] = None, base_rate: Optional[float] = None) -> Dict[str, Any]:
    """Lectura del crecimiento exigido frente al logrado (bandas de F3_DISENO §2.2), sin texto de informe.

    `base_rate`: proporción de comparables que sostuvieron g* 10 años (la aporta la fase 3). Si está por debajo del
    umbral de config, `muy_exigente` (la visión externa manda sobre la comparación con la propia historia).
    """
    T = cfg("valuation.reverse_dcf")
    band = T["band_pp"] if band_pp is None else band_pp
    out = {"band": None, "gap": None, "band_pp": band, "achieved_growth": achieved_growth, "base_rate": base_rate,
           "base_rate_threshold": T["very_demanding_base_rate"]}
    if g_star is None:
        return dict(out, band=NO_DATA)
    if base_rate is not None and base_rate < T["very_demanding_base_rate"]:
        out["band"] = VERY_DEMANDING
        if achieved_growth is not None:
            out["gap"] = g_star - achieved_growth
        return out
    if achieved_growth is None:
        return dict(out, band=NO_CONTRAST)
    out["gap"] = g_star - achieved_growth
    out["band"] = CHEAP if out["gap"] < -band else DEMANDING if out["gap"] > band else IN_PRICE
    return out


def ten_year_cagr(g: float, terminal_growth: Optional[float] = None, years: Optional[int] = None,
                  fade_start: Optional[int] = None) -> float:
    """CAGR equivalente de la trayectoria de g* (g* los años 1..fade_start − 1 y convergencia al terminal): lo que
    se compara con las tasas base a 10 años."""
    terminal_growth, years, fade_start, _b = _defaults(terminal_growth, years, fade_start, None)
    f = 1.0
    for gy in growth_path(g, terminal_growth, years, fade_start):
        f *= 1.0 + gy
    return f ** (1.0 / years) - 1.0


def read_against_base_rates(g10: Optional[float], base_share: Optional[float], own_growth: Optional[float],
                            out_of_range_side: Optional[str] = None) -> Dict[str, Any]:
    """Lectura del crecimiento exigido (F3_DISENO §2.2 con los ajustes de §8.1 y §8.3).

    1. Tasas base (referencia principal): si menos de `very_demanding_base_rate` de los comparables sostuvo g10 diez
       años, muy exigente; si menos de `demanding_base_rate`, exigente. "Exige más de +60%" (fuera de rango
       superior) es muy exigente; "menos de −20%", barata.
    2. Historia propia (segunda referencia, ingresos por acción a 5–10 años): solo cuando las tasas base no lo
       consideran excepcional; ±`band_pp` frente a lo logrado: barata / en precio / exigente.
    3. Sin historia propia: barata si al menos `cheap_base_rate` de los comparables lo sostuvo; si no, en precio."""
    T = cfg("valuation.reverse_dcf")
    out = {"band": None, "rule": None, "gap": None, "base_share": base_share, "own_growth": own_growth,
           "band_pp": T["band_pp"]}
    if out_of_range_side == "superior":
        return dict(out, band=VERY_DEMANDING, rule="fuera_de_rango_superior")
    if out_of_range_side == "inferior":
        return dict(out, band=CHEAP, rule="fuera_de_rango_inferior")
    if g10 is None:
        return dict(out, band=NO_DATA, rule="sin_crecimiento_exigido")
    if own_growth is not None:
        out["gap"] = g10 - own_growth
    if base_share is not None and base_share < T["very_demanding_base_rate"]:
        return dict(out, band=VERY_DEMANDING, rule="tasa_base")
    if base_share is not None and base_share < T["demanding_base_rate"]:
        return dict(out, band=DEMANDING, rule="tasa_base")
    if own_growth is not None:
        band = (CHEAP if out["gap"] < -T["band_pp"] else DEMANDING if out["gap"] > T["band_pp"] else IN_PRICE)
        return dict(out, band=band, rule="historia_propia")
    if base_share is None:
        return dict(out, band=NO_CONTRAST, rule="sin_referencias")
    return dict(out, band=CHEAP if base_share >= T["cheap_base_rate"] else IN_PRICE, rule="tasa_base")
