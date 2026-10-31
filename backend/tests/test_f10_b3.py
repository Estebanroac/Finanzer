"""F10 · B3 (escaneo del modelo general, `alertas_coherentes`): una sola referencia por métrica. La alerta del P/E, del
EV/EBITDA, del ROE y de los márgenes lee el resultado de su fila (lib/vs_reference.band con la referencia de la fila):
ninguna fortaleza con la fila en rojo, ningún aviso con la fila en verde."""
import glob
import json
import os
import sys

import pytest

import vs_reference
from settings import cfg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
from f10_b3_tono import contradictions  # noqa: E402


@pytest.mark.parametrize("env", ["panel", "local"])
def test_no_alert_contradicts_the_tone_of_its_row(env):
    bad = []
    for f in sorted(glob.glob(os.path.join(HERE, "golden", env, "*.json"))):
        with open(f, encoding="utf-8") as fh:
            bad += [(os.path.basename(f), *c) for c in contradictions(json.load(fh))]
    assert not bad, bad


def test_row_and_alert_share_the_bands():
    b = cfg("thresholds.pdf.vs_sector_bounds")
    assert vs_reference.band(1.0 + b[1] / 100, 1.0, True)[1] == "pos"
    assert vs_reference.band(1.0, 1.0, True)[1] == "neu"
    assert vs_reference.band(1.0 - b[0] / 100 - 0.01, 1.0, True)[1] == "neg"
    assert vs_reference.band(10.0, None, False) is None


def test_pgr_margin_reads_like_its_row():
    """PGR (panel): margen neto 12.8 % frente a 10.8 % de su industria: la fila dice «Superior» y la alerta ya no dice
    «estrecho» (el umbral de la tabla del sector)."""
    with open(os.path.join(HERE, "golden", "panel", "PGR.json"), encoding="utf-8") as fh:
        a = json.load(fh)
    reasons = [x["reason"] for k in ("strengths", "warnings", "red_flags") for x in a["alerts"][k]]
    assert not any("Margen neto estrecho" in r for r in reasons)
    assert any(r.startswith("Margen neto sólido") for r in reasons)
