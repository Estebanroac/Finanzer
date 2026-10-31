"use client";
import TopBar from "@/v2/components/TopBar";
import SearchBox from "@/v2/components/SearchBox";
import TickerStrip from "./TickerStrip";
import { TRUST_CARDS } from "./trust";
import { readTheme, useTheme, writeTheme } from "@/v2/lib/theme";
import "./home.css";
import { crossfade } from "@/v2/lib/motion";

/** Portada de /v2 (spec §3.5, maqueta 5; P8): buscador, cintillo de la sesión con mini-gráficas y el motor, y tres
 *  tarjetas de confianza. */
export default function HomeClient() {
  // El mismo almacén de tema que la historia (v4: guardado o del sistema, sin parpadeo por el script del layout).
  const theme = useTheme();
  // v4.1 (movimiento): el cambio de modo, con un fundido cruzado breve (no de golpe)
  const toggle = () => crossfade(() => writeTheme((theme ?? readTheme()) === "dark" ? "light" : "dark"), "theme");

  return (
    <div className="fz2 home" data-theme={theme ?? undefined}>
      <TopBar symbol={null} theme={theme ?? "light"} onToggleTheme={toggle} search={false} />
      <main>
        <div className="wrap">
          <section className="home-hero" aria-labelledby="home-title">
            <h1 id="home-title">Entiende una empresa antes de invertir</h1>
            <p className="lead">Calidad del negocio, precio y riesgos, con datos oficiales y en lenguaje claro.</p>
            <SearchBox hero placeholder="Buscar empresa o ticker… (Apple, AAPL, Coca-Cola)" shortPlaceholder="Empresa o ticker" />
          </section>
        </div>
        {/* P8: el cintillo ocupa todo el ancho; sus filtros y su línea de contexto van centrados en la columna. */}
        <TickerStrip />
        <div className="wrap">
          <section aria-label="Cómo trabaja Finanzer">
            <ul className="trust" data-sym-row>
              {TRUST_CARDS.map((c) => (
                <li key={c.title} className="trust-card surface"><h2>{c.title}</h2><p className="muted">{c.text}</p></li>
              ))}
            </ul>
          </section>
          <p className="disclaimer muted">Finanzer no es asesoría financiera.</p>
        </div>
      </main>
    </div>
  );
}
