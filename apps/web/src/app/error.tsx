"use client";

export default function RootError({ retry }: { error: unknown; retry: () => void }) {
  return (
    <section className="state state-error" role="alert" data-testid="error-state">
      <h1 className="state-title">Algo salió mal</h1>
      <p>No pudimos mostrar esta página. Intente de nuevo en unos minutos.</p>
      <button type="button" className="button" onClick={() => retry()}>
        Reintentar
      </button>
    </section>
  );
}
