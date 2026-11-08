"""
F8 · E1 (auditoría externa del 26-oct-2026): prueba de sensibilidad del veredicto al coste del patrimonio.

Se repite la valoración con Ke − Δ y Ke + Δ (`valuation.capm.ke_sensitivity_pp`, 1 pp): el desplazamiento entra por
cost_of_capital.KE_SHIFT en el único Ke del análisis, así que lo recogen a la vez el WACC (DCF, DCF inverso, grid,
spread ROIC−WACC), el P/B justificado (FINANCIAL, UTILITY) y el DCF del REIT. Si el nivel de precio de alguna de las dos
repeticiones es otro, el veredicto es «dependiente de Ke»: la confianza baja un escalón y el precio mostrado se
recalcula con ella (la contracción hacia el neutro depende de la confianza). Un fallo de la prueba no bloquea: queda
sin dato con el motivo.
"""
import contextvars
from typing import Any, Callable, Dict

from cost_of_capital import KE_SHIFT
from settings import cfg
from valuation_confidence import LEVELS
from verdict import reprice, verdict as build_verdict


def _tested(pa: Dict[str, Any]) -> Dict[str, Any]:
    """El precio cuya dependencia de Ke se prueba. Con la regla L1 (F16), que no usa Ke, la lectura de valoración del
    motor (múltiplos y DCF): así la confianza, y con ella la contracción de esa lectura que dispara la alerta de
    valoración extrema, sigue la definición probada en la versión A (Fase 1 · pendientes, 7-nov-2026)."""
    pa = pa or {}
    return (pa.get("valuation_reading") or {}) if pa.get("rule") == "L1" else pa


def _level_with_shift(shift: float, rerun: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    def run():
        KE_SHIFT.set(shift)
        return rerun()
    alt = contextvars.copy_context().run(run)      # el desplazamiento no sale de la repetición
    pa = _tested(alt.get("price_attractiveness"))
    return {"level": pa.get("level"), "score": pa.get("score"), "ke": (alt.get("cost_of_equity") or {}).get("value")}


def apply(result: Dict[str, Any], rerun: Callable[[], Dict[str, Any]]) -> None:
    """Añade result["ke_sensitivity"] y, si el veredicto depende de Ke, baja la confianza un escalón."""
    C = cfg("valuation.capm")
    if not C["ke_sensitivity"]:
        return
    pa = result.get("price_attractiveness") or {}
    tp = _tested(pa)
    base = tp.get("level")
    d = C["ke_sensitivity_pp"]
    out: Dict[str, Any] = {"status": "ok", "pp": d, "base": {"level": base, "score": tp.get("score"),
                                                            "ke": (result.get("cost_of_equity") or {}).get("value")},
                           "minus": None, "plus": None, "dependent": False, "reason": None}
    result["ke_sensitivity"] = out
    if base is None:
        out.update(status="sin_dato", reason="sin nivel de precio")
        return
    try:
        out["minus"], out["plus"] = _level_with_shift(-d, rerun), _level_with_shift(d, rerun)
    except Exception as e:  # noqa: BLE001 — la prueba nunca bloquea el análisis
        out.update(status="sin_dato", reason=f"la repetición con otro Ke falló ({type(e).__name__})")
        return
    changed = [(k, out[k]["level"]) for k in ("minus", "plus") if out[k]["level"] not in (None, base)]
    if not changed:
        return
    pp = f"{d * 100:g} pp"
    out["dependent"] = True
    out["reason"] = ("veredicto dependiente de Ke: el nivel de precio pasa de «" + base + "» a " + " y a ".join(
        f"«{lvl}» con Ke {'−' if k == 'minus' else '+'} {pp}" for k, lvl in changed))
    conf = result.get("confidence")
    if not conf or conf.get("level") not in LEVELS:
        return
    old = conf["level"]
    new = LEVELS[min(LEVELS.index(old) + 1, len(LEVELS) - 1)]
    # F10 · N4: la contracción parte de su propia base (sin el escalón de las tasas base, que no contrae); la
    # dependencia de Ke sí contrae, así que baja las dos.
    b_old = conf.get("contraction_basis") or old
    b_new = LEVELS[min(LEVELS.index(b_old) + 1, len(LEVELS) - 1)]
    conf["ke_dependent"] = {"from": old, "to": new, "reason": out["reason"]}
    conf["reasons"] = list(conf.get("reasons") or []) + [
        out["reason"] + (f": confianza {old} → {new}" if new != old else ": la confianza ya era baja")]
    if new == old and b_new == b_old:
        return
    conf["level"], conf["contraction_basis"] = new, b_new
    result["price_attractiveness"] = reprice(pa, b_new)
    if result.get("quality") is not None:
        # Fase 1 · pendientes (decisión del usuario, 7-nov-2026): la confianza ya no contrae la calidad
        result["verdict"] = build_verdict(result["quality"], result["price_attractiveness"], conf)
