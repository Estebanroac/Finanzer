# F13 · Paso 9: el flujo del DCF y la intensidad inversora (5-nov-2026)

Patrón 2 de la revisión de 110 empresas: «cada empresa con una regla». El DCF directo usaba siempre el FCF − SBC, y el
inverso cambiaba al flujo de mantenimiento solo si ese FCF salía ≤ 0. Lo decidía el signo del FCF, no cuánto invierte
la empresa. META (78 % del flujo operativo en capex) y MSFT (69 %) se valoraban con un FCF hundido por la inversión;
GOOGL, AMZN y ORCL, con el de mantenimiento.

## Medida: quién invierte en expansión

Regla general (`archetype_metrics.investment_intensity` y `expansion`, `config/valuation.toml
[investment_intensity]`). Una empresa invierte en expansión si cumple las dos condiciones:

- capex de al menos **1,5 veces la D&A** en 3 ejercicios: invierte bastante más de lo que repone;
- ese capex es al menos el **60 % del flujo operativo**, en los 3 ejercicios o en el TTM.

Hace falta el TTM porque META acelera en el último año: 78 % del flujo en el TTM frente a ~50 % en tres años.

| En expansión (banco de 110, sin cíclicas, utilities, REIT ni bancos) | Fuera, y por qué |
|---|---|
| APD, ORCL, LLY, AMZN, TXN, TSLA, WMT, MSFT, META, GOOGL | VZ, T y TGT reponen lo que amortizan (capex ≈ D&A); KO y COST invierten poco frente a su flujo (12 % y 41 %); NVDA, 5 % |

## Las tres formas de elegir el flujo, medidas

Upside del DCF directo frente al precio:

| Empresa | ROIC | g del DCF | FCF − SBC de hoy | Mantenimiento | Mantenimiento con la reinversión que exige g (g ÷ ROIC) |
|---|---|---|---|---|---|
| META ★ | 26 % | 19,9 % | −97 % | **+42 %** | −67 % |
| MSFT | 26 % | 16,1 % | −67 % | 0 % | −64 % |
| LLY | 41 % | 30 % | −48 % | +37 % | −65 % |
| WMT | 17 % | 5,3 % | −79 % | −52 % | −68 % |
| TXN | 30 % | 4,5 % | −63 % | −61 % | −67 % |
| GOOGL | 24 % | 12,5 % | (FCF − SBC ≤ 0) | −24 % | −62 % |
| AMZN | 16 % | 11,7 % | (≤ 0) | −58 % | −89 % |
| ORCL | 12 % | 8,3 % | (≤ 0) | +60 % | −68 % |

Lectura:

- El flujo de mantenimiento a secas supone que la inversión de expansión para, pero el DCF sigue proyectando el
  crecimiento que esa inversión compra. Es la cota alta.
- Aplicado como flujo que puntúa (probado en esta sesión), 5 empresas se iban hacia barata (META de muy exigente a
  razonable, con fiabilidad «alta»; LLY, MSFT, GOOGL, AMZN) sin que nada en sus datos lo justifique.
- Cobrando la reinversión que exige el crecimiento, el estándar (g = tasa de reinversión × ROIC, Damodaran), todas
  siguen caras y cerca de la lectura del FCF de hoy. MSFT −64 % frente a −67 % confirma que su FCF de hoy ya es,
  aproximadamente, el flujo que financia su crecimiento.
- La versión medida usa la reinversión del crecimiento inicial en todos los años, así que infravalora a las de
  crecimiento alto. La correcta la reduce año a año al converger g al terminal; eso exige cambiar el modelo del DCF
  (`dcf_multi_stage_dynamic`).

## Qué se aplica en este paso (sin cambiar ningún veredicto)

- **La medida de la intensidad inversora** de todas las empresas (`result.investment_intensity`, con `expansion` si
  la cumple).
- **Las dos lecturas a la vista.** En expansión, el DCF directo enseña la del flujo de mantenimiento junto a la del
  FCF − SBC, que sigue siendo la que puntúa, y dice que es la cota alta. Ejemplo de META: «con el flujo de mantenimiento
  … el valor sería X por acción (+42 % frente al precio). Es la cota alta: no descuenta lo que cuesta el crecimiento que
  proyecta; puntúa la del flujo de hoy».
- **El mantenimiento del inverso, con tope en el capex real** (nota del revisor), como el del directo
  (`maintenance_fcf`): flujo operativo − min(D&A, capex) − SBC. En el banco no cambia ninguna lectura, porque el tope
  solo actúa si el capex está por debajo de la D&A.

## Decisión pendiente del usuario

Qué flujo puntúa en el DCF de una empresa en expansión:

| Opción | Efecto en el banco de 110 |
|---|---|
| (a) el de mantenimiento | 5 bandas hacia barata (META muy exigente → razonable); ignora el coste del crecimiento |
| (b) **(recomendada)** el que financia el crecimiento: NOPAT × (1 − g ÷ ROIC), año a año en el DCF | Coherente con el estándar, pero cambia el modelo del DCF. Medido en versión simple: todas siguen caras, cerca del FCF de hoy |
| (c) el FCF − SBC de hoy, con las dos lecturas a la vista | Lo que queda aplicado ahora; `flujo_por_intensidad` sigue señalando LLY, META, MSFT y WMT |

Tabla y corridas: `archivo-historico/evidencias-de-pruebas/f13_banco110_2026-11-05/paso9_vs_paso8.md` y `paso9/`.

## Golden

Todos los análisis llevan el campo nuevo `investment_intensity`, así que se regeneran todos los golden (local, panel,
forzados). Cambios de fondo solo en las tres del panel en expansión: **MSFT**, **TSM** y **NVO**. Tienen
`dcf.expansion` y la frase de la cota alta en los parámetros del DCF; MSFT dice «el valor sería 490,55 $ por acción
(−8 % frente al precio)», frente al −67 % que puntúa. El PDF v2 de esas tres gana una página. Ningún veredicto cambia.

Tests: `tests/test_f13_paso9.py` (5). Suite: 6669 passed.
