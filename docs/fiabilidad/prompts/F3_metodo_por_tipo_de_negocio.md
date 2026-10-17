# Prompt del operador — Fase 3: Método por tipo de negocio

> Copia todo lo que hay debajo de la línea en un chat nuevo de Claude Code abierto en
> `/Users/joseestebanroa/Downloads/finanzer_next`.
>
> **Borrador del operador principal (2026-10-16), para revisión del planificador.** Implementa
> `F3_DISENO_METODO.md` (D3, D4 y los ajustes de su §8) con lo que dejó la fase 2 (RECON §7.21, F2b_PARADA2 §1.1 y §6).

---

Eres el **operador de la fase 3 del plan de fiabilidad de Finanzer**. La fase 3 asegura que **cada empresa se analiza
con las herramientas de su tipo de negocio** (propiedad F2). La fase 2 dejó los datos verificados contra la SEC; ahora
toca el método: clasificar por la historia real, juzgar el precio con dos métodos independientes (D3: DCF inverso) y
leer cada tipo de empresa como lo haría un analista.

## 1. Contexto (lee esto antes de tocar nada)

En este orden:

1. `docs/fiabilidad/BITACORA.md`: estado, decisiones D1–D8 y **todas las filas del mapa con fase 3** (incluidas las
   movidas desde la 2b: BRK-B en base anual, definiciones de D2, cautiva de CAT, ROTE con AT1, perímetro de UL).
2. `docs/PLAN_FIABILIDAD.md`: §3 (panel y tolerancias), §4 fase 3 y §5 (protocolo, con el punto 11).
3. **`docs/fiabilidad/F3_DISENO_METODO.md`, entero.** Es el criterio que implementas; su §8 (ajustes tras la muestra
   de F3prep) está **decidido** y manda sobre §1–§7 donde choquen.
4. `docs/fiabilidad/F3PREP_MUESTRA.md` y `F3PREP_REGISTRO.md`: lo que ya hacen `lib/reverse_dcf.py` y
   `lib/bank_implied.py` (aislados, sin conectar) y por qué la muestra cambió el contraste del DCF inverso.
5. `docs/RECON.md` §7.17 (precio con un solo método), §7.20 y §7.21 (cierre de la fase 2 y lo que pasa a la 3);
   `docs/fiabilidad/F2b_PARADA2.md` §1.1 (filas cuya definición cierra la fase 3) y §6 (observaciones nuevas).
6. El motor: `lib/classify.py` (clasificador), `archetype_metrics.py`, `financial_ratios.py` (DCF y score),
   `verdict.py`, `valuation_confidence.py`, `historical_metrics.py`, `normalize.py`, `perimeter.py`, `ordinary.py`,
   `debt.py`, `display.py`, `plain_language.py` y `config/thresholds.toml`, `valuation.toml`, `sectors.toml`,
   `betas.toml`; los datos: `lib/sec_edgar.py` y `lib/edgar_backup.py` (fase 2b).
7. `backend/tests/README.md`, `panel_run.py`, `diff_golden.py`, `edgar_verify.py` y el guardián (`tests/guardian.py`).

Hechos que debes tener presentes:

- **Producción:** `01336e2` (código `103c76f`). Rollback de código: `60f8a69`. `main` local = `origin/main`.
  `/api/health` devuelve el commit desplegado. Render se apaga sin tráfico (D6: sin plan de pago).
- **Si `SEC_EDGAR_USER_AGENT` aún no está en Render, producción va sin EDGAR.** Compruébalo al empezar (`/api/health`
  o un análisis de JNJ: si su Altman sale "sin dato", no está). Todo lo que la fase 3 apoye en EDGAR debe degradar
  igual que en la 2b ("verificación oficial no disponible") y decirlo.
- **F1 al cierre de la fase 2: 91.4%** (1290/1411; `edgar_verify.py --whatif`). Es la referencia que la fase 3 **no
  puede empeorar** salvo por un cambio de definición aprobado y explicado.
- `frontend/out` se compila con `npm run build` (Turbopack) en el checkout principal; en un worktree el
  `node_modules` es un enlace y Turbopack falla, y con webpack `build.sh` de Render rechaza el deploy.
- **Decisiones del usuario (no las reabras):**
  - **D2:** EDGAR verifica y respalda; **pasa a fuente principal campo a campo cuando esta fase cierre las
    definiciones** (deuda, capex, EBIT, EBIT bancario, ingresos y caja de bancos y aseguradoras). Esa decisión por
    campo la toma el usuario en el punto de parada 1.
  - **D3:** DCF inverso como segundo método cuando el directo no concilia; la confianza no se contrae por la mera
    ausencia del segundo método (opción 3 de RECON §7.17).
  - **D4:** se crea GROWTH_PROFITABLE; la ciclicidad se mide con la historia real (10+ ejercicios) y va antes que el
    crecimiento.
  - **D5:** lo técnico es solo contexto; nada de señales en el score.
  - **D7:** emisores sin CIK con aviso y confianza "baja" (hecho en la 2b; MC.PA en el panel).
