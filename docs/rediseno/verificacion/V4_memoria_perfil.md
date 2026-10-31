# Perfil de memoria por pieza (backend/tools/memory_profile.py, 2026-10-18T01:56:57)

Cada fila: servidor nuevo, huella en reposo (base), solo esa pieza, pico. Medida: máx(RSS, huella física).

| Pieza | Base (MB) | Pico (MB) | Aporta (MB) | Duración (s) |
|---|---|---|---|---|
| Un análisis en frío (AAPL) | 116.8 | 152.1 | **35.3** | 6.8 |
| 4 análisis en frío a la vez (AAPL, JPM, XOM, BCS) | 117.1 | 201.6 | **84.5** | 6.7 |
| Gráfica: serie de 5 años, mercado, sector y eventos (8 empresas, sin análisis) | 116.1 | 145.9 | **29.8** | 9.7 |
| Segmentos XBRL (8 empresas) | 117.3 | 160.1 | **42.8** | 6.2 |
| Tendencias: descarga del universo, sin precalentado | 116.2 | 149.7 | **33.5** | 16.0 |
| Tendencias con su precalentado (30 análisis en la cola de fondo) | 117.3 | 346.2 | **228.9** | 69.1 |
| Rivales de AAPL: su análisis y 5 rivales en la cola | 117.1 | 232.9 | **115.8** | 60.5 |
| PDF actual (/api/pdf) de 2 empresas, una tras otra | 116.6 | 226.3 | **109.7** | 10.3 |
| PDF nuevo (/api/v2/pdf) de 2 empresas, una tras otra | 116.8 | 248.6 | **131.8** | 14.4 |
| PDF nuevo de 4 empresas a la vez | 117.0 | 312.2 | **195.2** | 10.2 |
