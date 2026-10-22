import { describe, expect, it } from "vitest";

import { formatAttributeValue, formatDecimal, isSafeMediaPath, roleLabel, unitLabel } from "./format";

describe("formatDecimal", () => {
  it("formats decimal strings without floating point", () => {
    expect(formatDecimal("12.700")).toBe("12,7");
    expect(formatDecimal("1.000")).toBe("1");
    expect(formatDecimal("0.250")).toBe("0,25");
    expect(formatDecimal("007.5")).toBe("7,5");
    expect(formatDecimal("-0.000")).toBe("0");
    expect(formatDecimal("12345678901.123")).toBe("12345678901,123");
    expect(formatDecimal("abc")).toBe("abc");
  });
});

describe("attributes and labels", () => {
  it("formats by value_type and nullable unit", () => {
    expect(formatAttributeValue({ value: "12.700", value_type: "DECIMAL", unit: "mm" })).toBe("12,7 mm");
    expect(formatAttributeValue({ value: "0.500", value_type: "DECIMAL", unit: "in" })).toBe("0,5 pulg");
    expect(formatAttributeValue({ value: "true", value_type: "BOOLEAN", unit: null })).toBe("Sí");
    expect(formatAttributeValue({ value: "false", value_type: "BOOLEAN", unit: null })).toBe("No");
    expect(formatAttributeValue({ value: "Acero", value_type: "TEXT", unit: null })).toBe("Acero");
  });

  it("labels units and roles in Spanish", () => {
    expect(unitLabel("piece")).toBe("pieza");
    expect(roleLabel("GUEST")).toBe("Sin rol asignado");
    expect(roleLabel("EMPLOYEE")).toBe("Personal de sucursal");
  });

  it("accepts only same-origin relative media paths", () => {
    expect(isSafeMediaPath("/catalog-media/sintetico/a.svg")).toBe(true);
    expect(isSafeMediaPath("https://cdn.example/a.png")).toBe(false);
    expect(isSafeMediaPath("//cdn.example/a.png")).toBe(false);
    expect(isSafeMediaPath("javascript:alert(1)")).toBe(false);
    expect(isSafeMediaPath("")).toBe(false);
    expect(isSafeMediaPath(null)).toBe(false);
  });
});
