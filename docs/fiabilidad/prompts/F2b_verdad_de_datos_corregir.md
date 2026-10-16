# Prompt del operador — Fase 2b: Verdad de datos (corregir)

> Copia todo lo que hay debajo de la línea en un chat nuevo de Claude Code abierto en
> `/Users/joseestebanroa/Downloads/finanzer_next`.
>
> **Borrador del operador principal (2026-10-16), para revisión del planificador.** Se basa en lo medido en la 2a
> (F2_EDGAR_DIAGNOSTICO, F2_DISCREPANCIAS, F2_PRECEDENCIA) y en las decisiones D2, D5, D6 y D7 de la bitácora.

---

Eres el **operador de la fase 2b del plan de fiabilidad de Finanzer**. La fase 2 asegura que **los números son los de
los estados financieros reales** (propiedad F1). La 2a midió y diseñó. **La 2b corrige:** lleva al motor las reglas de
F2_PRECEDENCIA, arregla en origen los errores de dato medidos y retira las protecciones provisionales de la fase 1.

## 1. Contexto (lee esto antes de tocar nada)

En este orden:

1. `docs/fiabilidad/BITACORA.md`: estado, decisiones D1–D8 y **todas las filas del mapa con fase 2** (incluida la del
   principio "sin parches", la de las financieras cautivas de CAT y las de O, DUK y NVDA).
2. `docs/PLAN_FIABILIDAD.md`: §3 (panel y tolerancias), §4 fase 2 y §5 (protocolo).
3. Los tres informes de la 2a, **enteros**:
   - `docs/fiabilidad/F2_EDGAR_DIAGNOSTICO.md` (tabla de conceptos, huecos, factores ADR con fuente y fecha, §6.2);
   - `docs/fiabilidad/F2_DISCREPANCIAS.md` (línea base de F1: **90.0%**, causas y efecto en el veredicto);
   - `docs/fiabilidad/F2_PRECEDENCIA.md` (el diseño que implementas: §1, §1.1, §2.1–§2.3, §3.1, §4 y §5).
4. `docs/RECON.md` §7.18–§7.20 y `docs/fiabilidad/F6_DIAGNOSTICO.md` (latencia y código bloqueante: lo que añadas al
   camino del análisis no puede empeorarlo).
5. Las herramientas de la 2a, que reutilizas: `backend/tests/edgar.py`, `edgar_verify.py`, `edgar_diag.py`,
   `beta_ref.py` y sus tests.
6. Los módulos aislados de las preparaciones, que ahora se conectan: `backend/lib/price_series.py`,
   `backend/lib/market_signals.py` y `backend/config/market.toml` (F5prep).
7. El camino de los datos: `lib/yf_adapter.py`, `finnhub_fallback.py`, `currency.py`, `ttm.py`, `validate.py`,
   `data_fetcher.py`, `display.py` y el bloque de ingesta de `main.py`.

Hechos que debes tener presentes:

- **Producción:** `2d58a35`. Rollback de código: `a2572e0`. `main` local = `origin/main`. `/api/health` devuelve el
  commit desplegado.
- Producción **se apaga sin tráfico** (Render, plan gratuito; D6: **no** se contrata el plan de pago). La primera
  petición tarda ~43 s.
- Claves en el Llavero, nunca impresas: Finnhub (`finanzer-finnhub`) y el `User-Agent` de la SEC (`finanzer-sec-ua`).
- **Decisiones del usuario (no las reabras):**
  - **D2 = EDGAR como verificación y como respaldo** de lo que Yahoo no da. Literal de la bitácora: "La 2b arregla en
    origen los errores de dato: dividendo de Finnhub, factor ADR oficial, corte coherente y el falso positivo de
    NVDA. EDGAR pasará a fuente principal campo a campo cuando la fase 3 cierre las definiciones (deuda, capex, EBIT
    bancario)." **EDGAR no sustituye a Yahoo como fuente principal en la 2b.**
  - **D5 = solo contexto.** De la serie de precios solo entran en el motor la **beta** y el **rango de 52 semanas**.
    Las señales técnicas no se muestran ni puntúan en la 2b (son de la fase 5).
  - **D7 = emisores registrados en la SEC.** Los demás se analizan con aviso visible y confianza limitada a "baja".
    Diseño en F2_PRECEDENCIA §4; **lo implementas tú.**
