"""
Configuración única del motor (etapa 4).

Lee los TOML de backend/config/ (tomllib, librería estándar desde Python 3.11)
y los valida contra backend/config/schema.toml al importar el módulo. Si falta
una clave, sobra una clave o un tipo no cuadra, lanza SettingsError con TODOS
los problemas: no hay defaults silenciosos.

Esquema: el mismo árbol que la config, con el tipo como hoja:
    "int" | "float" | "str" | "bool"
    "list[int]" | "list[float]" | "list[str]" | "list[number]"
    "list[list[number]]"
Una tabla del esquema con la clave "*" acepta claves libres (p. ej. un sector
por clave) y valida cada valor contra el sub-esquema de "*".

"float" exige un float en el TOML (1.0 vale, 1 no) e "int" un entero: así el
tipo que ve el motor es exactamente el del literal original y la salida no
cambia ni en la serialización (4 frente a 4.0).

Uso:
    from settings import cfg
    T = cfg("valuation.dcf")          # dict
    g = cfg("valuation.dcf.default_growth")
"""
import os
import tomllib
from types import MappingProxyType
from typing import Any, Dict, List

CONFIG_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config"))
FILES = ("thresholds", "sectors", "valuation", "validation", "data", "market", "adr")


class SettingsError(RuntimeError):
    pass


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v):
    return _is_int(v) or isinstance(v, float)


_SCALARS = {
    "int": _is_int,
    "float": lambda v: isinstance(v, float),
    "str": lambda v: isinstance(v, str),
    "bool": lambda v: isinstance(v, bool),
    "number": _is_num,
}


def _check_leaf(path: str, typ: str, value: Any, errors: List[str]) -> None:
    if typ in _SCALARS:
        if not _SCALARS[typ](value):
            errors.append(f"{path}: se esperaba {typ}, hay {type(value).__name__} ({value!r})")
        return
    if typ.startswith("list[") and typ.endswith("]"):
        inner = typ[5:-1]
        if not isinstance(value, list):
            errors.append(f"{path}: se esperaba {typ}, hay {type(value).__name__}")
            return
        for i, item in enumerate(value):
            _check_leaf(f"{path}[{i}]", inner, item, errors)
        return
    errors.append(f"{path}: tipo desconocido en el esquema: {typ!r}")


def _check(path: str, schema: Any, value: Any, errors: List[str]) -> None:
    if isinstance(schema, str):
        _check_leaf(path, schema, value, errors)
        return
    if not isinstance(value, dict):
        errors.append(f"{path}: se esperaba una tabla, hay {type(value).__name__}")
        return
    if "*" in schema:
        for k, v in value.items():
            _check(f"{path}.{k}", schema["*"], v, errors)
        return
    for k in schema:
        if k not in value:
            errors.append(f"{path}.{k}: falta la clave")
        else:
            _check(f"{path}.{k}", schema[k], value[k], errors)
    for k in value:
        if k not in schema:
            errors.append(f"{path}.{k}: clave no declarada en schema.toml")


def _freeze(v):
    if isinstance(v, dict):
        return MappingProxyType({k: _freeze(x) for k, x in v.items()})
    if isinstance(v, list):
        return tuple(_freeze(x) for x in v)
    return v


def load(config_dir: str = CONFIG_DIR) -> Dict[str, Any]:
    """Carga y valida todos los TOML de `config_dir`. Lanza SettingsError."""
    errors: List[str] = []
    try:
        with open(os.path.join(config_dir, "schema.toml"), "rb") as fh:
            schema = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise SettingsError(f"no se pudo leer schema.toml en {config_dir}: {e}") from e
    data: Dict[str, Any] = {}
    for name in FILES:
        path = os.path.join(config_dir, f"{name}.toml")
        try:
            with open(path, "rb") as fh:
                data[name] = tomllib.load(fh)
        except (OSError, tomllib.TOMLDecodeError) as e:
            errors.append(f"{name}.toml: {e}")
    for name in FILES:
        if name not in schema:
            errors.append(f"schema.toml: falta la sección [{name}]")
        elif name in data:
            _check(name, schema[name], data[name], errors)
    for name in schema:
        if name not in FILES:
            errors.append(f"schema.toml: sección [{name}] sin archivo de config")
    if errors:
        raise SettingsError("configuración inválida:\n  - " + "\n  - ".join(errors))
    return _freeze(data)


SETTINGS = load()


def cfg(path: str) -> Any:
    """Valor de la config por ruta con puntos ("valuation.dcf.terminal_growth").
    Las listas se devuelven como tuplas y las tablas como mappings de solo
    lectura. Una ruta inexistente lanza SettingsError (no hay default)."""
    cur: Any = SETTINGS
    for part in path.split("."):
        try:
            cur = cur[part]
        except (KeyError, TypeError):
            raise SettingsError(f"clave de configuración inexistente: {path}") from None
    return cur
