# Prompt del operador — Preparación de la fase 3: DCF inverso y ROTE implícito (módulos aislados)

> Copia todo lo que hay debajo de la línea en un chat nuevo de Claude Code abierto en
> `/Users/joseestebanroa/Downloads/finanzer_next`. **Trabaja en un worktree aparte**: en paralelo hay otro operador
> en la rama `fiabilidad/f2a-medir` del mismo repositorio.

---

Eres el **operador de la preparación de la fase 3** del plan de fiabilidad de Finanzer. Construyes dos piezas de cálculo
**puro y aislado** que la fase 3 conectará al motor más adelante. **No las conectas a nada**: no tocas `main.py`, ni
`verdict.py`, ni `valuation_confidence.py`, ni `display.py`, ni el PDF, ni la web, ni la ingesta de datos. Ninguna salida
de la app ni ningún golden pueden cambiar.

## 1. Contexto (lee antes de tocar nada)

**Importante:** los documentos de planificación de este prompt (`F3_DISENO_METODO.md`, este prompt y la bitácora al
día) están **sin commitear en la carpeta principal** y no aparecerán en tu worktree. Léelos siempre por su ruta
absoluta en `/Users/joseestebanroa/Downloads/finanzer_next/docs/fiabilidad/`. El código, en cambio, léelo y escríbelo
en tu worktree.

1. `docs/fiabilidad/F3_DISENO_METODO.md`: **§2 (DCF inverso) y §3 (ROTE implícito)** son tu especificación. §0 son
   los principios.
2. `docs/fiabilidad/BITACORA.md`: decisiones **D3** (DCF inverso) y **D4**; las filas de BCS del mapa.
3. El DCF directo que ya existe, para que el inverso sea **coherente con él** (misma estructura de etapas, mismo
   terminal, mismo WACC): `backend/lib/financial_ratios.py` (`dcf_multi_stage*`, `dcf_sensitivity_analysis`),
   `backend/lib/cost_of_capital.py` y `backend/config/valuation.toml`. El P/B y el P/TBV justificados de los bancos:
   busca dónde se calculan hoy (`(ROE − g) / (Ke − g)`).
4. `backend/tests/README.md` y `backend/tests/test_config_literals.py`: **ningún literal numérico** en las funciones
   nuevas; los parámetros van a `config/valuation.toml` y a `config/schema.toml`.

Hechos:
- Producción y `main` = `8ed57a0`. Hay otro operador trabajando en `fiabilidad/f2a-medir`; **no toques esa rama ni sus
  archivos**.
- Suite: `cd backend && ../.venv313/bin/python -m pytest tests` (en tu worktree, con el `.venv313` del repo principal:
  `/Users/joseestebanroa/Downloads/finanzer_next/.venv313/bin/python`).

## 2. Tareas

### T0. Worktree
`git worktree add ../finanzer_next-f3prep -b fiabilidad/f3-prep main` y trabaja solo ahí.

### T1. `backend/lib/reverse_dcf.py`
Función principal (nombres orientativos):

`implied_growth(price, fcf_per_share_base, wacc, terminal_growth, years, fade_start, bounds) -> resultado`

- Resuelve el crecimiento anual **g\*** del FCF por acción tal que el valor presente (etapa explícita + valor terminal)
  iguala el precio. **Misma estructura que el DCF directo:** crecimiento g\* en los años 1..(fade_start−1), convergencia
  **lineal** de g\* al terminal en los años fade_start..years, terminal de Gordon con `terminal_growth`.
- **Bisección** acotada en `bounds` (config; propuesta −20%..+60%), con tolerancia y nº máximo de iteraciones en
  config. Comprueba la monotonía del valor en g dentro del rango.
- Casos que devuelven un estado explícito, nunca un número inventado:
  - `fcf_per_share_base <= 0` → `no_aplica` ("sin flujo positivo que proyectar");
  - `wacc <= terminal_growth` → `no_aplica`;
  - el precio queda por debajo del valor con g = límite inferior o por encima con g = límite superior →
    `fuera_de_rango`, con el lado ("exige menos de −20%" / "más de +60%").
- Devuelve: g\*, estado, iteraciones, el valor reconstruido (que debe igualar el precio dentro de la tolerancia) y los
  supuestos usados.

Y la lectura (sin texto final de informe, solo la clasificación):

