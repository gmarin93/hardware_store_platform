import type { Metadata } from "next";
import Form from "next/form";
import Link from "next/link";
import { Suspense } from "react";

import { LoadingState } from "../../components/StateMessage";
import { hasFilters, parseCatalogParams } from "../../lib/search-params";
import { ProductResults } from "./ProductResults";

export const metadata: Metadata = { title: "Catálogo" };

export default async function CatalogPage({ searchParams }: PageProps<"/catalog">) {
  const params = parseCatalogParams(await searchParams);
  return (
    <>
      <h1>Catálogo</h1>
      <Form action="/catalog" className="filters" role="search" aria-label="Buscar en el catálogo">
        <div className="field field-inline">
          <label htmlFor="catalog-q">Buscar por nombre</label>
          <input id="catalog-q" name="q" type="search" defaultValue={params.q} maxLength={100} />
        </div>
        {params.category ? <input type="hidden" name="category" value={params.category} /> : null}
        {params.brand ? <input type="hidden" name="brand" value={params.brand} /> : null}
        <button type="submit" className="button">
          Buscar
        </button>
        {hasFilters(params) ? (
          <Link href="/catalog" className="reset-link" data-testid="reset-filters">
            Restablecer filtros
          </Link>
        ) : null}
      </Form>
      <Suspense
        key={`${params.q}|${params.category}|${params.brand}|${params.cursor}`}
        fallback={<LoadingState label="Cargando productos…" />}
      >
        <ProductResults params={params} />
      </Suspense>
    </>
  );
}
