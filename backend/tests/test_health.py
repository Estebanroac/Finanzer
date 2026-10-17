"""
Fase 2a del plan de fiabilidad (T0): /api/health dice qué commit está desplegado. Render define RENDER_GIT_COMMIT en
el entorno del servicio; en local no existe y el commit es null. Hasta ahora no había forma de saber desde fuera qué
código servía producción (/build-stamp.json es el hash del contrato de la web, no del código).
"""
import asyncio

import main


def test_health_reports_the_deployed_commit(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "8ed57a0f00")
    h = asyncio.run(main.health())
    assert (h["status"], h["commit"]) == ("ok", "8ed57a0f00")


def test_health_commit_is_null_outside_render(monkeypatch):
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    h = asyncio.run(main.health())
    assert (h["status"], h["commit"]) == ("ok", None)


def test_health_reports_edgar_env_without_the_value(monkeypatch):
    """Fase 7: /api/health dice si EDGAR está activo y por qué no, sin el valor de la variable."""
    name = main.cfg("data.edgar.user_agent_env")
    monkeypatch.delenv(name, raising=False)
    assert asyncio.run(main.health())["edgar"] == {"enabled": False, "present": False, "has_contact": False,
                                                   "near_miss": False}
    monkeypatch.setenv(name, "Nombre sin correo")
    monkeypatch.setenv(name + " ", "x")
    h = asyncio.run(main.health())["edgar"]
    assert h == {"enabled": False, "present": True, "has_contact": False, "near_miss": True}
    monkeypatch.setenv(name, "Nombre nombre@example.com")
    h = asyncio.run(main.health())
    assert h["edgar"]["enabled"] and h["edgar"]["has_contact"]
    assert "example.com" not in str(h)
