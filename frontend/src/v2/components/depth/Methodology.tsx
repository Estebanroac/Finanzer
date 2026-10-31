/** Metodología al pie de cada página de profundidad: siempre visible, en letra más pequeña. */
export default function Methodology({ items }: { items: Array<{ label: string; text: string | null | undefined }> }) {
  const shown = items.filter((i): i is { label: string; text: string } => !!i.text && !!i.text.trim());
  if (!shown.length) return null;
  return (
    <section className="methodology" aria-labelledby="metodologia-t" id="metodologia">
      <h3 id="metodologia-t">Metodología</h3>
      <dl>
        {shown.map((i) => (
          <div key={i.label}><dt>{i.label}</dt><dd>{i.text}</dd></div>
        ))}
      </dl>
    </section>
  );
}
