import { test, expect, type APIRequestContext } from "@playwright/test";

// Revisión del PM: ningún motivo que llegue a la interfaz o a una respuesta de la API lleva rutas del sistema de
// archivos. Recorre todas las respuestas de la API del replay para los 8 tickers (análisis, precios, segmentos,
// rivales hasta que terminan, escenario, búsqueda y tendencias) y busca, en cada cadena ya decodificada, rutas de
// macOS/Linux («/Users/», «/home/», «/private/», «/tmp/») o de Windows («C:\…», «\\servidor»). Una barra invertida
// suelta en un texto («CREC. \ WACC») no es una ruta.
const TICKERS = ["AAPL", "JPM", "O", "NEE", "XOM", "PLTR", "RIVN", "BCS"];
const API = `http://localhost:${process.env.REPLAY_PORT || 8767}`;
const PATHS = /\/Users\/|\/home\/|\/private\/|\/tmp\/|\b[A-Za-z]:\\\S|\\\\[A-Za-z]/;

function strings(v: unknown, out: string[] = []): string[] {
  if (typeof v === "string") out.push(v);
  else if (Array.isArray(v)) v.forEach((x) => strings(x, out));
  else if (v && typeof v === "object") Object.values(v).forEach((x) => strings(x, out));
  return out;
}

async function body(req: APIRequestContext, url: string, init?: { data?: unknown }): Promise<string> {
  const r = init ? await req.post(url, { data: init.data, timeout: 120_000 }) : await req.get(url, { timeout: 120_000 });
  return await r.text();
}

test("las respuestas de la API del replay no llevan rutas locales", async ({ request }, info) => {
  test.skip(info.project.name !== "desktop", "una vez basta");
  test.setTimeout(600_000);
  const leaks: string[] = [];
  const seen: string[] = [];
  const check = (where: string, txt: string) => {
    seen.push(where);
    let all: string[];
    try { all = strings(JSON.parse(txt)); } catch { all = [txt]; }
    for (const s of all) {
      const m = s.match(PATHS);
      if (m) leaks.push(`${where}: …${s.slice(Math.max(0, m.index! - 60), m.index! + 60)}…`);
    }
  };
  check("trending", await body(request, `${API}/api/v2/trending`));
  // V6b: las mini-gráficas solo admiten valores del universo del cintillo (RIVN no lo es: 422, también revisado)
  const strip = TICKERS.filter((t) => t !== "RIVN");
  for (const p of ["1D", "1S", "1M", "6M"]) check(`sparklines/${p}`, await body(request, `${API}/api/v2/sparklines?symbols=${strip.join(",")}&period=${p}`));
  check("sparklines/422", await body(request, `${API}/api/v2/sparklines?symbols=${TICKERS.join(",")}&period=1D`));
  for (const t of TICKERS) {
    const a = await body(request, `${API}/api/analysis/${t}`);
    check(`analysis/${t}`, a);
    const an = JSON.parse(a);
    check(`prices/${t}`, await body(request, `${API}/api/v2/prices/${t}?sector=${encodeURIComponent(an.profile?.sector ?? "")}`));
    check(`segments/${t}`, await body(request, `${API}/api/v2/segments/${t}`));
    check(`search/${t}`, await body(request, `${API}/api/search?q=${t}`));
    if (an.scenario_inputs) check(`scenario/${t}`, await body(request, `${API}/api/v2/scenario`, { data: { inputs: an.scenario_inputs, assumptions: {} } }));
    for (let i = 0; i < 40; i++) {                                  // rivales: hasta que el replay los termina
      const p = await body(request, `${API}/api/v2/peers/${t}`);
      if (JSON.parse(p).status !== "calculando") { check(`peers/${t}`, p); break; }
      await new Promise((r) => setTimeout(r, 1500));
    }
  }
  check("analysis/ZZZZ (sin fixtures)", await body(request, `${API}/api/analysis/ZZZZ`));
  console.log(`respuestas revisadas: ${seen.length}`);
  expect(seen.filter((w) => w.startsWith("peers/")).length).toBe(TICKERS.length);   // los rivales terminaron
  expect(leaks).toEqual([]);
});
