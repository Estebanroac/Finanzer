"""
Verificación de la v4 (V4 · carga y memoria): cachés por símbolo con tope. Varias cachés de proceso guardaban una
entrada por símbolo para siempre (la caducidad solo decide si se usa, no la borra): con el keepalive el proceso vive
días y el precalentado de tendencias, los rivales y las búsquedas suman empresas distintas cada día, así que la memoria
crecía sin límite (Render: 512 MB). `put` escribe y, por encima del tope, saca la escrita hace más tiempo.
"""
from typing import Any, Dict, Hashable


def put(cache: Dict[Hashable, Any], key: Hashable, value: Any, cap: int) -> None:
    """cache[key] = value con como mucho `cap` entradas (las de escritura más antigua salen primero). Con el lock del
    llamador tomado si la caché es compartida entre hilos."""
    cache.pop(key, None)
    cache[key] = value
    while len(cache) > cap:
        cache.pop(next(iter(cache)))
