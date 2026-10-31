# V4b · 4 — Colores y presentación de las ausencias

Literal del usuario (2026-10-18): *«Muchos cuadros sin colores o bien indicados»*. El PM amplió el bloque con la
presentación de lo que falta: la auditoría de E4 (`V4b_datos_faltantes.md`) dejó el motivo de cada ausencia en el
motor, y la web tenía que pintarlo en su sitio.

## Cómo se mide

- **Ausencias:** el escáner de E4, `frontend/scripts/auditoria-faltantes.mjs`. Recorre las 9 secciones de los
  37 tickers del panel, con el build servido por el replay, y anota cada «—», «Sin dato», celda vacía o bloque de motivo.
- **Clasificación:** cada marca se clasifica con las reglas de E4 (`backend/tools/auditoria_faltantes.py`).
  `backend/tools/auditoria_presentacion.py` cuenta las de **presentación**: el motor tiene el motivo y la página no lo
  pinta. La web cumple cuando no queda ninguna. Si queda alguna, sale con 1.

  ```bash
  cd frontend && npm run build    # y el replay del panel en marcha
  BASE=http://localhost:8768 node scripts/auditoria-faltantes.mjs /tmp/recuento.json
  cd ../backend && ../.venv313/bin/python tools/auditoria_presentacion.py /tmp/recuento.json --ejemplos 3
  ```

- **Colores:** `frontend/e2e/v2/colores.spec.ts` recorre las 9 secciones de AAPL, JPM, PLTR, O y BCS y falla si encuentra:
  - una pastilla sin tono;
  - una cifra junto a su lectura sin tono;
  - una fila de tabla técnica con cifra y la lectura vacía;
  - una tarjeta con lectura y la cifra sin tono.

## Resultado

| | Antes (tras fusionar `rediseno/v4b-datos`) | Después |
|---|---|---|
| Marcas del escáner (37 tickers × 9 secciones) | 3.099 | 798 |
| **Marcas de presentación** | **2.264** | **0** |
| Clase (b): sin motivo en el motor | 0 | 0 |
| Colores: casos en los 5 tickers | ROE y ROA en Calidad sin color, tarjetas de la conclusión | 0 |

Las 798 que quedan llevan su motivo visible:

- **459 de clase (a):** el dato no existe o no aplica, y la página dice por qué. Las principales:
  - 327 «no aplica a este tipo de empresa»;
  - 84 «la fuente no lo publica»;
  - 38 «no significativo».
- **161 de clase (c):** rivales sin fixtures en el replay. En vivo, el backend analiza el rival.
- **178 que no son ausencias:** bloques informativos, el rótulo «Sin dato:» delante de su motivo y la celda «Quitar» de la propia empresa.

Recuentos completos: `V4b_ausencias/recuento-{antes,despues}.json.gz`.

## Las reglas del PM, una a una

| Regla | Cómo queda | Prueba |
|---|---|---|
| 1. Tablas sin referencia de industria | Una sección del motor de 3 columnas es una tabla de 3 columnas. En las de 5, las filas sin referencia van aparte, en una tabla de 3 columnas, con una nota que las nombra («Sin referencia de industria publicada para: …»). Métrica y Empresa caen en el mismo sitio en las dos formas. Ningún «—» por celda. | `depth.test.tsx`, `depth.spec.ts` (tablas apiladas) |
| 2. Márgenes sin CAGR | «no se compone» (márgenes) o «sin CAGR» (SBC), en gris, en lugar de la celda vacía | escáner |
| 3. Ajustes «No aplica» del desglose | «No aplica» y «No puntúa», con el motivo del motor. Nunca «Sin dato». | escáner |
| 4. Cifras de relleno | La fila lleva las cifras que hay (como mucho 3), en una rejilla simétrica para N. Sin «—» ni «Sin dato» de relleno. | `story.test.ts` |
| 5. ROIC − WACC, ROCE, escalas de solidez, conclusión, cifras clave y ficha del ejercicio | El estado del motor («No aplica», «Sin dato», «n. s.») y su motivo. En las cifras clave, el motivo va en una nota bajo la fila, para no descuadrarla. | escáner, `symmetry.spec.ts` |
| 6. Sensibilidad | Columnas del informe sin ninguna cifra: no se pintan. Escenario del usuario: cada celda sin valor dice por qué («≤ 0» o «fuera», del motor: `sensitivity.why`), con su explicación en la nota. | `test_scenario.py`, `colores.spec.ts` |
| 7. CAGR con base ≤ 0 | «n. s.» con «primer o último ejercicio ≤ 0» | escáner |
| Colores | Toda cifra con lectura lleva su tono y su pastilla. Sin lectura, una pastilla gris lo dice («Sin referencia», «Informativa»). | `colores.spec.ts` |

## Pruebas

- **e2e v2:** los 4 proyectos (escritorio, tableta, móvil y móvil WebKit).
- **Rendimiento:** `npm run e2e:perf`, 3 de 3 dentro de los umbrales del bloque 3.
- **Vitest:** 133 pruebas.
- **Backend:** 5.572 pruebas.
- **`npm run check`:** el contrato encaja con 46 salidas.

Pase completo e2e v2 final: 792 pasan y 1 falla. La que falla es la rotación de frases de la pantalla de carga, en
tableta. El bloque no toca esa pantalla, y la prueba pasa 12 de 12 sola (`--repeat-each=3`): es de tiempo, bajo la carga
del pase completo. Se vigila en la pasada final.
