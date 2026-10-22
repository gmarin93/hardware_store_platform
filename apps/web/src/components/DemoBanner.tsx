/** Always rendered: P1 uses only synthetic data (ADR 0001). */
export function DemoBanner() {
  return (
    <div className="demo-banner" role="note" aria-label="Aviso de datos" data-testid="demo-banner">
      <strong>Datos de demostración.</strong> Productos, marcas, sucursales y personas son ficticios (SINTÉTICO) y
      no representan una ferretería real.
    </div>
  );
}
