"use client";
import dynamic from "next/dynamic";

// Cada página carga solo su código: la portada no descarga la historia (gráficas de Lightweight Charts) ni al revés.
// La elección se hace en el cliente para que el export enlace en cada HTML solo el fragmento que pinta.
const StoryPageClient = dynamic(() => import("./StoryPageClient"));
const HomeClient = dynamic(() => import("@/v2/home/HomeClient"));

export default function V2Entry({ home }: { home: boolean }) {
  return home ? <HomeClient /> : <StoryPageClient />;
}
