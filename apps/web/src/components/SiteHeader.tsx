import Link from "next/link";

import { SessionNav } from "./SessionNav";

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="container header-inner">
        <Link href="/" className="brand">
          Ferretería Demo
        </Link>
        <nav aria-label="Principal" className="nav">
          <ul className="nav-list">
            <li>
              <Link href="/catalog">Catálogo</Link>
            </li>
          </ul>
          <SessionNav />
        </nav>
      </div>
    </header>
  );
}
