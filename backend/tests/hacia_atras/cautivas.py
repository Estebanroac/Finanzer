"""
companyfacts de las financieras cautivas con 10-K propio (config data.edgar.captive_filers: Ford Credit, GM Financial,
Cat Financial…) en <f2b>: capture_f2b_sources solo guarda los del CIK del ticker y sus predecesores; el banco de F13
los añadió aparte. Correr con el modo «fecha de corte» (corte_run.py): el replay vuelve a cortar por `filed`.

    python tests/hacia_atras/corte_run.py tests/hacia_atras/cautivas.py <carpeta f2b>
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "lib"))
sys.path.insert(0, os.path.join(HERE, ".."))
import f2b_fixtures as ff  # noqa: E402
import sec_edgar as edgar  # noqa: E402
from settings import cfg  # noqa: E402


def main():
    base = sys.argv[1]
    for sym, spec in (cfg("data.edgar.captive_filers") or {}).items():
        cik = spec.get("cik") if hasattr(spec, "get") else None
        if not cik:
            print(f"{sym}: sin CIK en la config ({spec})")
            continue
        # Entero (no el reducido de ff.save_facts, que corta en FACTS_SINCE): la serie de la cautiva llega a 2009 y el
        # replay debe dar lo mismo que la corrida en vivo.
        body = edgar._get(edgar.FACTS_URL.format(cik=int(cik)), edgar.Budget(600.0))
        path = os.path.join(base, "edgar", "companyfacts", f"CIK{int(cik):010d}.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(body)
        print(f"{sym}: companyfacts de CIK {cik} guardado en {base}")


if __name__ == "__main__":
    main()
