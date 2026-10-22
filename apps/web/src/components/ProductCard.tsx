import type { PublicProduct, PublicVariant } from "@hardware-store/api-client";
import Link from "next/link";

import { catalogHref } from "../lib/search-params";
import { PendingLink } from "./PendingLink";
import { ProductImage } from "./ProductImage";

interface ProductCardProps {
  product: PublicProduct;
  /** Published variants from the product detail; null when they could not be loaded. */
  variants: readonly PublicVariant[] | null;
}

export function ProductCard({ product, variants }: ProductCardProps) {
  const media = product.media[0];
  const headingId = `producto-${product.id}`;
  return (
    <article className="card" aria-labelledby={headingId} data-testid="product-card">
      <ProductImage src={media?.url} alt={media?.alt_text || product.name} className="card-image" />
      <div className="card-body">
        <h2 id={headingId} className="card-title">
          {product.name}
        </h2>
        <dl className="meta">
          {product.brand ? (
            <div>
              <dt>Marca</dt>
              <dd>
                <Link href={catalogHref({ brand: product.brand.id })} aria-label={`Filtrar por marca ${product.brand.name}`}>
                  {product.brand.name}
                </Link>
              </dd>
            </div>
          ) : null}
          {product.category ? (
            <div>
              <dt>Categoría</dt>
              <dd>
                <Link
                  href={catalogHref({ category: product.category.id })}
                  aria-label={`Filtrar por categoría ${product.category.name}`}
                >
                  {product.category.name}
                </Link>
              </dd>
            </div>
          ) : null}
        </dl>
        {product.description ? <p className="card-description">{product.description}</p> : null}
        {variants === null ? (
          <p className="muted">No se pudieron cargar las variantes de este producto.</p>
        ) : variants.length === 0 ? (
          <p className="muted">Este producto no tiene variantes publicadas.</p>
        ) : (
          <>
            <h3 className="variants-title">Variantes</h3>
            <ul className="variant-links">
              {variants.map((variant) => (
                <li key={variant.id}>
                  <PendingLink href={`/catalog/${encodeURIComponent(variant.sku)}`} data-testid="variant-link">
                    {variant.name} <span className="sku">SKU {variant.sku}</span>
                  </PendingLink>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </article>
  );
}
