// Anonymous, cacheable catalog reads (no cookies are ever forwarded).
import type {
  PaginatedPublicProductList,
  PublicProductDetail,
  PublicVariantDetail,
} from "@hardware-store/api-client";

import { publicApi } from "./api/server";
import { settle, type Result } from "./result";
import type { CatalogParams } from "./search-params";

export const CATALOG_PAGE_SIZE = 12;

export function listProducts(params: CatalogParams): Promise<Result<PaginatedPublicProductList>> {
  const query: Record<string, string | number> = { page_size: CATALOG_PAGE_SIZE };
  if (params.q) query.q = params.q;
  if (params.category) query.category = params.category;
  if (params.brand) query.brand = params.brand;
  if (params.cursor) query.cursor = params.cursor;
  return settle(() => publicApi().GET("/api/v1/catalog/products", { params: { query } }));
}

export function getProduct(productId: string): Promise<Result<PublicProductDetail>> {
  return settle(() =>
    publicApi().GET("/api/v1/catalog/products/{product_id}", { params: { path: { product_id: productId } } }),
  );
}

/** Exact SKU lookup: 0 or 1 result (`null` when there is none). */
export async function getVariantBySku(sku: string): Promise<Result<PublicVariantDetail | null>> {
  const result = await settle(() => publicApi().GET("/api/v1/catalog/variants", { params: { query: { sku } } }));
  if (!result.ok) return result;
  return { ok: true, data: result.data.results[0] ?? null };
}
