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
    return f"""// GENERADO por backend/tools/gen_frontend_config.py desde backend/.
// NO EDITAR A MANO: cambia el backend y vuelve a ejecutar el generador.
// tests/test_frontend_config_sync.py falla si este archivo se desincroniza.

/** Arquetipos del clasificador único (sectors.toml [archetypes.not_applicable]). */
export type Archetype = {" | ".join(_q(a) for a in na)};

/** Rótulo de cada estado de una métrica (lib/display.py STATE_LABELS). */
export const STATE_LABELS = {{
{chr(10).join(f"  {k}: {_q(v)}," for k, v in STATE_LABELS.items())}
}} as const;
"""


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
