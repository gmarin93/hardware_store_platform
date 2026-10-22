import Link from "next/link";

export default function HomePage() {
  return (
    <>
      <h1>Ferretería Demo</h1>
      <p className="lead">
        Consulte el catálogo de productos de demostración: herramientas, tornillería y materiales con datos
        sintéticos.
      </p>
      <p>
        <Link href="/catalog" className="button">
          Ver el catálogo
        </Link>
      </p>
    </>
  );
}