`classify_implied_growth(g_star, achieved_growth, band_pp, base_rate=None) -> banda`
- Bandas de F3_DISENO §2.2: `barata` (g\* < logrado − banda), `en_precio` (± banda), `exigente` (> logrado + banda),
  `muy_exigente` (si `base_rate` indica que muy pocas comparables lo sostienen 10 años; deja el umbral en config y el
  parámetro opcional: las tasas base reales las aporta la fase 3).
- `achieved_growth` puede ser `None` → banda `sin_contraste`.

### T2. `backend/lib/bank_implied.py`
- `implied_rote(p_tbv, ke, g)` = P/TBV × (Ke − g) + g. Y `implied_roe(p_b, ke, g)` análogo.
- Validaciones: `ke <= g` → `no_aplica`; P/TBV ≤ 0 → `no_aplica`.
- `rote_sensitivity(p_tbv, ke, g, deltas_pp)`: el P/TBV justificado para ROTE ± deltas (para la frase "con un ROTE del
  12% se justificaría 1.1x").
- **Coherencia con lo existente:** `implied_rote` aplicado al P/TBV justificado que calcula hoy el motor debe
  devolver el ROTE que usó el motor (inversa exacta). Test de ida y vuelta con los datos de JPM, BAC y BCS del panel.

### T3. Tests (sin red, rápidos)
- **Ida y vuelta con el DCF directo:** para 5 tickers del panel con DCF `ok` (p. ej. KO, JNJ, XOM, TXRH si estuviera,
  AAPL), calcula el valor con el DCF directo del motor para un g dado; usa ese valor como "precio" en
  `implied_growth`; debe recuperar g dentro de la tolerancia. Esto prueba que ambos modelos son el mismo.
- **Contraste independiente:** un cálculo aparte, escrito de forma distinta (descuento año a año explícito, sin reusar
  funciones del motor), para 3 casos a mano: debe coincidir con `implied_growth`.
- Casos límite: FCF ≤ 0, WACC ≤ g, fuera de rango por arriba y por abajo, precio exactamente en un límite.
- Ejemplo BCS de F3_DISENO §3: P/TBV 0.81, Ke 11.0%, g 2.5% → ROTE implícito ≈ 9.4%.
- `test_config_literals.py` en verde (sin literales).
- **Ningún golden cambia** y la suite entera sigue en verde: lo demuestras con la salida del comando.

### T4. Informe de muestra (solo documentación)
`docs/fiabilidad/F3PREP_MUESTRA.md`: g\* calculado para los tickers del panel con FCF > 0 (desde los fixtures
`panel`, en replay), junto al CAGR de FCF por acción a 3 años que ya calcula el motor, y la banda resultante. Para
los bancos del panel, el ROTE implícito frente al ROTE del motor. Es una **muestra para el planificador**, no un
cambio del motor: incluye PLTR, NVDA, CAT, AAPL, TSM y los bancos, y señala cuáles saldrían en `fuera_de_rango`.

### T5. Cierre → **PUNTO DE PARADA**
- Commits pequeños con prefijo `F3prep:` en `fiabilidad/f3-prep`. **Sin push, sin merge.**
- Entrada en `docs/fiabilidad/BITACORA.md` **del repo principal**: no la edites desde el worktree. Escribe tu entrada
  en `docs/fiabilidad/F3PREP_REGISTRO.md` de tu rama; el planificador la llevará a la bitácora. (Evita choques con el
  operador de la 2a, que sí edita la bitácora.)
- Presenta al usuario: la muestra de T4, la prueba de ida y vuelta y el contraste independiente. **Detente.**

## 3. Reglas que no se rompen

- **Nada conectado al motor**: si para algo crees que hace falta tocar un módulo existente, detente y pregunta.
- Ningún literal numérico en las funciones (config + schema). Ningún golden cambia.
- No edites archivos que el operador de la 2a pueda estar tocando (bitácora, `main.py`, `yf_adapter.py`,
  `currency.py`, `validate.py`, `tests/fixtures/`, `tests/golden/`).
- Toda afirmación de "hecho" o "pasa" va con el comando que la demuestra y su salida.
- No pushees ni hagas merge.

## 4. Definición de terminado

- [ ] `reverse_dcf.py` y `bank_implied.py` con estados explícitos y parámetros en config.
- [ ] Ida y vuelta con el DCF directo en 5 tickers y contraste independiente en 3 casos: dentro de tolerancia.
- [ ] Suite en verde, 0 golden cambiados, `test_config_literals` en verde.
- [ ] `F3PREP_MUESTRA.md` con g\* y bandas del panel y el ROTE implícito de los bancos.
- [ ] `F3PREP_REGISTRO.md` con la entrada de la sesión; rama sin push.
