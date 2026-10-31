# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T03:53:07. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.4 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 362 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.421 s (n = 295) | < 2.0 s |
| Memoria estable (2.ª mitad) | ❌ | 66.4 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 1.477 s; tenencia máx. 3.057 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 295 | 0 | 0 | 0.015 | 0.421 | 1.656 |
| analysis_cold | 10 | 0 | 0 | 1.663 | 3.075 | 3.075 |
| page | 396 | 0 | 0 | 0.002 | 0.049 | 0.127 |
| pdf | 41 | 0 | 0 | 0.082 | 0.235 | 0.294 |
| peers | 908 | 0 | 0 | 0.001 | 0.02 | 0.104 |
| prices | 295 | 0 | 0 | 0.063 | 0.23 | 2.502 |
| scenario | 83 | 0 | 0 | 0.001 | 0.032 | 0.065 |
| search | 56 | 0 | 0 | 0.094 | 0.245 | 0.3 |
| segments | 295 | 0 | 0 | 0.001 | 0.029 | 3.431 |
| trending | 101 | 0 | 0 | 0.001 | 0.003 | 0.006 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 1.1 s; HTML de /v2/AAPL: 0.002 s; primer análisis de AAPL: 2.77 s.
- Primer análisis de cada empresa: AAPL 2.77 s (200), JPM 1.8 s (200), O 1.71 s (200), NEE 1.68 s (200), XOM 1.63 s (200), PLTR 1.78 s (200), RIVN 1.51 s (200), BCS 1.81 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 63.3, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 258.8 MB; al empezar la carga 239.5 MB; pico de la carga 362.2 MB (picos por separado: RSS 314.5 MB, huella física 362.2 MB).

Turnos de análisis: 354 de usuarios y 84 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 72 | 16.55 |
| data_fetcher._data_cache | 160 | 11.59 |
| price_history._cache | 64 | 3.29 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 0.74 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
