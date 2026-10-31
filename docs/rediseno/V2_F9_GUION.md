# V2 con fuentes reales para la pasada oficial (tras F9): guion

Encargo del PM (2026-10-27): dejar preparada la V2 con fuentes reales para que en la pasada oficial sobre
`rediseno/v4-f8` (con F8 y F9 dentro) sea rápida. Incluye la comprobación de coherencia web ↔ PDF de las cifras de
portada, la que pide F9 · R3, «una sola verdad por cifra».

## Tickers (7)

| Ticker | Por qué |
|---|---|
| NU | El de la revisión externa: banco de mercado emergente con hipercrecimiento |
| ITUB | El otro banco de mercado emergente. Elegido frente a BBD: los dos responden con fuentes reales (comprobado el 27-oct, 200 en 5,5 s y 3,6 s, EDGAR disponible). Itaú es el mayor de los dos |
| VZ | Telecomunicaciones: mucha deuda y dividendo alto |
| PLD | REIT: P/FFO, sin escenario DCF |
| AMZN | Caja neta, FCF yield negativo y «reportado» frente a «normalizado» |
| MC.PA | París: EUR, sin SEC EDGAR |
| JPM | Banco de EE. UU.: el contraste con NU e ITUB |

ITUB y BBD no están en `config/universe.tsv`, pero el análisis acepta cualquier símbolo de Yahoo. ITUB, BBD y NU
salen «Banco», país «Brasil».

## Cómo se corre (≈ 15 min con la máquina libre)

Hace falta el build de la rama (`cd frontend && npm run build`). Las claves salen del Llavero solo en el entorno del
servidor: ningún informe las contiene.

```bash
cd backend
FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" \
SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" \
  ../../finanzer_next/.venv313/bin/python tools/load_server.py --port 8771 --no-prewarm &
T=NU,ITUB,VZ,PLD,AMZN,MC.PA,JPM

# 1. API: análisis, /v2/{T}, precios, segmentos, rivales hasta completar, escenario y PDF (3 a la vez)
../../finanzer_next/.venv313/bin/python tools/real_sources.py --base http://127.0.0.1:8771 --only $T --name V2_oficial

# 2. Páginas: la historia y las 9 secciones de cada uno (consola, errores de página, 5xx, «undefined/NaN»)
cd ../frontend && FR_BASE=http://127.0.0.1:8771 FR_SYMBOLS=$T npx playwright test -c playwright.fuentes.config.ts

# 3. Tablas (endpoints, tiempos y cada «sin dato» con su motivo)
cd ../backend && ../../finanzer_next/.venv313/bin/python tools/real_sources_report.py --api V2_oficial --out V2_oficial_tablas

# 4. Coherencia web ↔ PDF de la portada (sale con 1 si una cifra tiene dos valores)
cd ../frontend && node scripts/coherencia-portada.mjs http://127.0.0.1:8771 ../docs/rediseno/verificacion/V2_coherencia $T
cd ../backend && ../../finanzer_next/.venv313/bin/python tools/coherencia_portada.py \
  ../docs/rediseno/verificacion/V2_coherencia --out ../docs/rediseno/verificacion/V2_coherencia_portada.md

kill %1
```

Los PDF y los análisis que deja el paso 4 en `verificacion/V2_coherencia/` sirven para revisar a mano. Al cerrar
la pasada, se versiona solo el informe `.md`.

## Qué compara la coherencia de portada

- **Paso 1** (`frontend/scripts/coherencia-portada.mjs`):
  - lee lo que la web enseña de verdad en `/v2/{T}`, el DOM a 1440 px: precio, variación del día, conclusión, las
    tres puntuaciones y las cifras clave de «La empresa»;
  - guarda el análisis que pidió la propia página;
  - descarga el PDF del mismo servidor justo después.
- **Paso 2** (`backend/tools/coherencia_portada.py`; tests en `tests/test_coherencia_portada.py`):
  - **Cabecera:** cada pieza de la web tiene que estar tal cual en la portada del PDF (página 1, texto con pypdf como
    en las salidas guardadas).
  - **Cifras clave:** la web pinta `display.cover.kpis` y la portada del PDF `display.summary.cards`, dos listas del
    motor. Se emparejan por etiqueta y, si no casan, por la etiqueta sin «reportado», porque «P/E reportado (TTM)» y
    «P/E (TTM)» son la misma métrica. Con dos valores distintos es un **fallo (❌)**: es el caso de «P/B 5,34 frente
    a 4,55» de la revisión. La misma cifra con otra precisión, «5.34x» y «5.3x» o doble redondeo, es un **aviso
    (≈)**. Las que solo están en un lado se listan.
  - **PDF frente al análisis:** cada tarjeta del PDF dice en su texto lo que dice el análisis.

**Lo que no cubre:** la coherencia dentro de todo el informe, que es el test que hace F9 · R3 en la rama de
coherencia. Aquí solo se mira la portada: lo que el usuario ve primero en la web y en el PDF.

## Línea base en la v4 antes de F9 (27-oct)

Con fuentes reales, NU e ITUB: **0 fallos y 10 avisos**. Las cifras clave salen con 2 decimales en la web y con 1 en
el PDF (5.34x / 5.3x). Con el replay del panel (AAPL, JPM, MC.PA, PLD y AMZN): 0 fallos y 19 avisos.

Hay tres cosas para F9 · R3, que no son contradicciones:

- **La precisión:** la misma cifra con 2 decimales en la web y 1 en el PDF. Si «una sola verdad» incluye la
  presentación, el motor debería mandar el texto ya formateado y que las dos lo pinten igual.
- **Las etiquetas:** la web dice «ROE reportado», «Margen neto reportado» y «P/E reportado (TTM)» donde el PDF dice
  «ROE», «Margen neto» y «P/E (TTM)».
- **Las listas:** las cifras clave de la web y las de la portada del PDF son conjuntos distintos. La web lleva
  precio, capitalización y beta; el PDF lleva el crecimiento de 3 años y EV/EBITDA.
