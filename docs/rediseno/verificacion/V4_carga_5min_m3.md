# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T02:47:08. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.4 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 437 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.388 s (n = 268) | < 2.0 s |
| Memoria estable (2.ª mitad) | ❌ | 25.0 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.843 s; tenencia máx. 7.312 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 268 | 0 | 0 | 0.021 | 0.388 | 5.825 |
| analysis_cold | 10 | 0 | 0 | 1.612 | 2.01 | 2.01 |
| page | 359 | 0 | 0 | 0.003 | 0.033 | 0.115 |
| pdf | 37 | 0 | 0 | 0.097 | 0.274 | 1.298 |
| peers | 956 | 0 | 0 | 0.002 | 0.02 | 0.069 |
| prices | 268 | 0 | 0 | 0.062 | 0.109 | 1.707 |
| scenario | 78 | 0 | 0 | 0.003 | 0.03 | 0.049 |
| search | 53 | 0 | 0 | 0.102 | 0.228 | 0.279 |
| segments | 268 | 0 | 0 | 0.001 | 0.468 | 2.552 |
| trending | 91 | 0 | 0 | 0.002 | 0.003 | 0.014 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.63 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.51 s.
- Primer análisis de cada empresa: AAPL 2.51 s (200), JPM 1.65 s (200), O 1.45 s (200), NEE 1.37 s (200), XOM 1.53 s (200), PLTR 1.43 s (200), RIVN 1.5 s (200), BCS 2.11 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 60.1, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 353.5 MB; al empezar la carga 352.3 MB; pico de la carga 437.3 MB (picos por separado: RSS 401.9 MB, huella física 437.3 MB).

Turnos de análisis: 323 de usuarios y 79 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 102 | 42.78 |
| data_fetcher._data_cache | 160 | 11.43 |
| price_history._cache | 64 | 3.29 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 1.2 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
