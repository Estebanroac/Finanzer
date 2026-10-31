# F9 · Coherencia (revisión externa del informe de NU, 27-oct-2026) — Registro

Rama `fiabilidad/f9-coherencia` (worktree `../finanzer_next-f8p3`), desde `rediseno/v4-f8` en 21d76d63, tras la fusión
de P3. Revisión: `docs/fiabilidad/revision-nu-2026-10-27.md` (en main, 77edb5a0). Plan:
`docs/superpowers/plans/2026-10-27-fiabilidad-revision-nu.md`. Aquí van R3 y R6 (independientes); R1, R1b, R2, R4,
R5 y R7 son de E2a (`fiabilidad/f9-motor`).

Evidencia: NU en vivo (27-oct-2026) antes y después, con el código de esta rama; los 43 golden y las 4 muestras
forzadas. Los efectos que se miden aquí son los aislados de esta rama sobre 21d76d63; el combinado con el Ke de NU de
E2a (R1, R1b) se verá en la fusión.

---

## R3 · Una sola verdad por cifra (web y PDF)

### Los seis casos de la revisión, con su causa

| Caso (NU) | Causa | Arreglo en origen |
|---|---|---|
| P/B 5,34x (portada y resumen) frente a 4,55x (tabla) | **Dos periodos.** El modelo del banco (`archetype_metrics`) dividía la capitalización entre el patrimonio del FY2025 (11,3 B$); la tabla, entre el del balance del corte (13,25 B$, 30-jun-2026), que es la base del informe | El P/B del modelo es el de la tabla (`key_metrics.pb`, balance del corte, con su fecha en `pb_basis`). El P/TBV, con el tangible del mismo balance: fila «Tangible Book Value» del trimestre del corte (`ttm.ORDINARY_BALANCE_ROWS`, `ordinary.tangible_common`, sin AT1). Sin balance del corte, el del ejercicio, declarado. Igual en la utility (P/B frente a ROE) |
| CAGR 52,3 % frente a 48,8 % | **Dos fuentes y dos fórmulas.** Puntuaban los ingresos de Yahoo (2,97 → 10,63 B$); la historia, los de EDGAR (4,79 → 15,77 B$). Y el motor usa la regresión log-lineal con año base anómalo mientras el gráfico calculaba el CAGR de punta a punta (52,9 %) | Opción A (decisión del PM, regla M5): EDGAR es la serie FY única (abajo). El gráfico histórico usa la regla del motor (`historical_metrics.growth_rate`) y, con base anómala, la lectura, la alerta y la tabla anual dicen «por regresión log-lineal: el año inicial es anómalo» |
| Crecimiento del último ejercicio 28,5 % frente a 37,0 % | **Dos fuentes** (Yahoo y EDGAR), como el anterior | La misma serie FY: 37,0 % en las dos |
| TTM 13,17 B$ «del ejercicio» frente al FY 15,77 B$ | **Dos periodos sin etiqueta.** El cuadro «Cifras del ejercicio» mostraba el TTM | El título dice su periodo (`display.period_basis`): «Cifras de los últimos doce meses (TTM, a 30 de junio de 2026)» o «del ejercicio cerrado el … (FY)». La escalera de márgenes lo dice en la web («(TTM)») y en el PDF |
| Industria «Bancos regionales» frente a «Grandes bancos de mercados emergentes» | **Dos clasificaciones.** La cabecera usa la industria del perfil (Yahoo); la referencia, la de Damodaran por símbolo | Una sola etiqueta: la del perfil en todo el informe. La referencia dice el cruce: «Damodaran clasifica a la empresa en esa industria (símbolo), no en la de su perfil («Bancos regionales», la de la cabecera)» (`industry_bench.profile_differs`) |
| EV/EBITDA «No aplica» con 69,37x de industria | La columna de la industria no se vaciaba | `display._row`: con «No aplica», también la industria queda «—» |

### Opción A: EDGAR, la serie FY única (decisión del PM)

`edgar_primary._apply_fy_series`, regla general (config `data.edgar.fy_series_fields = ["revenue", "net_income"]`):

- Los ingresos y el beneficio neto de cada ejercicio de los estados salen de la **misma serie de EDGAR que la historia
  de 10 años** (`sec_edgar.annual_history`), convertidos como los de la fuente (`edgar_backup._convert`: el promedio
  del ejercicio), si EDGAR tiene **todos** los ejercicios de los estados. Si le falta alguno, la fuente entera, nunca
  una serie con dos definiciones, y `data_provenance.edgar.primary.series` dice por qué.
- **Conciliación:** cada ejercicio en que la fuente y EDGAR difieren más de `fy_series_reconcile_rel` (2 %) queda en
  `data_provenance.edgar.primary.reconciliation` (NU: −28 % a −38 %; XOM: −2,5 % a −3,6 %). No se muestra como alerta.
