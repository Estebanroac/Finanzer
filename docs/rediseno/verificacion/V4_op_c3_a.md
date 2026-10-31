# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T03:21:24. Backend: finanzer_next-e4/backend (mezcla v4). 20 usuarios durante 5.0 min (carga medida: 304.6 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 426 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.618 s (n = 292) | < 2.0 s |
| Memoria estable (2.ª mitad) | ✅ | 1.0 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 1.573 s; tenencia máx. 2.721 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 292 | 0 | 0 | 0.02 | 0.618 | 2.168 |
| analysis_cold | 10 | 0 | 0 | 1.703 | 1.965 | 1.965 |
| page | 393 | 0 | 0 | 0.003 | 0.039 | 0.144 |
| pdf | 41 | 0 | 0 | 0.099 | 0.297 | 1.355 |
| peers | 911 | 0 | 0 | 0.002 | 0.022 | 0.114 |
| prices | 292 | 0 | 0 | 0.065 | 0.229 | 1.064 |
| scenario | 84 | 0 | 0 | 0.002 | 0.025 | 0.085 |
| search | 56 | 0 | 0 | 0.123 | 0.27 | 0.294 |
| segments | 292 | 0 | 0 | 0.001 | 0.143 | 2.778 |
| trending | 101 | 0 | 0 | 0.002 | 0.005 | 0.03 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.002 s; primer análisis de AAPL: 2.65 s.
- Primer análisis de cada empresa: AAPL 2.65 s (200), JPM 1.53 s (200), O 1.45 s (200), NEE 1.59 s (200), XOM 1.47 s (200), PLTR 1.55 s (200), RIVN 1.5 s (200), BCS 1.87 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 60.1, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 290.0 MB; al empezar la carga 290.0 MB; pico de la carga 426.5 MB (picos por separado: RSS 426.5 MB, huella física 406.8 MB).

Turnos de análisis: 351 de usuarios y 84 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: todo en verde.**

## Cachés al final de la carga (huella en memoria, aproximada)

| Caché | Entradas | MB |
|---|---|---|
| sec_edgar._cache | 104 | 44.83 |
| data_fetcher._data_cache | 160 | 11.97 |
| price_history._cache | 64 | 3.29 |
| yf_adapter._stmt_cache | 336 | 2.8 |
| price_history._chart_cache | 15 | 1.86 |
| finnhub_fallback._cache | 96 | 0.83 |
| universe._state | 4 | 0.35 |
| analysis_queue._summaries | 64 | 0.27 |
| segments._cache | 8 | 0.05 |
| peers._caps | 131 | 0.02 |
| trending._state | 7 | 0.01 |
| yf_adapter._cache | 48 | 0.01 |
