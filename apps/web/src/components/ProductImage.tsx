"use client";

import { useEffect, useRef, useState } from "react";

import { isSafeMediaPath } from "../lib/format";

interface ProductImageProps {
  src: string | null | undefined;
  alt: string;
  className?: string;
}

/**
 * Renders a same-origin product image, or an accessible placeholder when the
 * media is missing, not a local path, or fails to load (P1 synthetic media
 * URLs do not exist).
 */
export function ProductImage({ src, alt, className }: ProductImageProps) {
  const [failed, setFailed] = useState(false);
  const ref = useRef<HTMLImageElement>(null);

  useEffect(() => {
    // An image that failed before hydration never fires onError.
    const img = ref.current;
    if (img && img.complete && img.naturalWidth === 0) setFailed(true);
  }, [src]);

  if (!isSafeMediaPath(src) || failed) {
    return (
      <div className={`image-placeholder ${className ?? ""}`} role="img" aria-label={`Sin imagen: ${alt}`}>
        <svg viewBox="0 0 24 24" width="40" height="40" aria-hidden="true" focusable="false">
          <path
            fill="currentColor"
            d="M21 5v14H3V5h18m0-2H3a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2Zm-7.14 9.86-3 3.87L8.71 13.14 5 18h14l-5.14-5.14Z"
          />
        </svg>
        <span>Sin imagen</span>
      </div>
    );
  }

  return (
    // Plain <img>: local synthetic paths only, no next/image optimizer or remote patterns.
    // eslint-disable-next-line @next/next/no-img-element
    <img ref={ref} src={src} alt={alt} className={className} loading="lazy" onError={() => setFailed(true)} />
  );
}
