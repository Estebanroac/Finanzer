# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-28T12:22:47. Backend: finanzer_next-perf/backend (mezcla v4). 20 usuarios durante 12.0 min (carga medida: 724.8 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 360 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.171 s (n = 1175) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | -21.5 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.204 s; tenencia máx. 7.166 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 1175 | 0 | 0 | 0.036 | 0.171 | 2.013 |
| analysis_cold | 10 | 0 | 0 | 2.196 | 3.011 | 3.011 |
| page | 1585 | 0 | 0 | 0.004 | 0.085 | 0.269 |
| pdf | 141 | 0 | 0 | 0.106 | 0.362 | 1.103 |
| peers | 1378 | 0 | 0 | 0.003 | 0.049 | 0.136 |
| prices | 1175 | 0 | 0 | 0.1 | 0.167 | 4.139 |
| scenario | 340 | 0 | 0 | 0.003 | 0.052 | 0.104 |
| search | 226 | 0 | 0 | 0.118 | 0.309 | 0.44 |
| segments | 1175 | 0 | 0 | 0.001 | 0.019 | 0.15 |
| sparklines | 410 | 0 | 0 | 0.005 | 0.05 | 3.171 |
| trending | 410 | 0 | 0 | 0.008 | 0.038 | 0.068 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.002 s; primer análisis de AAPL: 3.7 s.
- Primer análisis de cada empresa: AAPL 3.7 s (200), JPM 2.7 s (200), O 4.58 s (200), NEE 2.32 s (200), XOM 2.4 s (200), PLTR 1.92 s (200), RIVN 2.3 s (200), BCS 3.87 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 18.1, 'cards': 0, 'listo': 0}.
- Memoria: pico del calentamiento 310.5 MB; al empezar la carga 310.5 MB; pico de la carga 360.4 MB (picos por separado: RSS 360.4 MB, huella física 342.7 MB).

Turnos de análisis: 1334 de usuarios y 147 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 132 | 25.74 |
| data_fetcher._data_cache | 154 | 11.69 |
| price_history._cache | 64 | 3.31 |
| yf_adapter._stmt_cache | 336 | 2.86 |
| finnhub_fallback._cache | 96 | 2.35 |
| price_history._chart_cache | 16 | 1.98 |
| trending._state | 7 | 0.68 |
| sparklines._cache | 120 | 0.64 |
| segments._cache | 64 | 0.38 |
| analysis_queue._summaries | 64 | 0.31 |
| universe._state | 4 | 0.29 |
| peers._caps | 131 | 0.02 |
