// Presentation-only formatting for API values. Decimal strings are never
// converted to floating point.
import type { AttributeUnit, PublicAttribute, Role, Unit } from "@hardware-store/api-client";

const DECIMAL_RE = /^(-?)(\d+)(?:\.(\d+))?$/;

/** "12.700" -> "12,7"; "1.000" -> "1". Unrecognized strings are returned unchanged. */
export function formatDecimal(value: string): string {
  const match = DECIMAL_RE.exec(value.trim());
  if (!match) return value;
  const [, sign = "", integer = "0", fraction = ""] = match;
  const trimmed = fraction.replace(/0+$/, "");
  const normalizedInteger = integer.replace(/^0+(?=\d)/, "");
  const isZero = /^0*$/.test(normalizedInteger) && trimmed === "";
  return `${isZero ? "" : sign}${normalizedInteger}${trimmed ? `,${trimmed}` : ""}`;
}

const UNIT_LABELS: Record<Unit, string> = {
  piece: "pieza",
  m: "metro",
  cm: "centímetro",
  kg: "kilogramo",
  g: "gramo",
  l: "litro",
};

export function unitLabel(unit: Unit): string {
  return UNIT_LABELS[unit] ?? unit;
}

const ATTRIBUTE_UNIT_SYMBOLS: Partial<Record<AttributeUnit, string>> = { in: "pulg", l: "L", ml: "mL" };

export function attributeUnitSymbol(unit: AttributeUnit): string {
  return ATTRIBUTE_UNIT_SYMBOLS[unit] ?? unit;
}

export function formatAttributeValue(attribute: Pick<PublicAttribute, "value" | "value_type" | "unit">): string {
  let text: string;
  if (attribute.value_type === "BOOLEAN") {
    text = attribute.value === "true" ? "Sí" : attribute.value === "false" ? "No" : attribute.value;
  } else if (attribute.value_type === "DECIMAL") {
    text = formatDecimal(attribute.value);
  } else {
    text = attribute.value;
  }
  return attribute.unit ? `${text} ${attributeUnitSymbol(attribute.unit)}` : text;
}

const ROLE_LABELS: Record<Role, string> = {
  ADMIN: "Administración",
  EMPLOYEE: "Personal de sucursal",
  CUSTOMER: "Cliente",
  GUEST: "Sin rol asignado",
};

export function roleLabel(role: Role): string {
  return ROLE_LABELS[role] ?? role;
}

/**
 * Only same-origin relative media paths are rendered; anything else falls
 * back to the placeholder (no remote images are fetched).
 */
export function isSafeMediaPath(url: string | undefined | null): url is string {
  return typeof url === "string" && url.startsWith("/") && !url.startsWith("//") && !url.includes("\\");
}
