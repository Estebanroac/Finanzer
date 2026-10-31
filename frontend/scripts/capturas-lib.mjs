/**
 * Compresión de capturas del rediseño (revisión del PM: el repositorio lo clonan GitHub y Render; ninguna captura
 * pesada puede llegar a `main`). WebP de 1200 px de ancho como mucho y calidad 70; si pasa de 300 KB, baja la calidad
 * (hasta 40) y, si aun así no cabe, reduce el tamaño. Una captura de página entera muy alta se reduce para no pasar del
 * límite de WebP (16 383 px de alto).
 */
import sharp from "sharp";

export const MAX_WIDTH = 1200;
export const QUALITY = 70;
export const MAX_BYTES = 300 * 1024;
const MIN_QUALITY = 40;
const WEBP_MAX_SIDE = 16383;

export async function compress(input) {
  const meta = await sharp(input).metadata();
  let width = Math.min(meta.width ?? MAX_WIDTH, MAX_WIDTH);
  const scaleH = (w) => Math.round(((meta.height ?? 0) * w) / (meta.width ?? w));
  if (scaleH(width) > WEBP_MAX_SIDE) width = Math.floor((WEBP_MAX_SIDE * (meta.width ?? 1)) / (meta.height ?? 1));
  for (;;) {
    for (let q = QUALITY; q >= MIN_QUALITY; q -= 10) {
      const out = await sharp(input).resize({ width, withoutEnlargement: true }).webp({ quality: q, effort: 5 }).toBuffer();
      if (out.length <= MAX_BYTES) return { buffer: out, width, quality: q };
      if (q - 10 < MIN_QUALITY && width <= 320) return { buffer: out, width, quality: q };
    }
    width = Math.round(width * 0.8);
  }
}
