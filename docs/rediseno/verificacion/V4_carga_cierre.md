# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-27T21:55:11. Backend: finanzer_next-v4f8/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 307.6 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 409 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.126 s (n = 203) | < 2.0 s |
| Memoria estable (2.ª mitad) | ❌ | 42.6 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.099 s; tenencia máx. 9.025 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 203 | 0 | 0 | 0.043 | 0.126 | 3.488 |
| analysis_cold | 10 | 0 | 0 | 4.354 | 5.851 | 5.851 |
| page | 270 | 0 | 0 | 0.005 | 0.038 | 0.186 |
| pdf | 30 | 0 | 0 | 0.106 | 0.204 | 0.287 |
| peers | 1030 | 0 | 0 | 0.004 | 0.039 | 0.086 |
| prices | 203 | 0 | 0 | 0.1 | 0.67 | 5.557 |
| scenario | 67 | 0 | 0 | 0.004 | 0.042 | 0.062 |
| search | 42 | 0 | 0 | 0.145 | 0.386 | 1.203 |
| segments | 203 | 0 | 0 | 0.001 | 0.027 | 0.461 |
| sparklines | 67 | 0 | 0 | 0.006 | 1.406 | 2.753 |
| trending | 67 | 0 | 0 | 0.014 | 0.022 | 0.065 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.41 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 6.65 s.
- Primer análisis de cada empresa: AAPL 6.65 s (200), JPM 5.65 s (200), O 4.99 s (200), NEE 7.97 s (200), XOM 4.49 s (200), PLTR 3.7 s (200), RIVN 4.16 s (200), BCS 9.04 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 24.1, 'cards': 0, 'listo': 0}.
- Memoria: pico del calentamiento 328.9 MB; al empezar la carga 328.9 MB; pico de la carga 408.7 MB (picos por separado: RSS 408.7 MB, huella física 374.0 MB).

Turnos de análisis: 251 de usuarios y 37 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 120 | 28.78 |
| data_fetcher._data_cache | 82 | 6.19 |
| price_history._cache | 52 | 2.62 |
| finnhub_fallback._cache | 96 | 2.6 |
| yf_adapter._stmt_cache | 243 | 2.0 |
| price_history._chart_cache | 16 | 1.98 |
| sparklines._cache | 120 | 0.72 |
| trending._state | 7 | 0.68 |
| universe._state | 4 | 0.29 |
| segments._cache | 41 | 0.23 |
| analysis_queue._summaries | 31 | 0.15 |
| peers._caps | 131 | 0.02 |
