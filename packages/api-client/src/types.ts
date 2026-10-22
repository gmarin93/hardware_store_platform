// Convenience aliases over the generated schema (no runtime code).
import type { components, operations, paths } from "./generated/openapi";

type Schemas = components["schemas"];

export type { components, operations, paths };
export type Me = Schemas["Me"];
export type MeBranch = Schemas["MeBranch"];
export type Role = Schemas["RoleEnum"];
export type Unit = Schemas["Unit"];
export type AttributeUnit = Schemas["AttributeUnit"];
export type AttributeValueType = Schemas["AttributeValueType"];
export type PublicAttribute = Schemas["PublicAttribute"];
export type PublicMedia = Schemas["PublicMedia"];
export type PublicProduct = Schemas["PublicProduct"];
export type PublicProductDetail = Schemas["PublicProductDetail"];
export type PublicVariant = Schemas["PublicVariant"];
export type PublicVariantDetail = Schemas["PublicVariantDetail"];
export type PaginatedPublicProductList = Schemas["PaginatedPublicProductList"];
export type BrandSummary = Schemas["BrandSummary"];
export type CategorySummary = Schemas["CategorySummary"];
export type ProductListQuery = NonNullable<operations["catalog_products_list"]["parameters"]["query"]>;