- **Principio "sin parches" (usuario):** "no quiero un modelo con parches. quiero algo real y funcional". Cada regla
  de método se justifica con práctica estándar citable (Damodaran, Mauboussin y Callahan, CFA, la propia empresa) y
  se mide en el panel. Nada de cotas silenciosas (F3_DISENO §0, principio 4).

## 2. Conocimiento de dominio que necesitas (verifícalo en la fuente, no lo des por cierto)

- **Tasas base** (Mauboussin y Callahan, *The Base Rate Book*, Credit Suisse, 2016): proporción de empresas, por tramo
  de ingresos, que sostuvieron un CAGR de ventas dado durante 3, 5 y 10 años. **No cites cifras de memoria:** localiza
  el documento, extrae la tabla con página y edición, y guárdala en `config/` con su fuente. Si no encuentras una
  fuente verificable, para y dilo: sin tasas base no hay §8.1.
- **Ciclicidad:** mídela con la historia anual de EDGAR (ingresos, margen operativo, BPA, acciones), en la moneda de
  los estados y por acción si hubo emisión relevante; excluye los saltos explicados por cambio de perímetro (la 2b
  ya los declara: UL, BAC, AMT, JNJ, DUK).
- **Conglomerados (BRK-B):** sus "ingresos" incluyen ganancias de inversión; la ciclicidad y el crecimiento se miden
  sin ellas. Valoración por P/B, la métrica que usa la propia empresa.
- **Bancos:** ROTE implícito = P/TBV × (Ke − g) + g (`lib/bank_implied.py`); ROTE del accionista ordinario con los
  AT1 y sus cupones separados (la 2b ya separa beneficio y patrimonio del ordinario, `7b610a7`). Crecimiento con el
  margen de intereses y las comisiones, no con "Total Revenue".
- **Financieras cautivas** (CAT, DE, F, GM): la deuda de la financiera, respaldada por su cartera de préstamos, no
  entra en la deuda neta industrial. La 2b ya la separa y la declara (CAT 34.46 mil millones).
- **REIT:** el inverso, sobre FFO/AFFO por acción, no sobre FCF.

## 3. Tareas, en orden

### T0. Worktree y línea base
- Rama `fiabilidad/f3-metodo` desde `main`, en `../finanzer_next-f3`. No toques los worktrees `-f3prep`, `-f5prep`,
  `-f2b` ni `-f67prep` (el último lo usa la tarea programada de vigilancia).
- Línea base en tu rama: suite y guardián en verde; `edgar_verify.py --whatif` = 91.4%; y la **tabla del panel**
  (37 tickers con MC.PA): arquetipo, calidad, precio, confianza, métodos de precio evaluables y si el DCF directo
  concilia. Es la referencia de cada diff de la fase.
- Comprueba si `SEC_EDGAR_USER_AGENT` está en Render (sin pedirlo de nuevo si ya está).

### T1. Definiciones de D2, historia larga y tasas base → **PUNTO DE PARADA 1**
- **Definiciones** (F2b_PARADA2 §1.1; las 31 filas que la fase 2 dejó "fuera por definición"): para capex, EBIT,
  EBIT bancario, ingresos de bancos y de BRK-B, y caja de bancos y aseguradoras, propón la definición que quiere el
  motor con su práctica estándar citada, el concepto XBRL que la mide y qué hace hoy Yahoo. Propón también, campo a
  campo, si **EDGAR pasa a fuente principal** (D2) con lo que gana y lo que cuesta (cobertura, 20-F sin trimestres,
  latencia, efecto en el veredicto con un what-if).
- **Historia larga:** el cliente de la 2b guarda 4 ejercicios para el respaldo (`edgar.fy_backup_years`). La
  clasificación y el ciclo medio necesitan 10+. Diseña cómo se obtiene (companyfacts ya trae la historia; la
  cuestión es qué se conserva y en qué caché) y mide su coste.
- **Moneda del crecimiento** (F2b_PARADA2 §6): UL crece +0.5% en USD y −3.8% en EUR. Propón medir el crecimiento y el
  CAGR en la moneda de los estados (práctica estándar: el crecimiento operativo no incluye el tipo de cambio) y
  declarar aparte el efecto divisa.
