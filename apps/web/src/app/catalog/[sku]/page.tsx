import type { PublicVariant } from "@hardware-store/api-client";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { cache } from "react";

import { AttributeList } from "../../../components/AttributeList";
import { PendingLink } from "../../../components/PendingLink";
import { ProductImage } from "../../../components/ProductImage";
import { getProduct, getVariantBySku } from "../../../lib/catalog";
import { formatDecimal, unitLabel } from "../../../lib/format";
import { catalogHref } from "../../../lib/search-params";

// Anonymous: no cookies are read or forwarded. Rendered per request; the API
// responses come from the Next.js data cache (revalidate window in lib/api/server).
const MAX_SKU_LENGTH = 64;

const loadVariant = cache(async (rawSku: string) => {
  const sku = rawSku.trim();
  if (sku.length === 0 || sku.length > MAX_SKU_LENGTH) return null;
  const result = await getVariantBySku(sku);
  if (!result.ok) {
    if (result.failure.status === 400 || result.failure.status === 404) return null;
    // Thrown (not rendered) so a transient failure is never cached as a page.
    throw new Error(`Catalog lookup failed (${result.failure.envelope.code})`);
  }
  return result.data;
});

function decodeSku(raw: string): string {
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

export async function generateMetadata({ params }: PageProps<"/catalog/[sku]">): Promise<Metadata> {
  const variant = await loadVariant(decodeSku((await params).sku));
  return { title: variant ? `${variant.name} (SKU ${variant.sku})` : "Producto no encontrado" };
}

export default async function VariantPage({ params }: PageProps<"/catalog/[sku]">) {
  const variant = await loadVariant(decodeSku((await params).sku));
  if (!variant) notFound();

  const productResult = await getProduct(variant.product.id);
  const product = productResult.ok ? productResult.data : null;
  const siblings: PublicVariant[] = product ? product.variants.filter((item) => item.id !== variant.id) : [];
  const media = variant.media.length > 0 ? variant.media : (product?.media ?? []);

  return (
    <article className="detail" data-testid="variant-detail">
      <nav aria-label="Ruta de navegación" className="breadcrumbs">
        <ol>
          <li>
            <Link href="/">Inicio</Link>
          </li>
          <li>
            <Link href="/catalog">Catálogo</Link>
          </li>
          <li aria-current="page">{variant.name}</li>
        </ol>
      </nav>

      <h1>{variant.name}</h1>
      <p className="muted">
        Producto: <strong>{variant.product.name}</strong>
      </p>

      <div className="detail-grid">
        <div className="detail-media">
          {media.length === 0 ? (
            <ProductImage src={null} alt={variant.name} className="detail-image" />
          ) : (
            media.map((item) => (
              <ProductImage key={item.id} src={item.url} alt={item.alt_text || variant.name} className="detail-image" />
            ))
          )}
        </div>

        <div>
          <dl className="facts" data-testid="variant-facts">
            <div>
              <dt>SKU</dt>
              <dd data-testid="variant-sku">{variant.sku}</dd>
            </div>
            {variant.product.brand ? (
              <div>
                <dt>Marca</dt>
                <dd>
                  <Link href={catalogHref({ brand: variant.product.brand.id })}>{variant.product.brand.name}</Link>
                </dd>
              </div>
            ) : null}
            {variant.product.category ? (
              <div>
                <dt>Categoría</dt>
                <dd>
                  <Link href={catalogHref({ category: variant.product.category.id })}>
                    {variant.product.category.name}
                  </Link>
                </dd>
              </div>
            ) : null}
            <div>
              <dt>Unidad de venta</dt>
              <dd>{unitLabel(variant.sales_unit)}</dd>
            </div>
            <div>
              <dt>Cantidad mínima</dt>
              <dd>
                {formatDecimal(variant.min_quantity)} ({unitLabel(variant.sales_unit)})
              </dd>
            </div>
            <div>
              <dt>Incremento de cantidad</dt>
              <dd>
                {formatDecimal(variant.quantity_increment)} ({unitLabel(variant.sales_unit)})
              </dd>
            </div>
          </dl>

          {variant.product.description ? (
            <section aria-labelledby="descripcion">
              <h2 id="descripcion">Descripción</h2>
              <p>{variant.product.description}</p>
            </section>
          ) : null}
        </div>
      </div>

      <AttributeList attributes={variant.attributes} label="Características de esta variante" />
      {product ? <AttributeList attributes={product.attributes} label="Características del producto" /> : null}

      <section aria-labelledby="otras-variantes">
        <h2 id="otras-variantes">Otras variantes</h2>
        {!product ? (
          <p className="muted">No se pudieron cargar las demás variantes de este producto.</p>
        ) : siblings.length === 0 ? (
          <p className="muted">Este producto no tiene otras variantes publicadas.</p>
        ) : (
          <ul className="variant-links">
            {siblings.map((item) => (
              <li key={item.id}>
                <PendingLink href={`/catalog/${encodeURIComponent(item.sku)}`}>
                  {item.name} <span className="sku">SKU {item.sku}</span>
                </PendingLink>
              </li>
            ))}
          </ul>
        )}
      </section>
    </article>
  );
}