- **Una definición por serie:** si la serie de EDGAR usa dos conceptos en la ventana, manda la fuente. Y
  `annual_history` elige ya el concepto como `sec_edgar.candidates`: primero el que llega al ejercicio más reciente; los
  demás solo completan los ejercicios que le faltan. HSBC: el beneficio atribuible hasta 2022 y, desde 2023, solo
  `ProfitLoss`; por prioridad, la serie mezclaba los dos.
- **Bancos IFRS:** «ingresos» no tiene concepto estándar. Con el de la NIIF 15 (`RevenueFromContractsWithCustomers`,
  solo comisiones: BCS 11,1 B£ frente a unos ingresos totales tres veces mayores) EDGAR no da los ingresos del banco:
  la serie se queda con la fuente y la historia de 10 años lo dice como «sin dato» con el motivo
  (`edgar_primary.bank_history`). NU (`Revenue`, ingresos brutos) y HSBC (`RevenueAndOperatingIncome`) sí. Definición
  enviada a E2a para su R4 (que saca de la puntuación el margen neto sobre ingresos de bancos y aseguradoras).
- Las reglas de definición que ya existían (ingresos netos de un banco de EE. UU., ingresos sin ganancias de una
  aseguradora) mandan sobre esta.
- El TTM del corte no cambia: en un 20-F EDGAR no tiene trimestres (NU: TTM de Yahoo, 13,17 B$, otra definición que el
  FY de EDGAR; la diferencia FY queda registrada).

### Crecimiento en la moneda de los estados (decisión del PM)

El motor ya medía el crecimiento sin el tipo de cambio (`growth_currency`). Faltaba el resto del informe:
- el gráfico histórico calculaba el interanual y el CAGR sobre los importes en USD (TM: 7,0 % frente al 10,9 % en JPY).
  Ahora los calcula sobre la serie en la moneda de los estados (`growth_currency.yearly`) y lo dice: «Crecimientos en
  JPY, la moneda de los estados, sin el efecto del tipo de cambio; importes en USD»;
- la lectura del crecimiento lo dice donde está la cifra: «(FY2023–FY2026, en JPY, moneda de sus estados)».

Los niveles en USD salen todos de la misma conversión (lib/currency: promedio de cada ejercicio para los flujos), que
declara la portada; la historia de 10 años va en la moneda de los estados, rotulada.

### Repaso de E2b (portada web ↔ PDF)

- **Una precisión por cifra:** las tarjetas del resumen (las de la portada del PDF nuevo) usan la de las cifras clave y
  las tablas (`fv`, dos decimales; antes un decimal: 5,3x en el PDF y 5,34x en la web). También la referencia de
  industria («vs industria 17.78%») y la Regla de 40 de la cifra clave («-29» pasa a «-28.81%», como la tarjeta).
- **Una etiqueta por métrica:** la tarjeta de una cifra clave lleva la etiqueta de la cifra clave («ROE reportado»,
  «P/E reportado (TTM)» con el beneficio normalizado; antes «ROE» en el PDF).
- El comprobador de portada de E2b (`scripts/coherencia-portada.mjs`, rediseno/v4) y este test se complementan: el
  suyo compara la portada web con la del PDF; este, cada cifra del informe entero.

### Test de coherencia (`tests/coherence.py`, `tests/test_coherencia_f9.py`), en la suite

- **Display (web y base de los dos PDF):** cada cifra mostrada como (métrica, unidad, periodo, valor, redondeo):
  filas, tarjetas, KPI y puntos con clave (periodo del corte); historia de 10 años y gráfico histórico (por ejercicio);
  CAGR del gráfico con su ventana frente al crecimiento a 3 años; cuadro de cifras y escalera (corte). Falla si una
  métrica del mismo periodo aparece con dos valores más allá del redondeo con que se muestra. Los ingresos por acción
  (con emisión de acciones) son otra métrica que los agregados.
- **PDF (los dos):** en la portada y el resumen, la cifra pegada a cada rótulo es la del display.
- **Tarjetas y cifras clave:** la misma etiqueta y el mismo texto de la cifra.
- Pasa en los 43 golden y las 4 muestras forzadas, y en NU en vivo (antes: 16 contradicciones en el display y 2 en el
  PDF; ahora 0 y 0). Antes del arreglo, en los golden: P/B de los 6 bancos y aseguradoras, CAGR de 5, crecimientos en
  otra moneda de 5 y series EDGAR frente a Yahoo de 5.

### NU en vivo (efecto aislado sobre 21d76d63)

