import Link from "next/link";

export default function VariantNotFound() {
  return (
    <section className="state state-info" data-testid="not-found-state">
      <h1 className="state-title">Producto no encontrado</h1>
      <p>No hay ningún producto publicado con ese SKU.</p>
      <p>
        <Link href="/catalog">Volver al catálogo</Link>
      </p>
    </section>
  );
}
