# F15 · Las expectativas golden del evaluador, como prueba (6-nov-2026)

El evaluador externo convirtió sus tres revisiones en expectativas comprobables. Están en `finanzer_golden_110.yaml`
(copia en `informes-pdf/`):
- rangos aceptables de precio, confianza y arquetipo para las 110 empresas;
- 11 reglas globales;
- una muestra de control de 300 empresas contra el sobreajuste;
- una definición de «terminado».

El usuario aprobó adoptarlo y atacar las causas medidas: «Sí, adelante».

## Qué se adopta

- **`backend/tests/expectativas/golden_110.yaml`:** el archivo del evaluador. Solo cambia con la aprobación del usuario,
  y queda registrado en su cabecera. Tres empresas se re-anclaron al banco congelado: TXN, PLD y MOS. Su «actual ±1»
  venía de datos vivos del 6-nov, y con los datos congelados el motor previo a F15 daba otra etiqueta.
- **`backend/tests/expectativas.py`:**
  - comprueba cada empresa (precio, confianza, arquetipo y textos obligatorios);
  - comprueba las reglas globales que se pueden medir en un análisis: R1, R2, R3, R4, R6, R8, R10 y R11;
  - R5 la cubre `verdict.abstention`, R7 la cubre `test_damodaran_erp.py` y R9 la nota de la referencia (F14 · 11);
  - sale con error si una regla se incumple o si una empresa que cumplía deja de cumplir (`estado.json`);
  - lee el YAML con un lector propio, que da lo mismo que PyYAML en todo el archivo.
- **`backend/tests/muestra_control.py`:** 300 empresas fuera de las 110, con semilla 20261106 y estratificadas por
  sector GICS (`muestra_control.txt`). Se miden al cerrar cada versión y nunca se usan para ajustar.
- **`backend/tests/test_f15.py`:** el lector, las reglas, las tres correcciones y el banco (sin reglas incumplidas y sin
  regresiones).

## Causas medidas y corregidas

El evaluador atribuía los 12 «muy exigente» a un método solo. No es así: en las 12 coinciden al menos dos métodos.

1. **P/FCF con el flujo del DCF.** En expansión (F13 · paso 9), el DCF ya partía del flujo de mantenimiento, pero el
   P/FCF que puntúa seguía con el publicado. Ejemplos: MSFT 67x, GOOGL 176x, META 53x. Ahora es el «P/FCF de
   mantenimiento»; GOOGL queda en 29x.
2. **El máximo del DCF directo.** Restaba 4 puntos, lo mismo que todo el bloque de múltiplos, en cuanto el valor quedaba
   un 30 % por debajo del precio. Su sesgo de nivel es conocido: mediana de −40 %. Ahora el ±4 solo se aplica si ningún
   supuesto razonable de la tabla de sensibilidad alcanza el precio; si alguno lo alcanza, ±2.
3. **R11, regla del evaluador.** Ningún método solo lleva el precio a «muy exigente». Con menos de dos métodos que la
   vean cara, el precio crudo no baja de «exigente», y la nota lo dice. Afecta a DLR y EQIX.

No se aplicó una «causa 2» que yo había propuesto, el Forward P/E: sí puntúa (mide la compresión frente al P/E) y no
estaba mudo.

## Resultado

| | F14 (base) | F15 |
|---|---|---|
| Expectativas que cumplen (banco congelado del 5-nov) | 91 de 110 | **93 de 110** (85 %) |
| Reglas globales incumplidas en las 110 | 1 (DLR, R11) | **0** |
| «Muy exigente» en las 110 | 26 | 24 |
| Suite | 6722 | 6729 |

**Panel:** MSFT pasa de muy exigente a exigente, PG a «entre exigente y muy exigente», SNOW a exigente y UL a
razonable. AMZN pasa a muy exigente.

**Muestra de control con F14** (producción, base antes del push):
- 300 analizadas;
- «muy exigente»: 18 % (las 110: 24 %, −6 pp);
- confianza baja: 53 % (las 110: 61 %, −8 pp).

Las dos están dentro de los ±10 pp. Hay una regla incumplida: R8 en ECHO, coste de capital del 20 % con una cobertura
de 0,14x y rating D. Está justificado, pero la R8 solo exime la cobertura negativa. Tras el push se medirá la muestra
con F15.

## Para decidir el usuario (el archivo solo cambia con su aprobación)

- **AMZN** deja de cumplir. Antes no tenía P/FCF, porque su flujo publicado es negativo; ahora tiene el de
  mantenimiento, 48x, y queda en «muy exigente» por un punto (24 frente a 25). El propio evaluador escribe «flujo de
  mantenimiento ~2 % del precio», es decir, unas 50x.
- **DLR** deja de cumplir por aplicar la R11 del evaluador. Su «actual ±1» se fijó sobre un veredicto que incumplía esa
  misma regla.
- **KHC y T** piden confianza baja por el Altman. Eso choca con el ajuste del propio evaluador en F14: el EBIT
  normalizado, para no castigar deterioros sin caja. La R1 solo prohíbe la confianza alta.
- **R8:** eximir también una cobertura menor que 1, no solo la negativa (caso ECHO).
- **Las 11 «muy exigente» restantes** (V, PG, JNJ, ABBV, BLK, MMM, LIN, HD, GOOGL, NVDA, AMZN) son caras por todos los
  métodos: todos los múltiplos frente a su sector y un DCF en el que ningún supuesto alcanza el precio. Bajarlas sería
  ajustar el motor al criterio del revisor, que es lo que su muestra de control quiere evitar.
- **MRNA** sale MATURE y el evaluador lo prohíbe: sus ventas caen ~50 % anual y tiene pérdidas. La lista de tipos de
  empresa es cerrada, por decisión del usuario.
