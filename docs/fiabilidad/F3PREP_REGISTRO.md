# Registro de la sesión F3prep (para llevar a la bitácora)

> El operador de F3prep no edita `BITACORA.md` (la edita el operador de la 2a en paralelo). El planificador copia
> esta entrada al registro de la bitácora con el número que toque.

### #N · 2026-10-15 · operador · Preparación de la fase 3 (T0–T4 hechas; detenida en el punto de parada T5)

- **Objetivo de la sesión:** prompt `prompts/F3prep_dcf_inverso_y_rote.md`: DCF inverso y ROTE implícito como
  módulos de cálculo aislados, sin conectarlos al motor, con su muestra sobre el panel.

- **Hecho** (rama `fiabilidad/f3-prep` desde `main` = `8ed57a0`, worktree `../finanzer_next-f3prep`, **sin push ni
  merge**):
  - **T0:** `git worktree add ../finanzer_next-f3prep -b fiabilidad/f3-prep main`.
  - **`0f6f21b`, T1 + tests:** `backend/lib/reverse_dcf.py`.
    - `implied_growth` resuelve g\* por bisección, con la estructura del DCF directo en modo `step`: g\* en los
      años 1–5, convergencia lineal al terminal en los años 6–10, Gordon y puente al equity con la deuda neta por
      acción.
    - Comprueba la monotonía en una malla de 41 puntos.
    - Estados: `ok`, `no_aplica` (FCF ≤ 0, WACC ≤ g o sin precio), `fuera_de_rango` (con `side` inferior o
      superior) y `sin_convergencia`.
    - Devuelve g\*, iteraciones, valor reconstruido, error relativo, la senda de crecimientos y los supuestos.
    - `classify_implied_growth` da las bandas `barata`, `en_precio`, `exigente`, `muy_exigente`, `sin_contraste` y
      `sin_dato`.
    - Parámetros en `[reverse_dcf]` de `valuation.toml` y en `schema.toml`.
  - **`7300f8e`, T2 + tests:** `backend/lib/bank_implied.py`.
    - `implied_rote` e `implied_roe` (P/TBV o P/B × (Ke − g) + g).
    - `rote_sensitivity` usa los ± pp de `[bank_implied]` y el centro es el ROTE implícito o el que se pase.
    - Reusa `archetype_metrics.justified_multiple` (sin modificarlo) para que la inversa sea la del motor.
  - **`473531e`, T4:** `backend/tests/f3prep_muestra.py` (replay del panel) y `docs/fiabilidad/F3PREP_MUESTRA.md`.
  - `test_config_literals.py`: los dos módulos entran en `MIGRATED`, con una sola excepción justificada (el `/ 2` del
    punto medio de la bisección).

- **Verificación** (en el worktree, con `/Users/joseestebanroa/Downloads/finanzer_next/.venv313`):
  - suite completa, `../../finanzer_next/.venv313/bin/python -m pytest tests -q` → **"3023 passed, 4 skipped in
    54.13s"**:
    - de ellos, 109 tests nuevos (`test_reverse_dcf.py` y `test_bank_implied.py`) y 2 parametrizaciones nuevas del
      test de literales;
    - 3 de los 4 skips son `test_frontend_contract.py` ("sin Node o sin node_modules del frontend"): el worktree no
      tiene `node_modules`; el cuarto es el skip de siempre;
  - `pytest tests/test_config_literals.py tests/test_reverse_dcf.py tests/test_bank_implied.py -q` → "122 passed";
  - `tests/diff_golden.py --env panel` y `--env local` → "Resultado: sin diferencias" (**0 golden cambiados**;
    `git diff --stat 8ed57a0..HEAD` no toca `tests/golden/` ni `tests/fixtures/`);
  - **aislamiento:** `grep -rln "reverse_dcf\|bank_implied"` → solo los dos módulos, sus tests, el script de muestra
    y el test de literales; ningún módulo del motor (`main.py`, `verdict.py`, `valuation_confidence.py`,
    `display.py`, `pdf_report.py`) ni la web los importan;
  - **ida y vuelta con el DCF directo**, en KO, JNJ, XOM, AAPL y PG (los del panel con DCF `ok` y decaimiento
    `step`):
    - las entradas del golden reproducen al céntimo el `fair_value` del motor;
    - para g en {−15%, −5%, 0, 2.5%, 6%, 12%, 25%, 40%, 50%}, el valor de `dcf_multi_stage(decay_type="step")`
      tomado como precio devuelve g con |error| < 1e-8 y las mismas tasas año a año;
    - el `fair_value` publicado devuelve el crecimiento que usó el motor (< 1e-4, por el redondeo al céntimo);
  - **contraste independiente:** un cálculo escrito aparte (vector de tasas explícito, factores de descuento
    acumulados, secante), en 3 casos, coincide con < 1e-8 (uno es el caso analítico de Gordon: g\* = 2% exacto);
  - **ejemplo BCS de §3:** P/TBV 0.81, Ke 11.0%, g 2.5% → 9.385% (≈ 9.4%);
  - **ida y vuelta exacta** del ROTE y del ROE en JPM, BAC y BCS: diferencia < 1e-12;
  - **muestra:** `../../finanzer_next/.venv313/bin/python tests/f3prep_muestra.py` reproduce el DCF directo de los 21
    tickers con DCF (con un `assert` por ticker) y todas las bisecciones convergen en 33 iteraciones (error relativo
    máximo 2.9e-10).

