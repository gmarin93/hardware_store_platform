import type { Metadata } from "next";

import { AccountView } from "../../components/AccountView";
import { getSession } from "../../lib/session";

export const metadata: Metadata = { title: "Mi cuenta" };

// Per-user page: always rendered at request time, never cached (ADR 0001).
export const dynamic = "force-dynamic";

export default async function AccountPage() {
  const session = await getSession();
  return (
    <>
      <h1>Mi cuenta</h1>
      <AccountView session={session} />
    </>
  );
}
