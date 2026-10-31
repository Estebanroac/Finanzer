"""
Lecturas que entienden el modelo de negocio (fase 3, T6; F3_DISENO §5).

  · **Capital circulante negativo estructural** (restauración, comercio, aerolíneas, software por suscripción y
    consumo básico con financiación de proveedores): un current ratio < 1 es normal en un negocio que cobra antes de
    pagar. No puntúa en Solidez ni alerta, salvo que empeore frente a su propia historia (el último ejercicio por
    debajo de la mediana de los anteriores en más de `worsening_rel`).
  · **Altman referencial**: en esas industrias el modelo (calibrado con manufactureras y su capital circulante
    positivo) no se diseñó para su estructura: se muestra como referencia y no vota.
  · **Piotroski**: modelo cerrado, sin cambio de método; el texto avisa de qué criterios informan poco en la industria
    (liquidez y margen bruto).
Industrias en config (sectors.business_model), normalizadas como el clasificador.
"""
from statistics import median
from typing import Any, Dict, List, Optional

from classify import norm_industry
from settings import cfg


def structural_negative_wc(industry: Optional[str]) -> bool:
    return norm_industry(industry) in cfg("sectors.business_model.negative_working_capital_industries")


def current_ratio_context(industry: Optional[str], st: Optional[Dict[str, Any]],
                          current_ratio: Optional[float]) -> Dict[str, Any]:
    """{structural, history: [CR de cada ejercicio], median_prior, worsening, applies} para la lectura, el score y
    la alerta. `applies`: el current ratio < 1 se lee como estructural (no puntúa ni alerta)."""
    st = st or {}
    ca, cl = st.get("current_assets") or [], st.get("current_liabilities") or []
    hist = [(a / b) if (a is not None and b) else None for a, b in zip(ca, cl)]
    prior = [x for x in hist[1:] if x is not None]
    med = median(prior) if prior else None
    structural = structural_negative_wc(industry)
    rel = cfg("sectors.business_model.worsening_rel")
    worsening = bool(current_ratio is not None and med is not None and current_ratio < med * (1.0 - rel))
    applies = bool(structural and current_ratio is not None and current_ratio < 1.0 and not worsening)
    return {"structural": structural, "history": hist, "median_prior": med, "worsening": worsening,
            "applies": applies, "industry": industry}


def altman_referential(industry: Optional[str]) -> bool:
    return norm_industry(industry) in cfg("sectors.business_model.altman_referential_industries")


ALTMAN_REF_INDUSTRY = ("Referencial: el modelo de Altman no se diseñó para esta industria (pasivos por arrendamiento y "
                      "circulante negativo estructurales); no puntúa")
ALTMAN_REF_CAPTIVE = ("El Z de Altman no es comparable en empresas que consolidan una financiera cautiva (su deuda de "
                      "financiación entra en el pasivo)")
CAPTIVE_UNVERIFIED = ("sin los segmentos del emisor no se puede comprobar si consolida una financiera cautiva, en cuyo caso "
                      "el Z no sería comparable")


def captive_finance(segs: Optional[Dict[str, Any]], edgar_captive: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """F8 · E10: ¿consolida el emisor una financiera cautiva? Una sola detección con las dos fuentes primarias:

      · la deuda de la cautiva que ya separa lib/debt.py en la instancia XBRL (US GAAP; CAT: Cat Financial);
      · los segmentos de negocio de su último informe anual (lib/segments.build; US GAAP e IFRS): uno de servicios
        financieros (`captive_finance_segment_patterns` en su nombre) con al menos `captive_finance_segment_min_pct`
        de los ingresos del último ejercicio.

    {detected: True | False | None (sin segmentos: no se sabe), source, segment, share, reason}. Nada de proxies por
    industria ni por nombre de empresa."""
    B = cfg("sectors.business_model")
    if (edgar_captive or {}).get("status") == "ok":
        return {"detected": True, "source": "deuda de la financiera cautiva en el XBRL del emisor (SEC EDGAR)",
                "segment": edgar_captive.get("name"), "share": None, "reason": None}
    if not segs or segs.get("status") != "ok":
        return {"detected": None, "source": None, "segment": None, "share": None,
                "reason": (segs or {}).get("reason") or "sin los segmentos del emisor"}
    axes = [{"axis": segs.get("axis"), "segments": segs.get("segments")}] + \
        ([segs["secondary"]] if segs.get("secondary") else []) + list(segs.get("others") or [])
    hits = [(s.get("label"), s.get("share_last")) for ax in axes if ax.get("axis") in B["captive_finance_segment_axes"]
            for s in ax.get("segments") or []
            if s.get("share_last") is not None and s["share_last"] >= B["captive_finance_segment_min_pct"]
            and any(p in str(s.get("label") or "").lower() for p in B["captive_finance_segment_patterns"])]
    if not hits:
        return {"detected": False, "source": "segmentos de negocio del último informe anual (SEC EDGAR)",
                "segment": None, "share": None, "reason": None}
    label, share = max(hits, key=lambda h: h[1])
    return {"detected": True, "source": "segmentos de negocio del último informe anual (SEC EDGAR)",
            "segment": label, "share": share, "reason": None}


def piotroski_caveat(cr_ctx: Optional[Dict[str, Any]], current_ratio: Optional[float]) -> Optional[str]:
    """F8 · P3: la nota del Piotroski sale solo si el dato de la empresa la justifica: current ratio < 1 en una industria
    de circulante negativo estructural y sin empeorar frente a su historia (`current_ratio_context.applies`). Antes
    dependía solo de la industria y salía también con current ratio 1,23 (MSFT) o 7,2 (PLTR)."""
    if not (cr_ctx or {}).get("applies") or current_ratio is None:
        return None
    return (f"Su current ratio es {current_ratio:.2f}x: por debajo de 1, como es propio del modelo de negocio de su "
            "industria (capital circulante negativo), así que el criterio de mejora de la liquidez informa poco en "
            "esta empresa.")


def cr_history_text(ctx: Dict[str, Any]) -> Optional[str]:
    h: List[Optional[float]] = [x for x in ctx.get("history") or [] if x is not None]
    if len(h) < 2 or ctx.get("median_prior") is None:
        return None
    return f"mediana de los {len(h) - 1} ejercicios anteriores {ctx['median_prior']:.2f}x"
