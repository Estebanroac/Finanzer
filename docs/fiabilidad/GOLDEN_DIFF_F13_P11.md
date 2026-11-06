# F13 · Cierre: decisiones del usuario y pasos 11 y 12 (5-nov-2026)

El usuario decidió las tres cuestiones pendientes y pidió terminar F13 y publicarlo sin más consultas, solo esta vez.
Medida previa del paso 11: `F13_P11_CRECIMIENTO_MEDIDA.md`. Para el paso 11 se aplica la opción recomendada, la (c).

## Decisión 1 · Confianza de las cíclicas: opción (a) con matiz

Regla del usuario: si casi todas las candidatas caen por el umbral de estabilidad y las cercanas son industriales
razonables, se relaja solo ese umbral; si no, se vuelve a la (a) con matiz y la (b) queda medida.

Medida en las 60 cíclicas de las 543:

| Qué las deja fuera | Empresas |
|---|---|
| Productoras de materias primas | 23 |
| Sin una caída real del beneficio en la ventana | 4 |
| Años con pérdidas | **25 de las 33 restantes** |
| Solo el umbral de estabilidad | 8: DE (margen ±11,4 pp), SWKS, ARM (margen), ADI (−51 %), HON (−68 %, la escisión), NSC, EMR, y PCAR y ADM sin serie de margen |
| Pasan | 0 |

Casi todas caen por las pérdidas, no por el umbral. Por tanto, opción (a) con matiz (`valuation_confidence.cycle_evidence`):
- la cíclica sigue en «baja»;
- el motivo dice lo que el ciclo hizo en sus cifras de EDGAR, por ejemplo: «empresa cíclica: en sus 10 ejercicios,
  pérdidas en 2016; el beneficio cayó un 51% en 2020; margen operativo entre el 3.0% y el 20.2%» (CAT);
- las de materias primas, o las que aún no han tenido una caída real, lo dicen así.

La (b) queda documentada aquí; ningún umbral se relaja.

## Decisión 2 · Referencia acotada: 2 % fijo y prueba por causa entre el 2 % y el 3 %

`industry_bench._cause` (config `sectors.toml [benchmarks.industry]`). Entre el 2 % y el 3 %, la referencia sin la empresa:
- **es válida** en las industrias de margen fino por naturaleza: comercio, supermercados, distribución, distribución
  farmacéutica y agroindustria;
- **se acota** (pasa a la mediana de pares, con el motivo) si:
  - muchas empresas de la industria pierden dinero: la proporción de Damodaran (`pedata`, ahora en `industries.toml`)
    supera en 15 pp a la del mercado;
  - o el agregado queda por debajo de la mitad de la mediana de los pares;
- **es válida** en el resto de casos.

La regla de cordura pasa al 2 % y exige la prueba en la banda.

| Empresa | Referencia | Causa | Decisión |
|---|---|---|---|
| AMZN | Comercio general, margen neto 2,7 % | margen fino por naturaleza | válida |
| DE | Agricultura, 2,1 % | margen fino por naturaleza (agroindustria) | válida |
| UNH | Servicios de apoyo sanitario, margen operativo 2,4 % | margen fino por naturaleza (distribución farmacéutica) | válida |
| ECL, SHW | Química especializada, ROE 2,5 % / 2,1 % | mediana de los pares 2,6 %; pierde dinero el 59 % (mercado: 64 %) | válida (año bajo de la industria) |
| TSLA | Automóviles (global), 3,0 % | ni muchas pérdidas ni bajo la mediana | válida |
| HAL, PSX | Equipos petroleros, 2,2 % / 2,6 % | mediana de los pares 8,4 % / 8,8 % | **acotada** |
| MOS | Química especializada, 2,5 % | mediana de los pares 6,7 % | **acotada** |
| DIS, NFLX | Entretenimiento | ya era la mediana de pares (salto, paso 5) | — |

Ningún veredicto cambia. La regla `referencia_acotada` pasa de 11 a 0.

## Decisión 3 · SRE y Oncor: las participadas son negocio operativo

**Verificado.** Los 1,08 B$ que la normalización quitaba a SRE son su resultado de participadas neto de impuestos (1,80 B$
nombrados), del que Oncor (80 %) es el grueso.

El motor ya contaba como operativo el resultado de participadas presentado antes de impuestos (KO, XOM, NEE). Solo lo
quitaba cuando venía después de impuestos. Regla general: el resultado de una participada por el método de participación
es operativo; una inversión financiera, no.
- **Normalización** (`normalize.after_tax`): es operativo su nivel recurrente, la mediana de los 3 últimos ejercicios.
  El pico por encima se sigue quitando. FIS, con 2,39 B$ por vender su parte de Worldpay y sin participadas antes, sigue
  recortado.
  - SRE: 1,60 B$ operativos y nada recortado.
  - ALB: 0,49 B$ (Windfield).
- **Cobertura del rating** (`cost_of_capital.rating_coverage`): EBIT + participadas, si pesan al menos el 5 % del EBIT.
  SRE pasa de 2,2 a 3,3 veces, y su WACC del 6,7 % al 6,1 %.
- **EV/EBITDA:** el EV resta el valor contable de las participadas (Yahoo: Long Term Equity Investment) si pesan al menos
  el 5 % del EV.
  - SRE: 14,9 → 12,0 veces (Oncor pesa el 20 % del EV).
  - También PSX, MOS, KMI, GM, F, ALB, APD, PLD y SPG.
- **Efecto:**
  - SRE: exigente → razonable;
  - PLD y SPG: exigente → razonable (sus participadas inmobiliarias en el EV).

## Paso 11 · Opción (c): convergencia a la tasa base y divergencia ventas/BPA

