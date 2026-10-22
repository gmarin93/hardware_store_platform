import Link from "next/link";

export default function NotFound() {
  return (
    <>
      <h1>Página no encontrada</h1>
      <p>La dirección que buscó no existe.</p>
      <p>
        <Link href="/catalog">Ir al catálogo</Link>
      </p>
    </>
  );
}