| | Antes | Después |
|---|---|---|
| P/B (portada = tabla) | 5,33x y 4,54x | 4,54x |
| P/TBV | 5,85x (FY) | 4,99x (balance del 30-jun) |
| Crecimiento de ingresos a 3 años | 52,3 % (Yahoo, log-lineal) | 48,2 % (EDGAR, log-lineal, declarado) |
| Último ejercicio | 28,5 % (Yahoo) frente a 37,0 % (historia) | 37,0 % en los dos |
| Atractivo del precio | 45 · razonable | 50 · razonable |
| Veredicto | Calidad sólida · precio razonable | igual |

---

## R6 · Riesgo de crédito en bancos

**Evidencia (se reproduce):** el informe de NU no tenía ninguna métrica de crédito, concluía «0 riesgos» y llamaba
«Capitalización 16 %» al patrimonio sobre activos.

**Qué publican gratis los emisores** (companyfacts de la SEC, totales sin dimensiones, comprobado en vivo):

| Banco | Coste del riesgo | Provisión / cartera | Morosidad 90 días / no devengo | Castigos netos |
|---|---|---|---|---|
| JPM (US GAAP) | sí | sí | no etiquetado sin dimensiones | sí |
| BAC (US GAAP) | sí | sí | sí / sí | sí |
| BCS (IFRS) | deterioro de activos financieros | sin concepto estándar | no | no |
| HSBC (IFRS) | deterioro de préstamos | sin concepto estándar | no | no |
| NU (IFRS, 20-F) | **nada vigente**: su crédito va en extensiones propias, que la SEC no publica | | | |

**Arreglo:**
- `lib/credit_risk.py`, del último informe anual (conceptos en `sec_edgar.CREDIT`, que entran en `_WANTED`):
  - coste del riesgo = gasto por pérdidas de crédito del ejercicio ÷ cartera media (la del cierre si no hay la
    anterior, y se dice); el texto nombra lo que cubre el concepto (cartera de préstamos, o todos los activos
    financieros en BCS);
  - provisión ÷ cartera bruta; morosidad a 90 días y no devengo ÷ cartera bruta; castigos netos ÷ cartera media;
  - en IFRS la cartera es la neta de provisiones y la provisión queda sin dato (la NIIF no tiene concepto estándar);
  - sin conceptos estándar: **«riesgo de crédito no medido»** con su motivo.
- Solo bancos (`classification.subtype == "banco"`). Informa: no puntúa ni tiene umbrales de «elevado» (no hay aquí
  una referencia con fuente para fijarlos; se podría calibrar con las tasas de castigos de la Fed, en FRED).
- **Tabla de solidez:** filas «Coste del riesgo», «Provisión sobre cartera», «Morosidad a 90 días», «Cartera en no
  devengo» y «Castigos netos», con la cifra, el importe, la base y la fuente; o una fila «Riesgo de crédito: No
  medido» con el motivo.
- **Un banco nunca muestra «0 riesgos» sin haber medido el crédito:** advertencia «Riesgo de crédito no medido»
  (`alert_interpretations._credit`, peso en `thresholds.alerts.credit_risk`) y la cuenta de riesgos lleva la salvedad
  en la web y en los dos PDF: «0 riesgos (el riesgo de crédito no está medido)».
- **«Capitalización»** pasa a «Patrimonio / activos … (no es capital regulatorio)», con el umbral de la configuración
  (antes un 6 % escrito a mano). Los puntos no cambian.
- **FDIC BankFind no se usa:** es gratuito, pero mide cada banco de la licencia, no el grupo cotizado, y para los grupos
  de EE. UU. el 10-K ya trae los totales.
- Fixtures: `tests/capture_credit_f9.py` añade al juego f2b los hechos de `sec_edgar.CREDIT` presentados hasta la fecha
  de captura (2.755 hechos; el User-Agent, del Llavero en el mismo comando).

**En vivo:** NU «no medido» (advertencia y salvedad); JPM 0,83 % de coste del riesgo, 1,83 % de provisión, 0,73 % de
castigos; BAC 0,49 %, 1,11 %, morosidad 0,18 %, no devengo 0,49 %, castigos 0,49 %; BCS 0,66 % (deterioro de activos
financieros, sin provisión); HSBC 0,43 % (sin provisión).

**Tests** (`tests/test_credit_risk_f9.py`): US GAAP con cartera media; IFRS sin provisión; sin conceptos, «no medido»
con su fila; la advertencia; los cuatro bancos del panel medidos; solo bancos; «Patrimonio / activos».

---

## Mejoras pendientes (después de la v4)

- **Umbrales de «coste del riesgo elevado» (R6).** Hoy las métricas de crédito informan y no tienen lectura de
  «elevado»: no había una referencia con fuente para fijar el umbral. Propuesta: calibrarlos con las tasas de castigos
  netos de la Reserva Federal (FRED, gratuito: todos los préstamos y tarjetas de crédito de los bancos comerciales de
  EE. UU.), con la fecha de los datos en la configuración y revisión periódica. Decisión del PM (27-oct-2026): para
  después de la v4.
