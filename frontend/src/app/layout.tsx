import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Manrope } from "next/font/google";
import "./globals.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist", display: "swap" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono", display: "swap" });
// Marca: el logotipo «Finanzer» en Manrope 700 (SIL OFL 1.1). next/font la sirve desde el propio sitio
// (/_next/static/media): la CSP (font-src 'self') no cambia y no hay petición a Google en el navegador.
const manrope = Manrope({ subsets: ["latin"], weight: "700", variable: "--font-brand", display: "swap" });

// La marca en la pestaña, en iOS y al instalarla: favicon.ico (16 y 32 dibujados píxel a píxel, app/favicon.ico),
// PNG de 32, apple-touch de 180 y el manifiesto (iconos de 192 y 512). Activos generados por marca/exportar.mjs.
export const metadata: Metadata = {
  title: "Finanzer",
  description: "Análisis fundamental inteligente",
  icons: {
    icon: [{ url: "/brand/icon-32.png", type: "image/png", sizes: "32x32" }],   // /favicon.ico lo añade Next (app/favicon.ico)
    apple: [{ url: "/brand/apple-touch-icon.png", sizes: "180x180" }],
  },
  manifest: "/manifest.webmanifest",
};

// theme-color: el verde de la marca
export const viewport: Viewport = { themeColor: "#94E8A5" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // suppressHydrationWarning: el script de /v2 pone el tema en <html> antes de pintar (app/v2/layout.tsx); la web
    // actual no lo usa.
    <html lang="es" suppressHydrationWarning>
      <body className={`${geist.variable} ${geistMono.variable} ${manrope.variable} font-sans`}>{children}</body>
    </html>
  );
}