- **Decisiones tomadas por el usuario:** ninguna en esta sesión.

- **Decisiones de diseño del operador** (a validar por el planificador):
  - **Deuda neta por acción** como parámetro opcional de `implied_growth` (por defecto 0): sin ella el inverso no
    sería coherente con el DCF-FCFF del motor, que resta la deuda neta. El prompt no la nombraba.
  - **`muy_exigente` manda sobre la comparación con la historia:** si la tasa base está por debajo del umbral, la
    banda es `muy_exigente` aunque falte el crecimiento logrado o el g\* sea menor que el logrado. Es mi lectura de
    la tabla de §2.2, cuya fila no pone condición sobre lo logrado.
  - **Umbral de tasa base `very_demanding_base_rate = 0.10`: PROVISIONAL.** Las tasas base reales y su umbral los
    fija la fase 3, con la fuente verificada (§0.5).
  - **Bordes de banda inclusivos:** g\* = logrado ± 5 pp exacto es `en_precio`.
  - **`sin_convergencia`**, un cuarto estado para la salvaguarda de monotonía y el tope de iteraciones; no aparece
    en el panel.

- **Abierto / siguiente paso** (detalle en `F3PREP_MUESTRA.md`, "Lectura"):
  1. **Estructura del DCF directo.** Por encima del 15% decae de forma lineal desde el año 1, y por encima del 25%,
     exponencial; solo el modo `step` coincide con §2.2. Afecta a MSFT, CRWD, TSM y NVO (lineal) y a PLTR, NVDA y
     SNOW (exponencial). La fase 3 debe unificar la estructura o declarar la equivalencia.
  2. **`growth_cap` = 50% del DCF directo frente al +60% del inverso.** Afecta a PLTR (+52.6%) y CRWD (+51.1%).
  3. **La banda frente al CAGR a 3 años engaña en los extremos:**
     - PLTR, NVDA y NFLX salen `barata`;
     - KO, AAPL y NVO salen `exigente`.

     Hacen falta las tasas base y el CAGR de 5–10 años **[2b]** antes de conectar.
  4. **Base del FCF:**
     - FCF − SBC: decidir "donde aplique" (CRWD sale fuera de rango con él; SNOW, `no_aplica`);
     - mantenimiento de ciclo en cíclicas: MU sale fuera de rango con su base de 2.96 mil millones frente a un FCF
       TTM de 26.2 mil millones;
     - deuda de financieras cautivas (CAT).
  5. **PGR:** el ROE de un solo año (37.3%) no sirve para leer el implícito (22.2%) de una aseguradora; hace falta
     el ROE medio.
  6. **Punto de parada T5:** el usuario revisa la muestra, la ida y vuelta y el contraste. Después, el planificador
     lleva esta entrada a la bitácora y decide cuándo se integra la rama.

- **Archivos tocados** (solo en `fiabilidad/f3-prep`):
  - `backend/lib/reverse_dcf.py` y `backend/lib/bank_implied.py` (nuevos);
  - `backend/config/valuation.toml` y `backend/config/schema.toml` (secciones nuevas `reverse_dcf` y
    `bank_implied`);
  - `backend/tests/test_reverse_dcf.py`, `test_bank_implied.py` y `f3prep_muestra.py` (nuevos);
  - `backend/tests/test_config_literals.py`;
  - `docs/fiabilidad/F3PREP_MUESTRA.md` y este archivo.

  **No se tocaron** la bitácora, `main.py`, `yf_adapter.py`, `currency.py`, `validate.py`, `tests/fixtures/` ni
  `tests/golden/`, ni la rama `fiabilidad/f2a-medir`.

- **Avisos para el siguiente chat:**
  - el worktree no tiene `node_modules`: 3 skips de más, que es normal;
  - el `.venv313` es el del repo principal;
  - para recrear la muestra, `tests/f3prep_muestra.py` (sin red);
  - al conectar en la fase 3, este registro y la muestra son la línea base de g\* y del ROTE implícito con los
    fixtures del 14-oct.
