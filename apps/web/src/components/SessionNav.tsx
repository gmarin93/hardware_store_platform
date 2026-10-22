"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { browserApi } from "../lib/api/browser";
import { SESSION_CHANGED_EVENT } from "../lib/auth-actions";
import { LogoutButton } from "./LogoutButton";

type NavState = "unknown" | "anonymous" | "signed-in";

/**
 * Header session controls. Reads GET /auth/me from the browser (same origin),
 * so server-rendered HTML of public pages never depends on the session.
 * An authenticated GUEST is still "signed-in" (ADR 0003).
 */
export function SessionNav() {
  const pathname = usePathname();
  const [state, setState] = useState<NavState>("unknown");
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const onChange = () => setVersion((value) => value + 1);
    window.addEventListener(SESSION_CHANGED_EVENT, onChange);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, onChange);
  }, []);

  useEffect(() => {
    let cancelled = false;
    browserApi()
      .GET("/api/v1/auth/me", { cache: "no-store" })
      .then(({ response }) => {
        if (cancelled) return;
        if (response.ok) setState("signed-in");
        else if (response.status === 401) setState("anonymous");
        else setState("unknown");
      })
      .catch(() => {
        if (!cancelled) setState("unknown");
      });
    return () => {
      cancelled = true;
    };
  }, [pathname, version]);

  return (
    <ul className="nav-list" data-testid="session-nav" data-session-state={state}>
      <li>
        <Link href="/account">Mi cuenta</Link>
      </li>
      {state === "anonymous" ? (
        <li>
          <Link href="/login">Iniciar sesión</Link>
        </li>
      ) : null}
      {state === "signed-in" ? (
        <li>
          <LogoutButton className="link-button" />
        </li>
      ) : null}
    </ul>
  );
}
