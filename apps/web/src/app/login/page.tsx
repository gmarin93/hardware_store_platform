import type { Metadata } from "next";

import { LoginForm } from "../../components/LoginForm";

export const metadata: Metadata = { title: "Iniciar sesión" };

export default function LoginPage() {
  return (
    <div className="narrow">
      <h1>Iniciar sesión</h1>
      <p className="muted">Use una cuenta de demostración (@example.test) creada en su entorno local.</p>
      <LoginForm />
    </div>
  );
}
