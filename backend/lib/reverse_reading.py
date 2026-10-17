"""
DCF inverso en el motor (fase 3, T3; F3_DISENO §2 y §8; D3): "¿qué crecimiento exige el precio actual?".

Una lectura = crecimiento exigido (lib/reverse_dcf, la misma estructura que el DCF directo) + su CAGR equivalente a
10 años + tasas base (lib/base_rates, referencia principal) + historia propia (ingresos por acción a 5–10 años de
EDGAR, segunda referencia) -> banda (barata / en precio / exigente / muy exigente), señal para la convergencia y
puntos para Valoración, y la frase del informe (pasa por el guardián: claim "implied_growth").

  · Flujo: FCF − SBC por acción (§8.4) y el puente de la deuda neta (FCFF al WACC, como el directo).
  · CYCLICAL (§8.5): dos lecturas, con el FCF de mantenimiento de ciclo medio (la principal: "qué exige el precio
    en un año normal") y con el FCF − SBC del periodo ("si el nivel actual se mantiene").
  · REIT (§8.7): sobre el FFO por acción, flujo del accionista: al coste del capital propio y sin puente de deuda.
"""
from typing import Any, Dict, Optional

import base_rates as br
import cyclicality as cy
import reverse_dcf as rd
from settings import cfg

_IND_ES = {"Technology": "tecnología", "Healthcare": "salud", "Consumer": "consumo",
           "Manufacturing": "industria y energía", "Other": "otros sectores", "All": "todas las industrias"}


def _pct(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f}%".replace("-", "−")


def _bin_text(b: Optional[str]) -> str:
    if not b:
        return ""
    return "más de 100 mil millones" if b == "100+" else f"{b.replace('-', ' a ')} mil millones"


def own_growth(history: Optional[Dict[str, Any]], fallback_3y: Optional[float]) -> Dict[str, Any]:
    """Segunda referencia: ingresos por acción a 5–10 años de EDGAR; sin esa historia, el CAGR a 3 años de los
    estados (declarado)."""
    if history:
        r = cy.revenue_ps_cagr_long(history)
        if r["cagr"] is not None:
            return {"cagr": r["cagr"], "years": r["years"], "basis": r["basis"], "source": "EDGAR",
                    "label": "sus ingresos por acción" if r["basis"] == "por_accion" else "sus ingresos"}
    if fallback_3y is not None:
        return {"cagr": fallback_3y, "years": 3, "basis": "estados", "source": "estados (3 años)",
                "label": "sus ingresos"}
    return {"cagr": None, "years": None, "basis": None, "source": None, "label": None}


def reading(*, price: Optional[float], flow: Optional[float], shares: Optional[float], rate: Optional[float],
            net_debt: Optional[float], revenue_usd: Optional[float], sector: Optional[str],
            own: Dict[str, Any], flow_label: str) -> Dict[str, Any]:
    """Una lectura del DCF inverso con su banda."""
    T = cfg("valuation.reverse_dcf")
    tg = cfg("valuation.dcf.terminal_growth")
    fps = (flow / shares) if (flow is not None and shares) else None
    nds = ((net_debt or 0.0) / shares) if shares else 0.0
    r = rd.implied_growth(price, fps, rate, net_debt_per_share=nds)
    out = {"state": r["state"], "reason": r["reason"], "side": r["side"], "flow_label": flow_label,
           "flow_per_share": fps, "net_debt_per_share": nds, "rate": rate, "terminal_growth": tg,
           "g_star": r["g_star"], "g10": None, "base_rate": None, "own_growth": own, "band": None, "rule": None,
           "signal": None, "points": None, "text": None}
    if r["state"] == rd.OK:
        out["g10"] = rd.ten_year_cagr(r["g_star"])
    if r["state"] not in (rd.OK, rd.OUT_OF_RANGE):
        return out
    g_ref = out["g10"] if out["g10"] is not None else (T["growth_bounds"][1] if r["side"] == "superior"
                                                       else T["growth_bounds"][0])
    out["base_rate"] = br.share_sustaining(g_ref, revenue_usd, sector)
    rb = rd.read_against_base_rates(out["g10"], out["base_rate"]["share"], own.get("cagr"),
                                    out_of_range_side=r["side"])
    out.update(band=rb["band"], rule=rb["rule"], gap=rb["gap"],
               signal=T["band_signal"].get(rb["band"]), points=T["band_points"].get(rb["band"]))
    out["text"] = sentence(out)
    return out


def sentence(x: Dict[str, Any]) -> Optional[str]:
    """Frase obligatoria (§2.2), con las dos referencias."""
    fl = x["flow_label"]
    if x["state"] == rd.OUT_OF_RANGE:
        lo, hi = cfg("valuation.reverse_dcf.growth_bounds")
        return (f"El precio actual exige que el {fl} por acción crezca más de un {_pct(hi, 0)} anual: ningún "
                "crecimiento razonable lo reconcilia." if x["side"] == "superior" else
                f"El precio actual se justifica aun con el {fl} por acción cayendo más de un {_pct(-lo, 0)} anual.")
    if x["g10"] is None:
        return None
    path = f"({_pct(x['g_star'])} los 5 primeros y convergencia al {_pct(x['terminal_growth'])})"
    t = (f"El precio actual exige que el {fl} por acción crezca un {_pct(x['g10'])} anual durante 10 años {path}"
         if x["g10"] >= 0 else
         f"El precio actual se justifica aunque el {fl} por acción caiga un {_pct(-x['g10'])} anual durante 10 años "
         f"{path}")
    o = x["own_growth"] or {}
    if o.get("cagr") is not None:
        what = o.get("label") or "sus ingresos"
        pl = what.startswith("sus ")
        verb = (f"{'crecieron' if pl else 'creció'} un {_pct(o['cagr'])}" if o["cagr"] >= 0
                else f"{'cayeron' if pl else 'cayó'} un {_pct(-o['cagr'])}")
        t += f"; en los últimos {o['years']} años, {what} {verb} anual"
    t += "."
    b = x.get("base_rate") or {}
    if b.get("share") is not None:
        ind = (b.get("cell") or "").split(" · ")[-1]
        t += (f" Lo sostuvo 10 años el {_pct(b['share'], 0)} de las empresas comparables (ventas de "
              f"{_bin_text(b.get('bin'))}, {_IND_ES.get(ind, ind)}).")
    return t