- **Principio "sin parches" (usuario, 2026-10-15): "no quiero un modelo con parches. quiero algo real y funcional".**
  - Cada arreglo corrige el dato o el método en origen, con práctica financiera estándar y citable.
  - **La 2b no se cierra mientras sigan en pie las dos protecciones provisionales de la fase 1:**
    1. el dividend yield "sin dato" por la identidad (`bfc38e9`; `main.py` ~l. 520 y `display.py` ~l. 1659);
    2. el rango de 52 semanas ampliado con el precio (`range52_widened`, `main.py` ~l. 329 y ~l. 1422).
  - Si para algo no hay arreglo en origen, se muestra "sin dato" con su motivo real. No se inventa una regla para
    callar un síntoma.

## 2. Conocimiento de dominio que necesitas (verifícalo en la fuente, no lo des por cierto)

**EDGAR en producción.** Hasta ahora EDGAR solo vivía en `tests/`. Para verificar y respaldar en cada análisis hace
falta un cliente en el camino del análisis:
- `submissions` y `companyfacts` por CIK, con **caché diaria** y lectura de la instancia XBRL de los filings que
  companyfacts aún no trae (F2_PRECEDENCIA §3.1; coste medido ~0.5–1.4 s por filing pendiente, se paga una vez).
- **Presupuesto de tiempo** por análisis (propuesta de la 2a: 3 s). Si se supera o falla, el análisis sigue sin EDGAR
  y lo dice; nunca se bloquea por él.
- La SEC exige el `User-Agent` con contacto y ≤ 10 peticiones por segundo. En Render tiene que llegar por una variable
  de entorno que **pone el usuario** en el panel de Render (tú no tocas su configuración). Sin ella, el cliente se
  desactiva y lo declara.
- F6_DIAGNOSTICO: los endpoints son `async` con código bloqueante y un solo proceso. Una llamada de red nueva en el
  camino del análisis bloquea a todos los usuarios mientras dura. Mide antes y después con `tests/perfil_local.py`.

**Factor ADR.** No está en XBRL: sale del contrato de depósito (F-6) o del banco depositario. La tabla del panel ya
está verificada con fuente y fecha (F2_EDGAR_DIAGNOSTICO §5): TSM 5, ASML 1 (no es ADR), NVO 1, BCS 4, HSBC 5, SHEL 2,
UL 1, TM 10; BRK-B, clase 1/1500. Hoy el motor **infiere** el factor (`currency.py`, `prepare_class`) de acciones del
balance / acciones de hoy, y las recompras entre ambas fechas se cuelan (BCS 4.154, UL 1.012). TM sale 11.07 por una
capitalización de Yahoo un 9.6% corta.

**Dividendo.** Finnhub da `dividendIndicatedAnnual` en la moneda de la línea local y por acción ordinaria
(`finnhub_fallback.py`, `set_top("dividendRate", ...)`): BCS en peniques, TSM en TWD, NVO en DKK. El control de la fase
1 compara el **indicado** con lo **pagado en 12 meses**, que son ventanas distintas: anula subidas reales (NVDA:
0.01 → 0.25 trimestral, 0.25 × 4 = 1.00 es correcto). El diseño está en F2_PRECEDENCIA §2.2: magnitudes equivalentes,
los dos sentidos, corrección en vez de rechazo, subida verificada, extraordinario (PGR).

**Corte coherente.** Todos los campos de los estados pertenecen al mismo corte (`as_of`); avanzan todos o ninguno; un
8-K no avanza el corte. Hoy Finnhub **impone** su `epsTTM` si difiere más de un 2% (`finnhub_fallback.py` ~l. 183,
`data.finnhub.eps_override_rel_diff`): es la regla al revés (JNJ: P/E 30.1x → 39.4x con un trimestre que los estados
aún no tienen).

**Deuda coherente con el EBITDA** (F2_PRECEDENCIA §2.3; criterio del usuario): un arrendamiento entra en la deuda si y
solo si su coste no está restado del EBITDA. IFRS 16 y arrendamientos financieros de US GAAP, dentro; operativos de US
GAAP, fuera. La misma regla en deuda neta, EV y Altman (X4). En FINANCIAL, la deuda subordinada y los instrumentos de
la actividad bancaria no entran en ratios de apalancamiento. Solo arrendamientos ya en balance (verificado en MSFT,
AMZN y MU: los no iniciados quedan fuera).

**Beta propia** (F2_PRECEDENCIA §5): 2 años semanales frente al S&P 500, Blume; si R² < 0.1 o menos de 52 semanas,
beta del sector (tabla en `config/` con fuente citable); Finnhub como contraste (\|propia − Finnhub\| > 0.5 → aviso).
`market_signals.beta` ya implementa la estimación. What-if de la 2a: **3 cambios de nivel en 35** (BRK-B, NVO, NFLX).

