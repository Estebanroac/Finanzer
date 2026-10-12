"""lib/settings.py: carga y validación estricta de backend/config/*.toml."""
import os
import shutil

import pytest

import settings


@pytest.fixture
def cfgdir(tmp_path):
    """Copia de la config real en un directorio temporal, para corromperla."""
    d = tmp_path / "config"
    shutil.copytree(settings.CONFIG_DIR, d)
    return d


def _replace(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} no está en {path.name}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_real_config_loads():
    data = settings.load()
    assert set(data) == set(settings.FILES)


def test_missing_key_fails(cfgdir):
    _replace(cfgdir / "data.toml", "max_retries = 4", "")
    with pytest.raises(settings.SettingsError, match=r"data\.fetcher\.max_retries: falta la clave"):
        settings.load(str(cfgdir))


def test_undeclared_key_fails(cfgdir):
    _replace(cfgdir / "data.toml", "max_retries = 4", "max_retries = 4\nmax_retrys = 5")
    with pytest.raises(settings.SettingsError, match=r"max_retrys: clave no declarada"):
        settings.load(str(cfgdir))


def test_int_where_float_expected_fails(cfgdir):
    _replace(cfgdir / "validation.toml", "margin_max = 1.0", "margin_max = 1")
    with pytest.raises(settings.SettingsError, match=r"margin_max: se esperaba float, hay int"):
        settings.load(str(cfgdir))


def test_float_where_int_expected_fails(cfgdir):
    _replace(cfgdir / "data.toml", "max_retries = 4", "max_retries = 4.0")
    with pytest.raises(settings.SettingsError, match=r"max_retries: se esperaba int, hay float"):
        settings.load(str(cfgdir))


def test_string_where_number_expected_fails(cfgdir):
    _replace(cfgdir / "data.toml", "\ntimeout_s = 8", '\ntimeout_s = "8"')
    with pytest.raises(settings.SettingsError, match=r"finnhub\.timeout_s: se esperaba int, hay str"):
        settings.load(str(cfgdir))


def test_wrong_list_item_type_fails(cfgdir):
    _replace(cfgdir / "data.toml", 'gap_fields = ["beta"', 'gap_fields = [1')
    with pytest.raises(settings.SettingsError, match=r"gap_fields\[0\]: se esperaba str"):
        settings.load(str(cfgdir))


def test_missing_file_fails(cfgdir):
    os.remove(cfgdir / "valuation.toml")
    with pytest.raises(settings.SettingsError, match=r"valuation\.toml"):
        settings.load(str(cfgdir))


def test_malformed_toml_fails(cfgdir):
    (cfgdir / "data.toml").write_text("[fetcher\nmax_retries = 4\n", encoding="utf-8")
    with pytest.raises(settings.SettingsError, match=r"data\.toml"):
        settings.load(str(cfgdir))


def test_all_errors_reported_together(cfgdir):
    _replace(cfgdir / "data.toml", "max_retries = 4", "")
    _replace(cfgdir / "validation.toml", "margin_max = 1.0", "margin_max = 1")
    with pytest.raises(settings.SettingsError) as ei:
        settings.load(str(cfgdir))
    assert "max_retries" in str(ei.value) and "margin_max" in str(ei.value)


def test_cfg_unknown_path_has_no_default():
    with pytest.raises(settings.SettingsError, match="inexistente"):
        settings.cfg("data.fetcher.no_existe")


def test_config_is_read_only():
    with pytest.raises(TypeError):
        settings.cfg("data.fetcher")["max_retries"] = 99
