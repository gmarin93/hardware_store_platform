import type { Metadata } from "next";
import type { ReactNode } from "react";

import { DemoBanner } from "../components/DemoBanner";
import { SiteHeader } from "../components/SiteHeader";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Ferretería Demo (datos de demostración)", template: "%s · Ferretería Demo" },
  description: "Catálogo de demostración con datos sintéticos.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="es-CR">
      <body>
        <a href="#contenido" className="skip-link">
          Saltar al contenido principal
        </a>
        <DemoBanner />
        <SiteHeader />
        <main id="contenido" tabIndex={-1} className="container main">
          {children}
        </main>
        <footer className="site-footer">
          <div className="container">
            <p>Entorno local de demostración. Toda la información mostrada es sintética.</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