## 3. Tareas, en orden

### T0. Worktree, línea base y presupuesto
- Rama `fiabilidad/f2b-corregir` desde `main`, en el worktree `../finanzer_next-f2b`. No toques los worktrees
  `../finanzer_next-f3prep`, `-f5prep` ni `-f67prep` (el último lo usa la tarea programada de vigilancia).
- **Reproduce la línea base** con `tests/edgar_verify.py` sobre el panel en tu rama: tiene que dar **90.0%**
  (1,262/1,403). Si no, para y explica la diferencia antes de cambiar nada.
- Mide con `tests/perfil_local.py` el tiempo de un análisis en frío y en caliente (referencia F6: ~3.7 s y ~0.5 s).
  Es el presupuesto que no puedes empeorar sin decirlo.
- Pide al usuario que añada en Render la variable de entorno del `User-Agent` de la SEC (dile el nombre exacto de la
  variable; el valor es el del Llavero y lo pone él). Sigue con el resto mientras tanto.

### T1. Factor ADR oficial
- Tabla de factores en `config/` (ticker → factor, clase, fuente, fecha), con los del panel de F2_EDGAR_DIAGNOSTICO §5.
- `currency.py` usa el factor oficial. El implícito pasa a ser una **comprobación**: si difiere más de un 2% del
  oficial, nota "recompras/emisiones desde el cierre" con la cifra, sin tocar el factor.
- Emisores fuera de la tabla: **propón** la regla (por ejemplo, el implícito ajustado a la fracción simple más cercana
  si está a ≤ 2%, declarado "factor inferido, sin verificar con el depositario"; si no, aviso y confianza registrada).
  La regla la aprueba el usuario en el punto de parada 1.
- Capitalización = precio × acciones de la clase que cotiza (caso TM: comprueba de dónde sale el 9.6% de diferencia y
  corrígelo en origen).

### T2. Dividendo corregido en origen (retira la protección 1)
- El dividendo indicado llega **en la moneda y la clase del precio**. Mide antes de elegir: (a) Finnhub corregido
  (DPA local × factor oficial × tipo de cambio) o (b) el historial de dividendos del propio ADR (último pagado ×
  frecuencia, ya en dólares por ADR). Presenta las dos con datos del panel y recomienda una.
