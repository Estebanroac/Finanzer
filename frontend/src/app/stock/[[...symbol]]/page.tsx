import StockPageClient from "./StockPageClient";

export async function generateStaticParams() {
  return [{ symbol: [] }];
}

export default function StockPage() {
  return <StockPageClient />;
}
