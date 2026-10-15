"""
Fase 2a del plan de fiabilidad (T0): /api/health dice qué commit está desplegado. Render define RENDER_GIT_COMMIT en
el entorno del servicio; en local no existe y el commit es null. Hasta ahora no había forma de saber desde fuera qué
código servía producción (/build-stamp.json es el hash del contrato de la web, no del código).
"""
import asyncio

import main


def test_health_reports_the_deployed_commit(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "8ed57a0f00")
    assert asyncio.run(main.health()) == {"status": "ok", "commit": "8ed57a0f00"}


def test_health_commit_is_null_outside_render(monkeypatch):
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    assert asyncio.run(main.health()) == {"status": "ok", "commit": None}
