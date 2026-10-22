// Parses /catalog search params into the API's query values. Values are passed
// through as-is (the API validates them); only shape and length are bounded.

export interface CatalogParams {
  q: string;
  category: string;
  brand: string;
  cursor: string;
}

type RawParams = Record<string, string | string[] | undefined>;

const LIMITS: Record<keyof CatalogParams, number> = { q: 100, category: 64, brand: 64, cursor: 512 };

function first(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

export function parseCatalogParams(raw: RawParams): CatalogParams {
  const pick = (key: keyof CatalogParams) => first(raw[key]).trim().slice(0, LIMITS[key]);
  return { q: pick("q"), category: pick("category"), brand: pick("brand"), cursor: pick("cursor") };
}

/** Builds a /catalog href; empty values are omitted. */
export function catalogHref(params: Partial<CatalogParams>): string {
  const search = new URLSearchParams();
  for (const key of ["q", "category", "brand", "cursor"] as const) {
    const value = params[key];
    if (value) search.set(key, value);
  }
  const query = search.toString();
  return query ? `/catalog?${query}` : "/catalog";
}

export function hasFilters(params: CatalogParams): boolean {
  return Boolean(params.q || params.category || params.brand);
}
