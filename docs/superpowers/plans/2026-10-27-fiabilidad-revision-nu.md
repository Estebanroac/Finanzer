# Fiabilidad · Revisión externa del informe de NU (27-oct-2026) — Plan F9

> El usuario trajo una revisión del PDF de NU (Nu Holdings) generado con el motor nuevo (rama `rediseno/v4-f8`).
> Texto completo: `docs/fiabilidad/revision-nu-2026-10-27.md`. Veredicto del revisor: las correcciones F8 funcionan
> (piso de Ke, sensibilidad ±1 pp, contracción, umbral 85, referencia regional, honestidad de datos), pero NU, un banco
> de mercado emergente de hipercrecimiento, destapa huecos nuevos. Nota ≈ 70/100.

## Principios (los de F8)
Verificar cada hallazgo con NU en vivo antes de corregir · reglas generales en config con test, nada por ticker ·
presupuesto 0 (Damodaran `ctryprem`, EDGAR/XBRL, FRED/Tesoro, FDIC) · si un dato no existe gratis y fiable, «sin dato»
declarado · cambios de veredicto en `GOLDEN_DIFF_F9.md` con causa · re-correr los 26 de la auditoría + NU al cerrar.

## Hallazgos y reparto

| # | Hallazgo | Qué se hace | Quién |
|---|---|---|---|
| R1 | Sin prima de riesgo país (cambia el veredicto) | Ke = Rf + β·ERP + λ·CRP, CRP de Damodaran ponderada por **dónde opera** (ingresos por geografía del XBRL; si no hay, país de la sede operativa declarada en el 20-F/10-K, nunca el domicilio legal). Tabla en config con fecha; revisión semestral. El piso de Ke se aplica después, con la CRP incluida | E2a |
| R1b | Gordon de una etapa en un banco que crece el valor en libros > 20 % | P/B justificado en dos etapas (crecimiento alto que converge a g terminal en N años, en config) cuando el crecimiento del valor en libros supera el umbral; declarado | E2a |
| R2 | «Perfil defensivo, beta 0,40» como fortaleza con volatilidad 46 % | Comprobar por qué la beta es 0,40 (¿R² bajo?, ¿bottom-up de bancos EE. UU.?). La fortaleza solo si la beta es fiable **y** la volatilidad no es alta frente al mercado; nunca contradice la sección de mercado | E2a |
| R3 | Contradicciones internas (P/B 5,34 vs 4,55; CAGR 52,3 vs 48,8; crecimiento 28,5 vs 37,0; TTM < FY; industria; EV/EBITDA «no aplica» con columna de industria) | Una sola verdad por cifra en todo el informe (web y PDF): misma fuente, mismo periodo, etiqueta del periodo visible (TTM/FY). Test de coherencia que recorre el informe y falla si una misma métrica aparece con dos valores. Etiqueta de industria única. «No aplica» vacía también la columna de industria | Independientes |
| R4 | Margen neto de banco sobre ingresos brutos comparado con netos | En bancos, el margen neto sobre «ingresos» no puntúa (definiciones no comparables) | E2a |
| R5 | Plantilla en bancos: «cobertura de intereses 0,77x críticamente baja» | La cobertura de intereses no aplica a bancos ni aseguradoras (ni puntúa ni genera riesgo); revisar el resto de frases de plantilla con JPM, BAC, NU, CB | E2a |
| R6 | Falta el riesgo de crédito; «0 riesgos»; «capitalización 16 %» | Métricas de crédito con fuentes gratuitas: XBRL (US GAAP y `ifrs-full`: provisiones, deterioro, cartera) y FDIC para bancos de EE. UU. si es viable; si no hay dato, «riesgo de crédito no medido» declarado. Un banco nunca muestra «0 riesgos» sin haber medido el crédito. «Capitalización» pasa a llamarse «patrimonio / activos (no es capital regulatorio)» | Independientes |
| R7 | Menores: Rf 5,29 % vs 5,00 %; «posible cíclica» por desaceleración de hipercrecimiento; estabilidad del ROE penaliza pasar de pérdidas a ganancias | Verificar serie y fecha de Rf (y que Rf y ERP sean de la misma fecha); la marca cíclica exige caídas, no desaceleración; la estabilidad del ROE excluye la transición pérdidas → ganancias (o la declara aparte) | E2a |

Orden en E2a: R1 → R1b → R2 → R5 → R4 → R7. Independientes: R3 → R6. Ramas desde `rediseno/v4-f8` tras la fusión de
P3: `fiabilidad/f9-motor` (E2a) y `fiabilidad/f9-coherencia` (independientes). Después se fusionan en `rediseno/v4-f8`
y entonces se hace la pasada final oficial.
