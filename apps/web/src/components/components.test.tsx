import type { Me, PublicProduct } from "@hardware-store/api-client";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/",
}));

const { AccountView } = await import("./AccountView");
const { DemoBanner } = await import("./DemoBanner");
const { ProductCard } = await import("./ProductCard");
const { LoginForm } = await import("./LoginForm");

const baseMe: Me = {
  user: { id: "00000000-0000-4000-8000-000000000003", email: "empleado.central@example.test", full_name: "Empleado" },
  organization: { id: "00000000-0000-4000-8000-000000000010", slug: "demo", name: "Ferretería Demo (SINTÉTICO)", is_synthetic: true },
  role: "EMPLOYEE",
  branches: [{ id: "00000000-0000-4000-8000-000000000020", code: "central", name: "Sucursal Central (SINTÉTICO)" }],
  permissions: ["catalog.view_published", "catalog.view_staff_fields"],
};

describe("DemoBanner", () => {
  it("always shows the synthetic data notice", () => {
    expect(renderToStaticMarkup(<DemoBanner />)).toContain("Datos de demostración");
  });
});

describe("AccountView", () => {
  it("prompts anonymous visitors to sign in", () => {
    const html = renderToStaticMarkup(<AccountView session={{ kind: "anonymous" }} />);
    expect(html).toContain("Necesita iniciar sesión");
    expect(html).toContain('href="/login"');
    expect(html).not.toContain("Cerrar sesión");
  });

  it("shows role and visible branches for a signed-in employee", () => {
    const html = renderToStaticMarkup(<AccountView session={{ kind: "signed-in", me: baseMe }} />);
    expect(html).toContain("Personal de sucursal");
    expect(html).toContain("Sucursal Central (SINTÉTICO)");
    expect(html).toContain("empleado.central@example.test");
    expect(html).toContain("Cerrar sesión");
  });

  it("shows an authenticated GUEST as signed in without access (not as anonymous)", () => {
    const guest: Me = { ...baseMe, role: "GUEST", organization: null, branches: [], permissions: ["catalog.view_published"] };
    const html = renderToStaticMarkup(<AccountView session={{ kind: "signed-in", me: guest }} />);
    expect(html).toContain("Cuenta sin acceso asignado");
    expect(html).toContain("Sin rol asignado");
    expect(html).toContain("Cerrar sesión");
    expect(html).not.toContain("Necesita iniciar sesión");
  });

  it("renders the backend message on failure", () => {
    const html = renderToStaticMarkup(
      <AccountView
        session={{
          kind: "error",
          failure: {
            status: 500,
            fromServer: true,
            envelope: { code: "INTERNAL_ERROR", message: "Ocurrió un error interno.", field_errors: {}, request_id: "abc" },
          },
        }}
      />,
    );
    expect(html).toContain("Ocurrió un error interno.");
    expect(html).toContain('role="alert"');
  });
});

describe("ProductCard", () => {
  const product: PublicProduct = {
    id: "00000000-0000-4000-8000-000000000030",
    name: "Tornillo SINTÉTICO",
    description: "Descripción",
    brand: { id: "00000000-0000-4000-8000-000000000040", name: "Marca X", slug: "marca-x" },
    category: null,
    media: [{ id: "00000000-0000-4000-8000-000000000050", url: "https://remote.example/a.png", alt_text: "Tornillo" }],
  };

  it("uses an accessible placeholder for non-local media and links variants by SKU", () => {
    const html = renderToStaticMarkup(
      <ProductCard
        product={product}
        variants={[
          {
            id: "00000000-0000-4000-8000-000000000060",
            sku: "SIN-TOR-8X1",
            name: "Tornillo 8x1",
            sales_unit: "piece",
            quantity_increment: "1.000",
            min_quantity: "1.000",
            attributes: [],
            media: [],
          },
        ]}
      />,
    );
    expect(html).not.toContain("remote.example");
    expect(html).toContain('role="img"');
    expect(html).toContain('aria-label="Sin imagen: Tornillo"');
    expect(html).toContain('href="/catalog/SIN-TOR-8X1"');
  });

  it("explains when variants could not be loaded", () => {
    expect(renderToStaticMarkup(<ProductCard product={product} variants={null} />)).toContain(
      "No se pudieron cargar las variantes",
    );
  });
});

describe("LoginForm", () => {
  it("renders labelled email and password fields", () => {
    const html = renderToStaticMarkup(<LoginForm />);
    expect(html).toContain('<label for="login-email">Correo electrónico</label>');
    expect(html).toContain('<label for="login-password">Contraseña</label>');
    expect(html).toContain('autoComplete="current-password"');
  });
});
