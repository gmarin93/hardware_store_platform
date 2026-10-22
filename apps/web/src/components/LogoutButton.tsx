"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { browserApi } from "../lib/api/browser";
import { announceSessionChange, logout } from "../lib/auth-actions";

export function LogoutButton({ className }: { className?: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onClick() {
    setBusy(true);
    setError(null);
    const result = await logout({ api: browserApi(), readCookies: () => document.cookie });
    setBusy(false);
    if (!result.ok) {
      setError(result.failure.envelope.message);
      return;
    }
    announceSessionChange();
    router.push("/");
    router.refresh();
  }

  return (
    <span className="logout">
      <button type="button" className={className ?? "button button-secondary"} onClick={onClick} disabled={busy} data-testid="logout-button">
        {busy ? "Cerrando sesión…" : "Cerrar sesión"}
      </button>
      {error ? (
        <span className="field-error" role="alert">
          {error}
        </span>
      ) : null}
    </span>
  );
}
