# V4 · Carga y memoria (generado por backend/tools/load_test.py)

Fecha: 2026-10-18T00:43:59. 20 usuarios durante 5.0 min (carga medida: 304.4 s), backend real en local con la web compilada y las fuentes reales. Claves presentes: FINNHUB_API_KEY sí, SEC_EDGAR_USER_AGENT sí.

## Criterios

| Criterio | Resultado | Valor | Límite |
|---|---|---|---|
| Ningún 5xx | ✅ | 0 | 0 |
| Pico de memoria (máx. de RSS y huella física) | ✅ | 433 MB | < 450 MB |
| p95 de /api/analysis en caché | ✅ | 0.459 s (n = 306) | < 2.0 s |
| Memoria estable (2.ª mitad) | ❌ | 96.8 MB | < 25.0 MB |
| La cola no retrasa a un usuario más que un análisis | ✅ | espera máx. de usuario 1.363 s; tenencia máx. 4.241 s | espera ≤ tenencia |

## Por tipo de petición

| Tipo | n | 5xx | 4xx | p50 (s) | p95 (s) | máx. (s) |
|---|---|---|---|---|---|---|
| analysis | 306 | 0 | 0 | 0.016 | 0.459 | 1.705 |
| analysis_cold | 10 | 0 | 0 | 1.696 | 3.433 | 3.433 |
| page | 412 | 0 | 0 | 0.002 | 0.042 | 0.141 |
| pdf | 41 | 0 | 0 | 0.086 | 0.256 | 1.864 |
| peers | 892 | 0 | 0 | 0.001 | 0.02 | 0.178 |
| prices | 306 | 0 | 0 | 0.067 | 0.172 | 2.796 |
| scenario | 88 | 0 | 0 | 0.001 | 0.022 | 0.059 |
| search | 59 | 0 | 0 | 0.106 | 0.289 | 0.338 |
| segments | 306 | 0 | 0 | 0.001 | 0.077 | 5.223 |
| trending | 106 | 0 | 0 | 0.001 | 0.003 | 0.062 |

## Arranque en frío y calentamiento

- Proceso nuevo → primera respuesta de la portada: 0.62 s; HTML de /v2/AAPL: 0.001 s; primer análisis de AAPL: 2.92 s.
- Primer análisis de cada empresa: AAPL 2.92 s (200), JPM 1.79 s (200), O 1.84 s (200), NEE 1.85 s (200), XOM 1.63 s (200), PLTR 1.81 s (200), RIVN 1.95 s (200), BCS 1.77 s (200).
- Precalentado de las tendencias (parte del calentamiento): {'status': 'listo', 's': 66.1, 'cards': 30, 'listo': 30}.
- Memoria: pico del calentamiento 351.6 MB; al empezar la carga 351.6 MB; pico de la carga 433.2 MB (picos por separado: RSS 381.6 MB, huella física 433.2 MB).

Turnos de análisis: 365 de usuarios y 80 de la cola de fondo (rivales y precalentado). Espera p95 de un usuario: 0.0 s.

**Resultado: hay criterios en rojo.**