- **Tasas base:** la fuente con página y edición, la tabla que vas a usar y cómo se asigna el tramo de una empresa.
- **Detente y presenta** las cuatro cosas. El usuario decide la definición de cada campo, qué campos pasan a EDGAR
  principal, la moneda del crecimiento y la fuente de tasas base. Registra cada decisión literal en la bitácora.

### T2. Clasificador (D4) → **PUNTO DE PARADA 2**
- Implementa el orden de F3_DISENO §1.1 con la ciclicidad medida (§1.2) y GROWTH_PROFITABLE (§1.3), con los
  subtipos de FINANCIAL (§1.4: banco, aseguradora, conglomerado).
- **Calibra los umbrales de §1.2 con el panel** y anota la calibración (qué umbral, qué tickers cambia, por qué).
  Prohibido elegir umbrales para que salga un ticker concreto: los casos esperados son la prueba, no el objetivo.
- Con historia < 8 ejercicios, la regla de industria actual con confianza baja, y dicho.
- Entrega la **tabla de arquetipos del panel**: obtenido, esperado según el diseño, las medidas que lo deciden y la
  justificación de analista en una línea.
- **Detente y presenta.** El usuario aprueba los arquetipos **línea a línea** (PLAN §4 fase 3: terminado cuando todo
  el panel tiene arquetipo aprobado). No sigas con T3 sin esa aprobación: el método depende del arquetipo.

### T3. DCF unificado e inverso (D3)
- **Una sola estructura** para el directo y el inverso (F3_DISENO §8.2): crecimiento constante años 1–5,
  convergencia lineal al terminal años 6–10. Retira los decaimientos lineal y exponencial; revisa el `growth_cap` del
  directo y dilo en el diff.
- **FCF − SBC siempre** que haya dato de SBC (§8.4).
- Conecta `lib/reverse_dcf.py` con la referencia principal = **tasas base** (§8.1) y el histórico propio (ingresos
  por acción, 5–10 años) como segunda referencia, que nunca hace "barata" una exigencia que las tasas base
  consideran excepcional. "Exige más de +60%" se informa como tal (§8.3).
- **Cíclicas:** las dos lecturas de §8.5 (ciclo medio y TTM). **REIT:** sobre FFO/AFFO (§8.7).
- **Veredicto** (§2.3): el inverso es el método intrínseco cuando el directo no concilia; la contracción de la
  confianza solo por discrepancia entre métodos o datos débiles, no por falta del segundo método (D3). Texto
  obligatorio de §2.2, que pasa por el guardián.
- **Contraste independiente** en 5 tickers (una hoja o un script aparte, no el código del motor): el crecimiento
  exigido coincide a ±0.1 pp.

