import type { SessionState } from "../lib/session";
import { roleLabel } from "../lib/format";
import { LogoutButton } from "./LogoutButton";
import { ApiErrorState, StateMessage } from "./StateMessage";

export function AccountView({ session }: { session: SessionState }) {
  if (session.kind === "anonymous") {
    return (
      <StateMessage
        title="Necesita iniciar sesión"
        tone="warning"
        testId="unauthorized-state"
        action={{ href: "/login", label: "Iniciar sesión" }}
      >
        <p>Inicie sesión para ver los datos de su cuenta.</p>
      </StateMessage>
    );
  }
  if (session.kind === "error") {
    return (
      <ApiErrorState
        title="No pudimos cargar su cuenta"
        message={session.failure.envelope.message}
        requestId={session.failure.envelope.request_id}
        action={{ href: "/account", label: "Reintentar" }}
      />
    );
  }

  const { me } = session;
  const isGuest = me.role === "GUEST";
  return (
    <div className="account" data-testid="account-view" data-role={me.role}>
      {isGuest ? (
        <StateMessage title="Cuenta sin acceso asignado" tone="warning" testId="guest-state">
          <p>
            Su sesión está iniciada, pero la cuenta no tiene un rol activo en la organización. No tiene permisos
            adicionales. Comuníquese con la administración si cree que es un error.
          </p>
        </StateMessage>
      ) : null}

      <dl className="facts">
        <div>
          <dt>Nombre</dt>
          <dd data-testid="account-name">{me.user.full_name || "Sin nombre registrado"}</dd>
        </div>
        <div>
          <dt>Correo electrónico</dt>
          <dd data-testid="account-email">{me.user.email}</dd>
        </div>
        <div>
          <dt>Organización</dt>
          <dd data-testid="account-organization">
            {me.organization ? me.organization.name : "Sin organización asignada"}
          </dd>
        </div>
        <div>
          <dt>Rol</dt>
          <dd data-testid="account-role">{roleLabel(me.role)}</dd>
        </div>
      </dl>

      <section aria-labelledby="sucursales">
        <h2 id="sucursales">Sucursales visibles</h2>
        {me.branches.length === 0 ? (
          <p className="muted" data-testid="account-no-branches">
            Su cuenta no tiene sucursales asignadas.
          </p>
        ) : (
          <ul data-testid="account-branches">
            {me.branches.map((branch) => (
              <li key={branch.id}>
                {branch.name} <span className="muted">({branch.code})</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="permisos">
        <h2 id="permisos">Permisos</h2>
        {me.permissions.length === 0 ? (
          <p className="muted" data-testid="account-no-permissions">
            Su cuenta no tiene permisos asignados.
          </p>
        ) : (
          <ul className="permission-list" data-testid="account-permissions">
            {me.permissions.map((code) => (
              <li key={code}>
                <code>{code}</code>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p>
        <LogoutButton />
      </p>
    </div>
  );
}