- **Crecimiento** (`main.py`, `base_rates.median_growth`): el de la fase 1 del DCF es la media de su crecimiento y la
  mediana a 5 años del CAGR de ventas de sus comparables de tamaño e industria (Mauboussin y Callahan). Es lo mismo que
  converger en línea recta en 5 años. No se aplica a las cíclicas. El texto del DCF lo dice.
- **Fiabilidad del DCF**, criterio (6): si las ventas y el BPA a 3 años se separan más de 10 pp, un escalón menos.

Efecto en las 110 (paso 10 + decisiones → paso 11): cambian 27 empresas, 5 bandas hacia cara y 3 hacia barata.

| Hacia cara | Hacia barata |
|---|---|
| META, MSFT, NVDA, LLY: exigente → muy exigente | GOOGL: muy exigente → exigente |
| CRM: atractivo → razonable | UPS, VZ: exigente → razonable |

En el panel:
- NVO: DCF de +83 % a +46 %; sigue «atractivo (media)» por sus múltiplos.
- MSFT, TSM y NFLX: un escalón hacia caro.
- MC.PA y UL: el DCF sube; sin cambio de banda.

La mediana del DCF de las 76 pasa de −36 % a −40 %: el sesgo hacia «caro» no lo explica el crecimiento (la medida previa).

## Paso 12 · Base inflada

`historical_metrics.growth_rate`, el caso simétrico de la base deprimida: si el año inicial supera 1,5 veces la mediana de
los demás de la ventana, se usa la regresión log-lineal, con la serie larga de EDGAR si hace falta. La tasa de punta a
punta queda como cota inferior, y nunca se usa una menor que ella.
- PFE: FCF (287 % de la mediana; el «−29,6 % anual» queda como cota) y BPA, por regresión sobre FY2020–FY2025.
- MRNA: ingresos (595 %).
- ABBV, PSA: BPA.
- TXN, MMM: FCF.

Cambian TXN (precio 35 → 42) y UPS (confianza), sin cambio de banda. La regla `base_inflada` baja de 24 a 3:
- ya no aplica a las cíclicas: su pico es el ciclo;
- CCI y PLD son REIT y puntúan por FFO;
- la base de MRK solo es alta frente a toda su historia, no dentro de la ventana.

## Balance F13 en las 110 congeladas (inicio → final)

- Cambian 56 veredictos: 12 bandas hacia barata y 5 hacia cara.
- Confianza alta: 13 → 7.
- Las 11 «no se sostiene»:

| Empresa | Al empezar | Al final |
|---|---|---|
| ORCL | media · atractivo (alta) | media · razonable (baja) |
| META | excelente · muy exigente (media) | excelente · muy exigente (baja) |
| WBD | débil · exigente (baja) | débil · sin veredicto |
| EA | sólida · exigente (baja) | sólida · sin veredicto |
| GM | débil · exigente (baja) | media · atractivo (media) |
| KHC | media · razonable (baja) | media · atractivo (media) |
| XEL | débil · muy exigente (alta) | media · exigente (baja) |
| NEM | excelente · atractivo (alta) | sólida · exigente (baja) |
| HON, WELL, APD | — | mismo veredicto (HON: escisión en el perímetro; WELL y APD: WACC corregido en el paso 2) |

Tablas: `archivo-historico/evidencias-de-pruebas/f13_banco110_2026-11-05/paso12_vs_paso10.md` y `paso12_vs_antes.md`.

## Golden y web

- **Golden:** se regeneran los del panel, los locales, los forzados y el PDF v2. Todos los análisis llevan los campos
  nuevos: `dcf_growth_base_rate`, `ev_cross_holdings`, la evidencia del ciclo y la causa de la referencia.
- **Web:** se recompila con Turbopack y lleva la página Riesgos del paso 10.
  - En el worktree, la raíz de Turbopack se apunta a la carpeta Finanzer con un cambio temporal de `next.config.ts` que
    no se sube: el node_modules enlazado queda fuera de su raíz.
  - Con webpack, el HTML cita rutas codificadas (`%5B%5B...symbol%5D%5D`) y el guardián de `build.sh` las da por
    ausentes. Por eso el primer push (489d420f) no llegó a desplegarse, y producción siguió con la versión anterior.
  - Comprobado en el replay local: NEE muestra «Riesgos del sector (no puntúan)» con huracanes, todos los recursos
    responden 200 y la consola no da errores.

- **Ajustes de presentación, en origen:**
  - Con el DCF de fiabilidad baja, la lectura del valor intrínseco ya no cita la tabla de sensibilidad: el DCF no
    puntúa y la frase lo dice. Además, alargaba la página 2 del PDF de NFLX por debajo de la escala mínima (0,85).
  - Los motivos nuevos tienen su traducción llana (`plain_language`), y el de la divergencia entre ventas y BPA queda
    registrado para el guardián.
  - Ninguna cifra en inglés en la prosa: la tasa base dice «de tamaño e industria», no la celda «25-50 · Technology».
- **Ejemplos de los tests:**
  - PLD vuelve a «confianza alta». Ahora es una coincidencia real: su EV/EBITDA, sin las participadas, está en línea con
    su industria, como el inverso; no es el doble conteo del paso 3.
  - V local: su DCF converge del 10,9 % al 7,2 % y deja de depender de ±1 pp de Ke.
  - El caso de convergencia media pasa de UL a NFLX y a DUK.
  - AAPL: margen de seguridad −206 % → −196 %.

Tests: `tests/test_f13_paso11.py` (13). Suite: 6698 passed, 19 skipped. Web: tipos y 173 tests en verde.
