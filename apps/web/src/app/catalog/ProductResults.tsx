import type { PublicProduct, PublicVariant } from "@hardware-store/api-client";
import Link from "next/link";

import { ProductCard } from "../../components/ProductCard";
import { ApiErrorState, StateMessage } from "../../components/StateMessage";
import { getProduct, listProducts } from "../../lib/catalog";
import { catalogHref, hasFilters, type CatalogParams } from "../../lib/search-params";

function activeFilterLabels(params: CatalogParams, products: readonly PublicProduct[]) {
  const labels: { key: "q" | "category" | "brand"; text: string }[] = [];
  if (params.q) labels.push({ key: "q", text: `Nombre contiene “${params.q}”` });
  if (params.category) {
    const name = products.find((p) => p.category?.id === params.category)?.category?.name;
    labels.push({ key: "category", text: `Categoría: ${name ?? "seleccionada"}` });
  }
  if (params.brand) {
    const name = products.find((p) => p.brand?.id === params.brand)?.brand?.name;
    labels.push({ key: "brand", text: `Marca: ${name ?? "seleccionada"}` });
  }
  return labels;
}

export async function ProductResults({ params }: { params: CatalogParams }) {
  const result = await listProducts(params);
  if (!result.ok) {
    return (
      <ApiErrorState
        title="No pudimos cargar los productos"
        message={result.failure.envelope.message}
        requestId={result.failure.envelope.request_id}
        action={{ href: "/catalog", label: "Restablecer filtros" }}
      />
    );
  }

  const { results, next_cursor, previous_cursor } = result.data;
  // The list endpoint has no SKUs; published variants come from each product's detail.
  const variantsByProduct = await Promise.all(
    results.map(async (product): Promise<readonly PublicVariant[] | null> => {
      const detail = await getProduct(product.id);
      return detail.ok ? detail.data.variants : null;
    }),
  );
  const filters = activeFilterLabels(params, results);

  return (
    <>
      {filters.length > 0 ? (
        <div className="active-filters" aria-label="Filtros activos" role="group">
          <span>Filtros activos:</span>
          <ul>
            {filters.map((filter) => (
              <li key={filter.key}>
                {filter.text}{" "}
                <Link href={catalogHref({ ...params, cursor: "", [filter.key]: "" })} aria-label={`Quitar filtro ${filter.text}`}>
                  Quitar
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {results.length === 0 ? (
        <StateMessage
          title="No encontramos productos"
          testId="empty-state"
          action={hasFilters(params) ? { href: "/catalog", label: "Restablecer filtros" } : undefined}
        >
          <p>{hasFilters(params) ? "Ningún producto coincide con los filtros." : "Todavía no hay productos publicados."}</p>
        </StateMessage>
      ) : (
        <>
          <p className="muted" role="status">
            Mostrando {results.length} {results.length === 1 ? "producto" : "productos"}.
          </p>
          <ul className="card-grid" data-testid="product-list">
            {results.map((product, index) => (
              <li key={product.id}>
                <ProductCard product={product} variants={variantsByProduct[index] ?? null} />
              </li>
            ))}
          </ul>
        </>
      )}

      {previous_cursor || next_cursor ? (
        <nav className="pagination" aria-label="Paginación">
          {previous_cursor ? (
            <Link href={catalogHref({ ...params, cursor: previous_cursor })} rel="prev" data-testid="page-previous">
              Anterior
            </Link>
          ) : (
            <span aria-hidden="true" />
          )}
          {next_cursor ? (
            <Link href={catalogHref({ ...params, cursor: next_cursor })} rel="next" data-testid="page-next">
              Siguiente
            </Link>
          ) : null}
        </nav>
      ) : null}
    </>
  );
}
