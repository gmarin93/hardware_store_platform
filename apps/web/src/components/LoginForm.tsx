"use client";

import { fieldMessages, type ErrorEnvelope } from "@hardware-store/api-client";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { browserApi } from "../lib/api/browser";
import { announceSessionChange, login } from "../lib/auth-actions";

export function LoginForm() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [envelope, setEnvelope] = useState<ErrorEnvelope | null>(null);
  const summaryRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (envelope) summaryRef.current?.focus();
  }, [envelope]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const email = String(data.get("email") ?? "");
    const password = String(data.get("password") ?? "");
    setSubmitting(true);
    setEnvelope(null);
    const result = await login({ api: browserApi(), readCookies: () => document.cookie }, email, password);
    if (result.ok) {
      announceSessionChange();
      router.replace("/account");
      router.refresh();
      return;
    }
    // Never keep or log the password after a failed attempt.
    const passwordInput = form.elements.namedItem("password");
    if (passwordInput instanceof HTMLInputElement) passwordInput.value = "";
    setEnvelope(result.failure.envelope);
    setSubmitting(false);
  }

  const emailErrors = envelope ? fieldMessages(envelope, "email") : [];
  const passwordErrors = envelope ? fieldMessages(envelope, "password") : [];
  const generalErrors = envelope ? fieldMessages(envelope, "non_field_errors") : [];

  return (
    <form className="form" onSubmit={onSubmit} noValidate aria-describedby={envelope ? "login-error" : undefined}>
      {envelope ? (
        <div
          id="login-error"
          className="form-error"
          role="alert"
          tabIndex={-1}
          ref={summaryRef}
          data-testid="login-error"
          data-error-code={envelope.code}
        >
          <p>{envelope.message}</p>
          {generalErrors.map((message) => (
            <p key={message}>{message}</p>
          ))}
        </div>
      ) : null}

      <div className="field">
        <label htmlFor="login-email">Correo electrónico</label>
        <input
          id="login-email"
          name="email"
          type="email"
          autoComplete="username"
          inputMode="email"
          required
          maxLength={254}
          aria-invalid={emailErrors.length > 0 || undefined}
          aria-describedby={emailErrors.length > 0 ? "login-email-error" : undefined}
        />
        {emailErrors.length > 0 ? (
          <p id="login-email-error" className="field-error">
            {emailErrors.join(" ")}
          </p>
        ) : null}
      </div>

      <div className="field">
        <label htmlFor="login-password">Contraseña</label>
        <input
          id="login-password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          maxLength={256}
          aria-invalid={passwordErrors.length > 0 || undefined}
          aria-describedby={passwordErrors.length > 0 ? "login-password-error" : undefined}
        />
        {passwordErrors.length > 0 ? (
          <p id="login-password-error" className="field-error">
            {passwordErrors.join(" ")}
          </p>
        ) : null}
      </div>

      <button type="submit" className="button" disabled={submitting} aria-disabled={submitting}>
        {submitting ? "Ingresando…" : "Iniciar sesión"}
      </button>
    </form>
  );
}
