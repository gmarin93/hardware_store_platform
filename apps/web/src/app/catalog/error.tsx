"use client";

import Link from "next/link";

export default function CatalogError({ retry }: { error: unknown; retry: () => void }) {
  return (
    <section className="state state-error" role="alert" data-testid="error-state">
      <h1 className="state-title">No pudimos cargar el catálogo</h1>
      <p>El servicio de catálogo no respondió. Intente de nuevo en unos minutos.</p>
      <p className="actions">
        <button type="button" className="button" onClick={() => retry()}>
          Reintentar
        </button>{" "}
        <Link href="/catalog">Volver al catálogo</Link>
      </p>
    </section>
  );
}
