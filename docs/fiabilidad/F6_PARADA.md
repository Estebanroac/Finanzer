# F6 · Infraestructura: verificación y cierre (solo código, D6)

> Fase 6 del plan de fiabilidad (PLAN_FIABILIDAD §4). Rama `fiabilidad/f6-infra`, que sale de `fiabilidad/f5-contexto`
> (worktree `../finanzer_next-f3`). **Nada subido.**
> Hecha bajo la delegación del usuario (registro #29), sobre el diagnóstico de F67prep
> ([`F6_DIAGNOSTICO.md`](F6_DIAGNOSTICO.md)). D6 vigente: sin plan de pago en Render. El arranque en frío (≈ 43 s tras
> la inactividad) no se puede quitar con código y queda fuera.

## 0. Resumen

| | Antes de la fase 6 | Ahora | Objetivo del plan |
|---|---|---|---|
| 12 análisis en frío a la vez (local, en vivo, Render simulado) | 25.8–26.5 s en total; mediana 14.7–14.9 s, p95 23.6–24.0 s | **7.1–7.9 s** en total; mediana **5.1–5.6 s**, p95 **6.9–7.7 s**, 12 de 12 con EDGAR (19 s en dos corridas con la red lenta, §3) | p95 < 6 s en frío; 12 a la vez sin cola en serie |
| `/api/health` durante esa ráfaga | 12.7–13.0 s de mediana, hasta 26 s (bucle bloqueado) | **0.001 s** de mediana, máximo 0.03 s | — |
| 12 análisis en caliente a la vez | p95 0.13 s | p95 0.12–0.15 s | < 1 s |
| 12 análisis tras caducar la cotización (5 min), con los estados en caché | (se descargaba todo otra vez: como en frío) | **2.3 s** en total; mediana **1.5 s**, p95 2.2 s | — |
| Cola en serie | sí: el k-ésimo espera a los k − 1 anteriores | **no**: 4 análisis a la vez por proceso y el resto espera turno sin bloquear | sin cola en serie |
| Suite | — | 3930 passed; falla 1, las muestras forzadas del contrato, que van con los golden | — |

Lectura: con 12 a la vez, el p95 de 6.9 s queda cerca del objetivo de 6 s. Una petición sola en frío tarda 3–4 s
(diagnóstico, §1.3). El objetivo se cumple para el uso real, que es una petición o pocas a la vez. Con 12 a la vez lo
limita el semáforo de 4 análisis, que protege la memoria de Render (512 MB). La medida es local, desde una IP
residencial y sin Finnhub. En Render se mide con el deploy.

## 1. Qué se hizo (un commit por causa)

| Commit | Qué y por qué |
|---|---|
| `94ce758` | La búsqueda de Yahoo usa la sesión compartida de `yf_adapter`. En un proceso recién arrancado fallaba, porque la sesión aún no existía. |
| `6fb46c3` | **Fuera del bucle de eventos** (F6_DIAGNOSTICO §2: la causa medida de la cola). El análisis, el PDF y la búsqueda van a hilos (`run_in_threadpool`), con un semáforo de `server.max_concurrent_analyses` = 4. El proceso ocupa ≈ 190 MB y cada análisis en curso unas decenas más: 4 caben con margen en los 512 MB de Render. Test: con un análisis en curso, `/api/health` responde al instante. |
| `1b8f5ca` | **Caché de los estados de 6 h** por símbolo, aparte de la cotización (5 min). Los estados cambian cada trimestre, y 6 h es la caché de la lista de filings de EDGAR, así que unos resultados nuevos se ven como mucho con ese retraso. La moneda de los estados también se guarda. Se guarda el estado crudo y se entrega una copia; los vacíos y los errores no se guardan; LRU de 700 entradas. |
| `fafdf3b` | Los tres estados trimestrales se descargan a la vez. Antes iban uno tras otro: tres idas y vueltas a Yahoo en frío. |
| `b586299`, `a83fe4e` | **Procedencia en el anexo técnico** (lo que pide el plan). "Procedencia de los datos" cuenta los campos por fuente (estados de Yahoo, SEC EDGAR, Finnhub, perfil, derivados, regla del arquetipo, sin dato) y nombra los que no salen de los estados. El respaldo anual de EDGAR sale con el nombre del dato, no con su código. |
| `96a7e8c` | Un 8-K de resultados que llega dentro de los 70 días posteriores al corte es el comunicado del propio corte, no un "resultado pendiente". BRK-B presenta el 10-Q un día antes que el 8-K. |
| `9b7bbc4` | **Corte de doce meses con EDGAR (BRK-B)**: filas del mapa "BRK-B en base anual" y "su P/E (TTM)", movidas a esta fase en la 3. Ver §2. |

## 2. BRK-B: el corte pasa al último 10-Q

Yahoo no trae el 3T-2025 de BRK-B, así que el análisis iba con el ejercicio de diciembre de 2025: datos con 10 meses
de retraso. Ahora, sin 4 trimestres de Yahoo, el corte pasa al último trimestre presentado en EDGAR posterior al
ejercicio, con la misma regla que el corte de Yahoo: ingresos y beneficio de doce meses, más el balance de esa fecha.

- **Flujos:** los doce meses de EDGAR, calculados como ejercicio + acumulado del año − acumulado del año anterior.
- **Balance:** el trimestral de Yahoo de esa fecha, que sí existe. Así caja y deuda conservan la definición del resto del análisis. EDGAR solo completa lo que falta.
- **BPA:** el del ejercicio × beneficio de doce meses / beneficio del ejercicio. No se rehace la clase A/B, y la recompra del semestre no se recoge (se dice).
- **Normalización:** no aplica a un beneficio de doce meses las partidas inusuales del ejercicio, que son de otro periodo (se dice).
- **Solo si no pierde nada:** el corte se ensaya en una copia. Si pierde un campo que el ejercicio tenía, se queda el ejercicio y se registra el motivo. UL (6-K semestral sin deuda ni EBITDA) se queda en el ejercicio. La única excepción declarada es el resultado financiero neto (`recut_droppable`), que solo fija el signo del estado de la cobertura.

| BRK-B | Antes (FY2025) | Ahora (doce meses a 30-jun-2026) |
|---|---|---|
| Ingresos | 371.4 mil millones | 384.7 mil millones |
| Beneficio neto | 67.0 mil millones | 85.8 mil millones |
| P/E | 16.96 ("último ejercicio") | 13.24 (TTM) |
| ROE | 9.3% | 11.5% |
| Calidad / precio | 70 sólida / 35 exigente | 71 sólida / 42 exigente |
| Confianza | media | media (la fuente deja de restar por "sin TTM") |

Sin cambio de nivel. El resto del panel queda idéntico (diff de los JSON).

**Límite que queda (para la fase 7 o una decisión del usuario):** el beneficio neto GAAP de BRK-B incluye las
ganancias no realizadas de su cartera de acciones (ASC 321). Los analistas usan el "beneficio operativo" que publica
la propia Berkshire. El P/E de 13.2 está hecho con un beneficio que sube y baja con la bolsa. El problema ya existía
con el ejercicio, que también las incluía. No se arregla aquí porque es una decisión de definición, como la de los
ingresos en la fase 3: qué beneficio usa una aseguradora o un conglomerado con cartera de renta variable.

## 3. Medición antes y después (protocolo §5 del plan)

Misma corrida de 12 tickers fuera del panel (HD, PEP, COST, MCD, UNH, ORCL, LOW, MDLZ, WMT, YUM, CVS, IBM). Servidor
local en vivo con Render simulado (S1: quoteSummary 401; S2: info vacío) y SEC EDGAR activo; sin Finnhub, para que
su espaciado de prueba (1.1 s) no se mida como cola. "Antes" es `6008328`, el cierre de F5; "ahora", la rama. 12
peticiones a la vez de cada tipo, con una sonda de `/api/health` cada 0.5 s durante la ráfaga en frío. Sábado
17-oct-2026, 12:54–13:20 de Nueva York. Producción no se tocó.

| Ráfaga de 12 | Antes (1ª) | Antes (2ª) | Ahora |
|---|---|---|---|
| Frío: total / mediana / p95 | 26.5 / 14.9 / 24.0 s | 25.8 / 14.7 / 23.6 s | **7.1 / 5.1 / 6.9 s** (repetida: 7.8 / 5.2 / 7.1 s) |
| `/api/health` durante el frío: mediana / máximo | 13.0 / 26.0 s | 12.7 / 25.3 s | **0.001 / 0.03 s** |
| Caliente: p95 | 0.13 s | 0.13 s | 0.12 s |
| PDF caliente: total | 0.96 s | 0.96 s | 0.91 s |
| Frío otra vez a los 5 min 20 s (cotización caducada, estados en caché): total / mediana / p95 | — | — | **2.3 / 1.5 / 2.2 s** |

Después de los arreglos de la revisión de código (§5) se repitió la ráfaga en frío contando además cuántos análisis
traen EDGAR completo, con el código de antes (`3ef8c8f`) y el de después (`ead7808`), uno detrás de otro (13:17–13:23 de Nueva York):
7.8 s y 7.5 s en total (mediana 5.5 y 5.4 s), 12 de 12 con EDGAR y sus filings pendientes leídos en los dos. Dos
corridas anteriores (13:15 y 13:16) dieron 19 s con EDGAR completo. La diferencia es la red: la de Yahoo y la SEC
varía hasta el doble en minutos (F6_DIAGNOSTICO §1.2). Además, la SEC limita el ritmo (≤ 10 peticiones/s; el motor
usa ≤ 8.3), y 12 análisis en frío son ≈ 100 peticiones compartidas. Ese es el límite real de 12 a la vez: el código
ya no pone cola en serie.

Herramientas en la carpeta de trabajo de la sesión: `live_server.py`, que monta el servidor en vivo con
`fixture_backend.render_sim`, y `burst.py`, la ráfaga. No se versionan: son la medida, no la app. La de producción la
hace `tests/medir_concurrencia.py`, que contra finanzer.app se niega a pasar de 3 a la vez.

## 4. Revisión de código de la fase 6

Revisión independiente del diff. Arreglos en cuatro commits (prefijo F6), verificados con la suite, el panel (0 cambios de
nivel) y la medida A/B de §3:

| Hallazgo | Arreglo |
|---|---|
| 1. `SimpleCache` sin lock: con 4 análisis en hilos, "dictionary changed size during iteration" y un 404 falso posible | Lock en la caché (`2006379`); test de 4 hilos |
| 2. El presupuesto de EDGAR (3 s) se gastaba esperando el turno de otros análisis: con carga se perdía EDGAR y el resultado dependía de ella (BRK-B: P/E 13.24 o 16.96); pool de series de precios de 2 | La espera en cola no gasta presupuesto, hasta `queue_max_s` (4 s); la descarga sale del turno de parseo; el pool de series es 2 × los análisis simultáneos (`2006379`, `ead7808`) |
| 3. Tras el corte de EDGAR, el valor en libros por acción seguía siendo el del ejercicio (BRK-B 335.13 junto a un P/B del corte) | Valor en libros del patrimonio del corte: 349.37 (`0d86c00`) |
| 4. Anexo: códigos sin traducir (capex y amortizaciones anuales, `trailingEps`) y "liquidez corriente" dos veces | Nombres legibles y un dato con dos nombres internos cuenta una vez (`0d86c00`) |
| 5. Carrera en la clase de acciones con los trimestrales en paralelo (solo ruta quoteSummary) | `convert` espera a que termine `prepare_class` (`dd0ca0a`) |
| 6. Un reset de la sesión de Yahoo en otro hilo dejaba la búsqueda o la sonda de moneda con None | `_live_session` (`dd0ca0a`) |
| 7. El PDF se construía fuera del semáforo | Análisis y PDF en el mismo turno; el PDF se envía como bytes (`dd0ca0a`) |
| 8. La caché de 6 h fija un trimestral parcial no vacío de Yahoo | Se acepta y se declara (§5): volver a pedirlo a los 5 min da lo mismo (BRK-B, 3T-2025) |
| 9. El BPA aproximado del corte de EDGAR no llegaba al lector | El anexo explica el corte y el BPA aproximado, o por qué se descartó (UL) (`0d86c00`) |

## 5. Lo que no se hizo y por qué

- **Arranque en frío de Render** (≈ 43 s tras la inactividad): D6, sin plan de pago. El código no lo quita.
- **Caché persistente en disco o en un servicio externo:** el disco de Render es efímero y se pierde en cada apagado y deploy, igual que la memoria. Un servicio externo es un coste que D6 descarta. La caché de 6 h en memoria da lo mismo mientras el proceso vive.
- **PDF con 12 a la vez en Render:** el PDF es CPU (reportlab, ≈ 1.7 s en Render, F6_DIAGNOSTICO §1.3). Los hilos no lo aceleran; el semáforo evita que 12 a la vez agoten la memoria. Sigue por debajo de 10 s en frío: análisis ≈ 3.4 s + PDF ≈ 1.7 s.
- **Yahoo distinto en Render que en local** (fila del mapa): no se puede medir sin deploy. El corte coherente y el respaldo de EDGAR (2b) acotan su efecto.
- **Medida en Render:** con el deploy, que espera al usuario (`SEC_EDGAR_USER_AGENT` en Render, golden y "ok, pushea").
- **Cancelación:** un cliente que se desconecta deja su análisis en la cola del semáforo. Las esperas ocupan hilos del pool de anyio (40): con más de 40 peticiones a la vez también esperarían la búsqueda y el envío. Es una carga fuera del uso real de la app y queda anotada.
- **Trimestral parcial en caché 6 h** (hallazgo 8): Yahoo devuelve lo mismo a los 5 minutos. El corte de EDGAR (§2) cubre el caso que importa.
