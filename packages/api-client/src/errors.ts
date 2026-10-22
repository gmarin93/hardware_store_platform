// Helpers for the API error envelope {code, message, field_errors, request_id}
// (ADR 0003). They only interpret the transport shape; messages come from the
// backend (es-CR) with a generic Spanish fallback for non-envelope failures.
import type { components } from "./generated/openapi";

export type ErrorEnvelope = components["schemas"]["ErrorEnvelope"];
export type FieldError = components["schemas"]["FieldError"];

/** Code used when the response is not a valid envelope (proxy error, HTML, network). */
export const UNEXPECTED_RESPONSE = "UNEXPECTED_RESPONSE";
export const NETWORK_ERROR = "NETWORK_ERROR";

export const FALLBACK_MESSAGES: Readonly<Record<string, string>> = {
  [UNEXPECTED_RESPONSE]: "El servicio respondió de forma inesperada. Intente de nuevo en unos minutos.",
  [NETWORK_ERROR]: "No se pudo conectar con el servicio. Revise su conexión e intente de nuevo.",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isFieldErrorList(value: unknown): value is FieldError[] {
  return (
    Array.isArray(value) &&
    value.every((item) => isRecord(item) && typeof item.code === "string" && typeof item.message === "string")
  );
}

/** Runtime guard: true only for a well-formed error envelope. */
export function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (!isRecord(value)) return false;
  if (typeof value.code !== "string" || typeof value.message !== "string") return false;
  if (typeof value.request_id !== "string") return false;
  if (!isRecord(value.field_errors)) return false;
  return Object.values(value.field_errors).every(isFieldErrorList);
}

/** Normalized failure: HTTP status (0 for network errors) plus an envelope. */
export interface ApiFailure {
  status: number;
  envelope: ErrorEnvelope;
  /** False when the envelope was synthesized locally (non-envelope body). */
  fromServer: boolean;
}

export function toApiFailure(status: number, body: unknown): ApiFailure {
  if (isErrorEnvelope(body)) {
    return { status, envelope: body, fromServer: true };
  }
  const code = status === 0 ? NETWORK_ERROR : UNEXPECTED_RESPONSE;
  return {
    status,
    envelope: { code, message: FALLBACK_MESSAGES[code] ?? "", field_errors: {}, request_id: "" },
    fromServer: false,
  };
}

export function networkFailure(): ApiFailure {
  return toApiFailure(0, undefined);
}

/** Messages for one field (dotted path), or [] when none. */
export function fieldMessages(envelope: ErrorEnvelope, field: string): string[] {
  return (envelope.field_errors[field] ?? []).map((item) => item.message);
}
