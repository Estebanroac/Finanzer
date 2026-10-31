"""
Genera frontend/src/lib/generated/backendConfig.ts desde backend/config/.

El frontend (export estático de Next.js) pinta el bloque `display` del JSON
(etapa 9b); solo necesita los vocabularios cerrados (arquetipos, rótulos de
estado), que este script vuelca desde el backend en lugar de copiarlos a mano:

    python3 backend/tools/gen_frontend_config.py          # escribe el .ts
    python3 backend/tools/gen_frontend_config.py --check  # 1 si está desincronizado

tests/test_frontend_config_sync.py falla si el .ts no coincide con la config.
Tras regenerar con valores distintos hay que reconstruir frontend/out (build.sh
no lo hace en Render).
"""
import json
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BACKEND, "lib"))
OUT = os.path.normpath(os.path.join(BACKEND, "..", "frontend", "src", "lib", "generated", "backendConfig.ts"))

from settings import cfg  # noqa: E402


def _q(v):
    return json.dumps(v, ensure_ascii=False)


def render() -> str:
    # Etapa 9b: la web pinta el bloque `display` (lib/display.py): lecturas, tonos,
    # medianas del benchmark y bandas llegan en el JSON. Aquí solo quedan los
    # vocabularios cerrados que el frontend necesita para tipar y rotular.
    na = cfg("sectors.archetypes.not_applicable")
    from display import STATE_LABELS  # noqa: E402
    q, p = cfg("thresholds.score.quality"), cfg("thresholds.score.price")
    cat, scale = cfg("thresholds.score.category"), cfg("thresholds.score.total.max")
    # Niveles de confianza del veredicto, del mejor al peor ([score.price] confidence_factor).
    conf_levels = sorted(p["confidence_factor"], key=lambda k: -p["confidence_factor"][k])
    score_bands = (
        "\n/** Bandas de las dos puntuaciones (thresholds.toml [score.quality] y [score.price]):\n"
        " *  `bands` de mayor a menor (≥), `labels` de la mejor a la peor; `confidence.labels`: niveles de\n"
        " *  confianza del veredicto del mejor al peor ([score.price] confidence_factor). Rediseño /v2.\n"
        " *  V7 (PM, el texto de los desgloses): `scale`, la escala de las dos ([score.total] max); `categories`, cuántas\n"
        " *  categorías suma la calidad; `category`, la base y el máximo de cada una ([score.category]); `neutral`, el\n"
        " *  punto hacia el que la confianza contrae el precio ([score.price] neutral). */\n"
        "export const SCORE_BANDS = {\n"
        f"  quality: {{ bands: {_q(q['bands'])}, labels: {_q(q['labels'])}, categories: {len(q['categories'])} }},\n"
        f"  price: {{ bands: {_q(p['bands'])}, labels: {_q(p['labels'])}, neutral: {p['neutral']} }},\n"
        f"  category: {{ base: {cat['base']}, max: {cat['max']} }},\n"
        f"  scale: {scale},\n"
        f"  confidence: {{ labels: {_q(conf_levels)} }},\n"
        "} as const;\n"
    )
    w = cfg("data.web")
    import names                                                  # noqa: E402
    nc = cfg("names.company")
    # El nombre corto de la empresa (P8, el del cintillo): las reglas de names.toml y, para comprobar que la copia de
    # la web dice lo mismo (src/v2/lib/companyName.test.ts), lo que da el backend con unos nombres de muestra.
    samples = sorted(set(nc["exceptions"]) | {
        "Apple Inc.", "Tesla, Inc.", "Microsoft Corporation", "Home Depot (The)", "NVIDIA Corporation",
        "Alphabet Inc. Class A", "TOYOTA MOTOR CORP/", "Deere & Company", "Foo, Holdings", "LVMH Moët Hennessy - Louis Vuitton, Société Européenne",
        "Unilever PLC", "Novo Nordisk A/S", "SAP SE", "Siemens AG", "Shell plc", "Berkshire Hathaway Inc.",
        "JPMorgan Chase & Co.", "Procter & Gamble Company (The)", "Taiwan Semiconductor Manufacturing Company Limited",
        "Inc.", "Realty Income Corporation"})
    company = (
        "\n/** P8 (el cintillo): el nombre corto de la empresa, sin forma jurídica (names.toml [company]; backend/lib/names.py\n"
        " *  company). `samples`: lo que devuelve el backend con unos nombres de muestra (src/v2/lib/companyName.test.ts). */\n"
        "export const COMPANY_NAMES = {\n"
        f"  suffixesCi: {_q(list(nc['suffixes_ci']))},\n"
        f"  suffixes: {_q(list(nc['suffixes']))},\n"
        f"  afterComma: {_q(list(nc['after_comma']))},\n"
        f"  edgarState: {_q(nc['edgar_state'])},\n"
        f"  exceptions: {_q(dict(nc['exceptions']))},\n"
        f"  samples: {_q({s: names.company(s) for s in samples})},\n"
        "} as const;\n"
    )
    web = (
        "\n/** La web /v2 (data.toml [web]). `analysisTimeoutMs`: cuánto espera la página al análisis antes de dar el\n"
        " *  error «tarda más de lo normal»; `loading`: el ritmo de la pantalla de carga (AnalyzeLoading). */\n"
        "export const WEB = {\n"
        f"  analysisTimeoutMs: {round(cfg('data.web.analysis_timeout_s') * 1000)},\n"
        f"  peersPollMaxMs: {w['peers_poll_max_s'] * 1000},\n"
        "  loading: {\n"
        f"    delayMs: {w['loading_delay_ms']}, expectedMs: {round(w['loading_expected_s'] * 1000)}, "
        f"fastMs: {w['loading_fast_ms']}, stallFill: {w['loading_stall_fill']},\n"
        f"    typicalS: {_q(list(w['loading_typical_s']))}, exitHoldMs: {w['loading_exit_hold_ms']}, "
        f"exitMs: {w['loading_exit_ms']},\n"
        f"    titles: {_q(list(w['loading_titles']))},\n"
        f"    labels: {_q(list(w['loading_labels']))},\n"
        f"    phrases: {_q(list(w['loading_phrases']))},\n"
        f"    stallTitle: {_q(w['loading_stall_title'])}, stallPhrase: {_q(w['loading_stall_phrase'])},\n"
        "  },\n"
        "  /** Umbrales de la prueba de rendimiento (e2e/perf, V4b · 3). */\n"
        f"  perf: {{ cpuThrottle: {w['perf_cpu_throttle']}, sectionChangeMs: {w['perf_section_change_ms']}, "
        f"inpP75Ms: {w['perf_inp_p75_ms']}, longTaskMs: {w['perf_long_task_ms']}, "
        f"scrollLongTaskMs: {w['perf_scroll_long_task_ms']} }},\n"
        "} as const;\n"
    )
    return f"""// GENERADO por backend/tools/gen_frontend_config.py desde backend/.
// NO EDITAR A MANO: cambia el backend y vuelve a ejecutar el generador.
// tests/test_frontend_config_sync.py falla si este archivo se desincroniza.

/** Arquetipos del clasificador único (sectors.toml [archetypes.not_applicable]). */
export type Archetype = {" | ".join(_q(a) for a in na)};

/** Rótulo de cada estado de una métrica (lib/display.py STATE_LABELS). */
export const STATE_LABELS = {{
{chr(10).join(f"  {k}: {_q(v)}," for k, v in STATE_LABELS.items())}
}} as const;
""" + score_bands + web + company


def main():
    content = render()
    current = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
    if "--check" in sys.argv:
        if current != content:
            print(f"DESINCRONIZADO: {OUT}\n  ejecuta: python3 backend/tools/gen_frontend_config.py")
            sys.exit(1)
        print("sincronizado")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"escrito {OUT}")


if __name__ == "__main__":
    main()
