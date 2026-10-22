import Link from "next/link";
import type { ReactNode } from "react";

type Tone = "info" | "error" | "warning";

interface StateMessageProps {
  title: string;
  children?: ReactNode;
  tone?: Tone;
  /** Optional follow-up link. */
  action?: { href: string; label: string };
  testId?: string;
  /** Use role="alert" for failures that should be announced immediately. */
  announce?: boolean;
}

export function StateMessage({ title, children, tone = "info", action, testId, announce }: StateMessageProps) {
  return (
    <section
      className={`state state-${tone}`}
      role={announce ? "alert" : "status"}
      aria-live={announce ? undefined : "polite"}
      data-testid={testId}
    >
      <h2 className="state-title">{title}</h2>
      {children ? <div className="state-body">{children}</div> : null}
      {action ? (
        <p>
          <Link href={action.href}>{action.label}</Link>
        </p>
      ) : null}
    </section>
  );
}

export function LoadingState({ label }: { label: string }) {
  return (
    <div className="state state-loading" role="status" aria-live="polite" data-testid="loading-state">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

/** Failure state with the backend's es-CR message and request id (for support). */
export function ApiErrorState({
  title,
  message,
  requestId,
  action,
}: {
  title: string;
  message: string;
  requestId?: string;
  action?: { href: string; label: string };
}) {
  return (
    <StateMessage title={title} tone="error" action={action} testId="error-state" announce>
      <p>{message}</p>
      {requestId ? (
        <p className="muted">
          Referencia: <code>{requestId}</code>
        </p>
      ) : null}
    </StateMessage>
  );
}