### T4. Financieras
- Banco: P/TBV frente a ROTE (justificado e implícito, con sensibilidad ±2 pp), ROTE ajustado por AT1, P/E y
  dividend yield como métricas que **sí aplican** (registro #14), crecimiento con margen de intereses y comisiones.
- Aseguradora: P/B frente a ROE, ROE implícito frente al ROE medio del ciclo de suscripción (§8.8); ratio combinado
  si hay dato, si no "sin dato".
- Conglomerado (BRK-B): subtipo explícito, P/B, ingresos sin ganancias de inversión. Resuelve aquí la fila "BRK-B en
  base anual" (movida desde la 2b) con la definición de ingresos aprobada en T1.

### T5. Crecimiento
F3_DISENO §4, con la moneda decidida en T1:
- base por acción;
- **perímetro** (UL: crecimiento sobre operaciones continuadas o "no comparable", sin puntuar);
- convergencia en el DCF directo (TXRH: el CAGR con inflación de precios se dice como riesgo, no se ajusta a ojo);
- **ciclo medio con 10+ ejercicios**, que sustituye la cota −5%/+10% (que queda solo con historia corta, y dicha);
- AMZN con base ≤ 0 (CAGR de ingresos por acción, declarado);
- MATURE de dividendo alto como retorno total;
- AAPL interanual frente a 3 años (mezcla declarada o escenarios; nunca en silencio).

### T6. Lecturas que entienden el modelo de negocio
F3_DISENO §5:
- current ratio < 1 estructural;
- Altman referencial donde el modelo no se diseñó (coherente con la deuda de la 2b);
- avisos del Piotroski por industria;
- bandas de utility en lectura y alertas;
- Graham fuera de los REIT;
- SBC en MATURE;
- **uso de la deuda de la cautiva** (CAT) en la deuda neta del DCF y en el apalancamiento;
- las mejoras aprobadas: DuPont del ROE, margen FCF con tendencia y Rule of 40 (GROWTH_PROFITABLE).

Los compromisos fuera de balance (MSFT 329 mil millones en arrendamientos no iniciados) solo si hay una fuente
estructurada que dé el importe. En XBRL solo viene el plazo. Si no la hay, anótalo en el mapa con su motivo; no lo
saques del texto a mano.

### T7. Verificación y despliegue → **PUNTO DE PARADA 3**
- **Panel:** tabla final de arquetipo, calidad, precio y confianza frente a T0. Cada cambio de nivel, explicado por una
  regla de F3_DISENO con su commit.
- **Ningún precio con DCF de fiabilidad baja sin el inverso mostrado** (PLAN §4: terminado cuando).
- **Fichas de analista:** para un ticker de cada arquetipo, "cómo lo analizaría un analista" frente a lo que hace el
  motor.
- **Revisión externa (punto 11):** 2–3 tickers fuera del panel que estresen los tipos nuevos (un software de
  crecimiento rentable, una cíclica industrial, un banco europeo). Fixture nuevo de cada uno.
- **F1** con `edgar_verify.py`, comparando con la definición aprobada en T1 donde cambió. No empeora frente al 91.4%
  salvo por definiciones aprobadas; informa el número con y sin ellas.
- Golden: un diff por causa, explicado, y **aprobado por el usuario antes de regenerar**. Tiempo del análisis frente
  a T0.
- **Detente y presenta.** Pide el "ok, pushea". Tras el deploy, `/api/health` y comprobación en producción
  (concurrencia ≤ 3) de un ticker por arquetipo, más PLTR, NVDA, CAT, MU, BCS, BRK-B, UL y AMZN.

### T8. Cierre de la fase 3
RECON §7.22, bitácora (entrada, estado, fila de la fase 3 "cerrada", mapa: cada fila de fase 3 hecha o movida con su
motivo). Detente: el prompt de la fase 4 lo escribe el planificador.

## 4. Reglas que no se rompen

- **Sin parches.** Cada regla de método, con práctica estándar citada y medida en el panel. Cada cambio dice si es
  arreglo de fondo o provisional. Uno provisional, solo con la aprobación del usuario y su fase de sustitución en el
  mapa.
- **Los casos esperados son la prueba, no el objetivo:** no ajustes umbrales, bandas ni pesos para que un ticker salga
  como "debería". Si un caso esperado no sale, se explica con datos o se reabre el diseño con el usuario.
- **No cambies tolerancias de F1 ni la clasificación de causas de `edgar_verify`.** Comparar con una definición
  aprobada en T1 sí está permitido, declarado.
- Ningún golden se regenera sin la aprobación del usuario y sin el diff explicado causa por causa.
- Límites: SEC ≤ 10 peticiones/s con `User-Agent`; Finnhub ≤ 60/min; finanzer.app con concurrencia ≤ 3 y fuera de la
  ventana 15:55–16:45 de Nueva York.
- Ningún secreto (clave de Finnhub, contacto de la SEC) en el repo, los fixtures, los logs ni el chat. La clave de
  Finnhub no se rota.
- No crees tareas programadas sin permiso explícito.
- **No pushees** sin un "ok, pushea" explícito. Un commit por regla, con prefijo `F3:`.
- No saltes fases ni decidas un D# nuevo: si surge, se añade a la bitácora como "abierta" y te detienes.
- Si el código o los datos contradicen este prompt, el diseño o la bitácora, mandan ellos: verifica, repórtalo y
  sigue solo si no cambia el alcance.
- Toda afirmación de "hecho" o "pasa" va con el comando que la demuestra y su salida.
- Al cerrar la sesión, aunque quede a medias, deja tu entrada en la bitácora.

## 5. Definición de terminado de la fase 3

- [ ] Definiciones de D2 decididas por el usuario, y EDGAR como fuente principal en los campos que él apruebe.
- [ ] Historia de 10+ ejercicios disponible para clasificar y para el ciclo medio; crecimiento en la moneda decidida.
- [ ] Fuente de tasas base verificada (con página y edición) y en `config/`.
- [ ] Clasificador D4 calibrado y documentado; **todo el panel con arquetipo aprobado línea a línea**.
- [ ] DCF con una sola estructura, FCF − SBC y DCF inverso conectado; **ningún precio con DCF "baja" sin el inverso
      mostrado**; contraste independiente en 5 tickers.
- [ ] Financieras con sus métricas (ROTE implícito y ajustado por AT1, aseguradora, conglomerado); BRK-B resuelto.
- [ ] Crecimiento (§4) y lecturas por modelo de negocio (§5), incluida la cautiva de CAT.
- [ ] Fichas de analista por arquetipo y revisión externa de 2–3 tickers.
- [ ] F1 sin empeorar (o explicado por definiciones aprobadas); golden aprobados; tiempo medido.
- [ ] Desplegado con "ok, pushea" y verificado en producción; RECON §7.22 y bitácora al día.
