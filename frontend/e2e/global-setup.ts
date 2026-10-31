// Revisión V6 (encargo del PM): cada pasada empieza con el replay como recién arrancado (POST /__replay/reset: cola
// compartida, rivales, tendencias con su cupo propio de precalentado y sin fallo activo). Así una pasada no depende de
// las horas de pruebas que el replay lleve encima (la tarjeta sin análisis de la portada, por ejemplo).
// V1_LIVE=1 (cierre de la v4): V1 contra un backend real (tools/load_server.py, fuentes reales), que no es un replay
// y no tiene nada que reiniciar.
export default async function globalSetup(): Promise<void> {
  if (process.env.V1_LIVE === "1") return;
  const port = Number(process.env.REPLAY_PORT || 8767);
  const res = await fetch(`http://localhost:${port}/__replay/reset`, { method: "POST" });
  if (!res.ok) throw new Error(`no se pudo reiniciar el replay (${res.status}): ¿es un replay de antes de la revisión V6?`);
}
