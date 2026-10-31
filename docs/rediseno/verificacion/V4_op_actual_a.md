# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T03:15:04. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 303.6 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 419 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.401 s (n = 298) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 18.7 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 0.714 s; tenencia máx. 3.45 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 298 | 0 | 0 | 0.019 | 0.401 | 1.855 |
| analysis_cold | 10 | 0 | 0 | 1.61 | 1.989 | 1.989 |
| page | 403 | 0 | 0 | 0.002 | 0.051 | 0.111 |
| pdf | 41 | 0 | 0 | 0.092 | 0.303 | 0.506 |
| peers | 901 | 0 | 0 | 0.002 | 0.013 | 0.075 |
| prices | 298 | 0 | 0 | 0.061 | 0.117 | 1.336 |
| scenario | 85 | 0 | 0 | 0.002 | 0.032 | 0.058 |
| search | 57 | 0 | 0 | 0.081 | 0.3 | 0.479 |
| segments | 298 | 0 | 0 | 0.001 | 0.021 | 2.694 |
| trending | 105 | 0 | 0 | 0.001 | 0.002 | 0.004 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.67 s.
- Primer análisis de cada empresa: AAPL 2.67 s (200), JPM 1.77 s (200), O 1.41 s (200), NEE 1.72 s (200), XOM 1.46 s (200), PLTR 1.6 s (200), RIVN 1.64 s (200), BCS 2.21 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 57.1, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 337.2 MB; al empezar la carga 337.2 MB; pico de la carga 419.2 MB (picos por separado: RSS 392.2 MB, huella física 419.2 MB).

Turnos de análisis: 357 de usuarios y 84 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 104 | 44.37 |
| data_fetcher._data_cache | 160 | 11.97 |
| price_history._cache | 64 | 3.29 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 1.16 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
