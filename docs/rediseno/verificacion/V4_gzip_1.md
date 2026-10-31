# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T08:36:22. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.1 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 402 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.435 s (n = 282) | < 2.0 s |
| Memoria estable (2.ª mitad) | ❌ | 71.1 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 1.124 s; tenencia máx. 4.075 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 282 | 0 | 0 | 0.013 | 0.435 | 2.171 |
| analysis_cold | 10 | 0 | 0 | 1.757 | 4.089 | 4.089 |
| page | 380 | 0 | 0 | 0.001 | 0.029 | 0.111 |
| pdf | 39 | 0 | 0 | 0.071 | 0.351 | 1.315 |
| peers | 924 | 0 | 0 | 0.001 | 0.016 | 0.069 |
| prices | 282 | 0 | 0 | 0.059 | 0.133 | 1.299 |
| scenario | 83 | 0 | 0 | 0.001 | 0.017 | 0.048 |
| search | 56 | 0 | 0 | 0.139 | 0.263 | 0.299 |
| segments | 282 | 0 | 0 | 0.001 | 0.309 | 3.307 |
| trending | 98 | 0 | 0 | 0.001 | 0.002 | 0.043 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.83 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 3.0 s.
- Primer análisis de cada empresa: AAPL 3.0 s (200), JPM 1.78 s (200), O 1.84 s (200), NEE 1.8 s (200), XOM 1.96 s (200), PLTR 2.93 s (200), RIVN 1.85 s (200), BCS 2.88 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 69.3, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 270.5 MB; al empezar la carga 270.5 MB; pico de la carga 402.4 MB (picos por separado: RSS 334.6 MB, huella física 402.4 MB).

Turnos de análisis: 339 de usuarios y 86 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 102 | 26.65 |
| data_fetcher._data_cache | 160 | 11.56 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 1.06 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
