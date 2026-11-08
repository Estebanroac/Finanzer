# Prueba hacia atrás del motor · segundo corte (5-nov-2024) · pre-registro (7-nov-2026)

Encargo del usuario (7-nov-2026): «segundo corte al 5-nov-2024 con el mismo pre-registro». Manda
`PRUEBA_HACIA_ATRAS_2025_PREREGISTRO.md` (c65d36cd) **punto por punto**; este documento solo fija lo que cambia por la
fecha y lo que se añade como información. Se escribe y se sube a git **antes de capturar ningún dato al corte, correr
el motor o mirar un rendimiento**. Nada se cambia después de ver resultados; lo que no se pueda medir, «sin dato».

## 1. Fecha de corte: 5-nov-2024, después del cierre de Nueva York

- Reloj congelado en 2024-11-05 18:00 (America/New_York). Todas las reglas de §1 del pre-registro de 2025, con
  2024-11-05 donde dice 2025-11-05 (EDGAR por `filed` ≤ corte, Yahoo cortado y pedido con fechas explícitas, Finnhub
  sin bloque actual, consenso y noticias sin dato, pares reconstruidos con EDGAR ≤ corte y el cierre del corte).
- **Damodaran**: industrias, betas, primas país y lista de empresas de **enero de 2024** (archivo de NYU Stern:
  enlace «1/24», archivos con sufijo 23); par Rf–ERP de **noviembre de 2024** (ERPbymonth.xlsx, fila 2024-11-01).
- **Universo** (`tests/hacia_atras/universo_2024-11-05.tsv`, 543): el S&P 500 de la revisión **1254993211** de
  Wikipedia (2-nov-2024, 503 valores; su tabla de cambios no trae ninguno efectivo entre el 2 y el 5-nov) + los 40 ADR
  de `market.universe.adrs` (sector GICS de `adr_sectors`). Símbolos de esa fecha; los datos se piden con el de hoy si
  cambió (BK→BNY, FI→FISV, MMC→MRSH, SQ→XYZ, EQR→VMRK; PARA: la sucesora, con su canje).

## 2. Versiones del motor (mismos datos congelados)

- **A** = `96d781ec`, **B** = `450cb5fc` (herramientas de `e61a513a`), **A14** = `023644f0` (información): las mismas
  de 2025, para que la regla de decisión se aplique igual.
- Información, no decide (nueva): **C** = `f7351511` (rama `fiabilidad/f16-precio-l1`: precio con la regla L1 de
  beneficio normalizado, una sola alerta roja de valoración extrema, consistencia en lugar de confianza). Su
  referencia L1 (`config/precio_l1.toml`) se construye al corte con el propio motor C sobre el universo de 2024, como
  en 2025.

## 3. Muestra

- Las 110 (las mismas; todas están en el universo de 2024 con sus símbolos de esa fecha).
- Control: 300 del universo de 2024 sin las 110, mismo algoritmo y misma semilla **20261106**. Reparto: Com. 9,
  Cons. disc. 32, Cons. básico 21, Energía 12, Financiero 52, Salud 39, Industria 47, Tecnología 45, Materiales 14,
  Inmobiliario 14, Utilities 15. **Declarado**: 229 de las 300 coinciden con el control de 2025 (mismo índice y misma
  semilla); la prueba es fuera de muestra **en el tiempo** (otra fecha, otros datos, otros 12 meses), no en las
  empresas. Lista en `universo_2024-11-05.tsv` (columna `grupo`). **Decide el control.**

## 4–7. Etiquetas, líneas base, resultados y métricas

Como en 2025 (§4–§7), con estas fechas:

- Resultados reales: del **5-nov-2024 al 5-may-2025 y al 5-nov-2025**; fundamentales de los 2 trimestres siguientes
  presentados ≤ 2025-11-05; eventos en 12 meses hasta el 5-nov-2025.
- L1 y L2 con el universo de 2024 y datos ≤ 2024-11-05.
- Etiquetas de C: precio `verdict.price_level` (tres niveles: atractivo = barata, exigente = cara); alerta roja
  `alerts.red_flags`; consistencia `verdict.consistency` (consistente / mixta).

## 8. Regla de decisión

La de 2025 para A frente a L1 y L2 (§7 a–c y §8). La decisión de 2025 (precio = L1) ya se aplicó; este corte
**confirma o no** fuera de muestra. Para C, sin regla automática: se informan, y decide el usuario,

- **C1** (a) con la etiqueta de C: D(C) frente a D(L1) y D(L2), con su intervalo.
- **C2** la alerta de valoración extrema: frecuencia de caída máxima ≥ 40 % en 12 meses con alerta frente a sin
  alerta (la cifra que cita la alerta: 34,7 % frente a 14,9 % en 2025), y el criterio (c) con ella.
- **C3** acierto de dirección por consistencia (consistente frente a mixta), con n.

## 9. Entregables

`archivo-historico/evidencias-de-pruebas/hacia_atras_2024-11-05/`: `empresas_410.csv`, métricas, datos congelados,
registro de accesos no grabados; informe en `informes-pdf/`.