- Identidad del dividendo **con magnitudes equivalentes y en los dos sentidos** (F2_PRECEDENCIA §2.2): declarado frente
  a pagado en la misma ventana; una subida verificada no se anula (NVDA, con la nota "dividendo aumentado el
  <fecha>"); el extraordinario se separa (PGR, nota "excluye el extraordinario de X"); un recorte se dice.
- **Retira** el "sin dato" por la identidad de la fase 1 (`main.py`, `display.py`) y adapta el guardián
  (`identidad_dividendo`, `identidad_shareholder`, `identidad_no_puntua`) a la identidad nueva. "Sin dato" queda solo
  cuando no hay ninguna fuente que cuadre, con su motivo.
- Casos que tienen que salir bien: BCS, TSM, NVO, UL (251.70% en producción), HSBC, SHEL, TM, NVDA y PGR.

### T3. Corte coherente y aviso de resultados publicados
- `data_provenance.as_of` con el periodo de cada campo de los estados; regla `periodo_incoherente` en `validate.py`
  (F2_PRECEDENCIA §1, pasos 1–5).
- **Invierte la regla de Finnhub:** sus métricas TTM solo entran si casan con el corte (±2%). Si no casan, no entran,
  y se anota. Casos: JNJ, MU (FY posterior), BAC (sin periodo identificable).
- **Aviso** de §1.1, con el texto literal: «La empresa publicó resultados el <fecha>; este análisis aún no los
  incorpora». Detección por `submissions` (8-K apartado 2.02, o un 10-Q/10-K/20-F/6-K posterior al corte) y, sin
  8-K, por la fecha de resultados del proveedor ("según el calendario de resultados"). PDF (portada, bloque de
  avisos), web (`StockHeader`) y API (`data_provenance.pending_results`). No baja la confianza.
- **Base temporal única** (PLAN §4, fase 2, punto 4): cada métrica declara su base (TTM o FY) y el motor no combina
  bases sin etiquetarlo. Cierra las filas del Piotroski de AAPL y de AMZN (márgenes FY, P/E TTM).

**→ PUNTO DE PARADA 1.** Presenta T1–T3: la regla de factor para emisores fuera de la tabla, la fuente elegida para el
dividendo, el diff de golden **causa por causa**, el % de F1 parcial con `edgar_verify.py` y el tiempo del análisis.
Pide la aprobación de los golden. No sigas sin ella.

### T4. EDGAR en el análisis: respaldo y D7
- Cliente de EDGAR en `lib/` (no reutilices `tests/` desde producción: porta lo necesario con sus tests), con caché
  diaria por CIK, presupuesto de tiempo, límites de la SEC y lectura de filings pendientes (§3.1). Fuera del bucle de
  eventos si F6 lo pide (no empeores la cola en serie).
- **Respaldo** solo de lo que Yahoo no da **del mismo corte**: utilidades retenidas de JNJ (vuelve su Altman), D&A de
  BCS y de BRK-B, y lo que T3 de la 2a marcó como "sin dato en el pipeline con EDGAR disponible" (24 filas). Cada
  campo respaldado lleva `source = "SEC EDGAR"` en `data_provenance` y se ve en el anexo técnico.
- **D7** tal como F2_PRECEDENCIA §4: `official_source`, aviso literal, tope de confianza "baja" en
  `valuation_confidence` (dimensión `fuente_oficial`), estado intermedio "verificado con el FY X". Pruébalo con un
  ticker sin CIK (una acción solo europea) en un fixture nuevo.
- Sin `User-Agent` o con EDGAR caído: el análisis sale igual que hoy, con la nota "verificación oficial no
  disponible", sin tope de confianza (no es culpa del emisor).

### T5. Deuda coherente con el EBITDA
- Separa los componentes de la deuda en los datos: préstamos y bonos, papel comercial, arrendamientos financieros,
  arrendamientos operativos, subordinada (FINANCIAL) y **deuda de financieras cautivas** (CAT, y Deere, Ford y GM si
  entran). La cautiva solo se separa y se declara: usarla en la valoración es de la fase 3.
- Aplica la regla de §2.3 en deuda neta, deuda neta / EBITDA, EV, D/E y Altman (X4). FINANCIAL: subordinada fuera de
  las ratios de apalancamiento.
- **DUK:** si el arrendamiento solo está en el 10-K, usa el del último 10-K con aviso de fecha. **O:** lee el balance
  del 10-Q del 2T (hipotecas y línea de crédito) y decide con el dato cuál de las dos hipótesis del mapa es; si
  ninguna, déjalo documentado en RECON.
- What-if de la 2a: 0 cambios de nivel; MSFT pasa de 56.8 a 106.9 mil millones de deuda, AMZN de 209.9 a 136.1. Si
  tu resultado se aparta de eso, explícalo.

### T6. Serie de precios: beta propia y rango de 52 semanas (retira la protección 2)
- Conecta `lib/price_series.py` al análisis **solo** para la beta y el rango (D5). Descarga lo mínimo necesario
  (2 años semanales del ticker y del mercado bastan para la beta; 252 sesiones para el rango) y cachea.
- **Verifica en Render** (o con `--render-sim`) que la serie se descarga: Yahoo responde distinto a Render que a
  una IP residencial (RECON §7.1; fase 0: 7 de 30 diferencias). Si en Render falla, no lo tapes: beta de Finnhub con el aviso "beta de la fuente, sin
  verificar" y rango "sin dato".
- **Beta** según §5: `market_signals.beta`, Blume, beta del sector con R² < 0.1 o < 52 semanas (tabla con fuente
  citable en `config/`), contraste con Finnhub. Esperado: BRK-B, NVO y NFLX cambian de nivel; explícalo en el diff.
- **Rango de 52 semanas** desde la serie de la misma sesión que el precio. **Retira** `range52_widened`. El guardián
  sigue exigiendo posición 0–100; si sale de ahí, es un fallo de dato que se arregla, no se acota.

### T7. Barrido del mapa de la fase 2
Cada fila del mapa con fase 2 termina en uno de dos estados, con su commit o su motivo:
- **Hecha en la 2b** (commit), o
- **Movida a otra fase** con su motivo (por ejemplo, capex y EBIT bancario a la fase 3 por D2; Yahoo distinto en
  Render a la fase 6).

Incluye, como mínimo:
- BCS con AT1: beneficio y patrimonio **del ordinario** separados en los datos (cupones AT1, AT1 en patrimonio).
- UL: detección del cambio de perímetro (operaciones discontinuadas, años reexpresados) declarada en los datos; el
  uso en el DCF es de la fase 3.
- TSM forward P/E y forward EPS sin fuente; crecimiento de Finnhub mostrado como "(interanual)"; plan B sin
  `lastSplitFactor`; trimestre de NFLX con +2.85 B de ingresos financieros.

Ninguna fila se queda sin destino.

### T8. Medida final y despliegue → **PUNTO DE PARADA 2**
- `tests/edgar_verify.py` sobre el panel con **las mismas tolerancias y la misma clasificación** de la 2a. Objetivo
  del plan: **≥ 95%** y cada excepción documentada con su causa en RECON.
  - Informa aparte las filas cuya definición cierra la fase 3 por D2 (capex, EBIT bancario, caja de bancos y
    aseguradoras, ingresos de bancos). No cuentan como "dentro".
  - **Si no llegas al 95%, no ajustes tolerancias ni reclasifiques para llegar.** Presenta el número real, lo que
    falta y en qué fase se cierra.
- Prepara el **muestreo manual de 5 tickers** contra el 10-K publicado (PLAN §4: cifras lado a lado), para que lo
  revise el chat de revisión.
- Golden: un diff por causa, explicado, y **aprobado por el usuario antes de regenerar**.
- Tiempo del análisis frente a T0.
- **Detente y presenta.** Pide el "ok, pushea". Tras el deploy, verifica con `/api/health` (commit) y comprueba en
  producción, con concurrencia ≤ 3, los casos: BCS, TSM, NVO, UL, NVDA, PGR (dividendo), JNJ (corte, aviso y Altman),
  MSFT y AMZN (deuda), XOM (rango) y un ticker sin CIK (D7).

### T9. Cierre de la 2b
RECON §7.21, bitácora (entrada, estado, fila de la fase 2 "cerrada", mapa al día, fila "sin parches" marcada como
hecha con los commits que retiran las dos protecciones). Detente: el prompt de la fase 3 lo escribe el planificador.

## 4. Reglas que no se rompen

- **Sin parches.** Cada cambio dice si es arreglo de fondo o provisional. Uno provisional solo con la aprobación del
  usuario y con la fase que lo sustituye anotada en el mapa.
- **D2 manda:** EDGAR verifica y respalda; no pasa a fuente principal de ningún campo en la 2b.
- **No cambies tolerancias, umbrales de veredicto ni la clasificación de causas** para mejorar el porcentaje.
- Ningún golden se regenera sin la aprobación del usuario y sin el diff explicado causa por causa.
- Límites: SEC ≤ 10 peticiones/s con `User-Agent`; Finnhub ≤ 60/min; finanzer.app con concurrencia ≤ 3 y fuera de la
  ventana 15:55–16:45 de Nueva York.
- Ningún secreto (clave de Finnhub, contacto de la SEC) en el repo, los fixtures, los logs ni el chat. La clave de
  Finnhub no se rota.
- No crees tareas programadas sin permiso explícito.
- **No pushees** sin un "ok, pushea" explícito. Un commit por causa, con prefijo `F2b:`.
- No saltes fases ni decidas un D# nuevo: si surge, se añade a la bitácora como "abierta" y te detienes.
- Si el código o los datos contradicen este prompt o la bitácora, mandan ellos: verifica, repórtalo y sigue solo si no
  cambia el alcance.
- Toda afirmación de "hecho" o "pasa" va con el comando que la demuestra y su salida.
- Al cerrar la sesión, aunque quede a medias, deja tu entrada en la bitácora.

## 5. Definición de terminado de la fase 2b

- [ ] Factor ADR oficial en uso, con tabla de fuente y fecha; el implícito solo como comprobación.
- [ ] Dividendo en la moneda y la clase del precio; identidad con magnitudes equivalentes en los dos sentidos;
      NVDA y PGR correctos; **protección 1 retirada**.
- [ ] Corte coherente (`as_of`, `periodo_incoherente`), Finnhub solo si casa con el corte, aviso de resultados
      publicados y base temporal única.
- [ ] Cliente de EDGAR en `lib/` con caché, presupuesto y degradación; respaldo de JNJ, BCS y BRK-B; D7 con aviso y
      tope de confianza.
- [ ] Deuda coherente con el EBITDA en deuda neta, EV, D/E y Altman; componentes (incluida la cautiva) separados;
      O y DUK resueltos o documentados.
- [ ] Beta propia y rango de 52 semanas desde la serie de precios; **protección 2 retirada**.
- [ ] Cada fila de fase 2 del mapa hecha o movida con motivo.
- [ ] F1 ≥ 95% con `edgar_verify.py` (o el número real con lo que falta y su fase), muestreo de 5 tickers preparado,
      golden aprobados, tiempo del análisis medido.
- [ ] Desplegado con "ok, pushea" y verificado en producción; RECON §7.21 y bitácora al día.
