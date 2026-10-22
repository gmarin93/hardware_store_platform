"use client";

import Link, { useLinkStatus } from "next/link";
import type { ComponentProps } from "react";

function PendingHint() {
  const { pending } = useLinkStatus();
  return pending ? (
    <span className="pending-hint" role="status">
      {" "}
      (cargando…)
    </span>
  ) : null;
}

/** Link that shows a loading hint while its navigation is pending. */
export function PendingLink({ children, ...props }: ComponentProps<typeof Link>) {
  return (
    <Link {...props}>
      {children}
      <PendingHint />
    </Link>
  );
}
