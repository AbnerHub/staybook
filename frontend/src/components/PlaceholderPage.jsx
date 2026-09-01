/**
 * PlaceholderPage: componente base reutilizable para las páginas placeholder.
 * Muestra el título de la sección y una nota de funcionalidad pendiente.
 */
export default function PlaceholderPage({ title, description }) {
  return (
    <section className="placeholder-page">
      <h1>{title}</h1>
      <p className="placeholder-page__note">
        {description ?? "Esta sección estará disponible próximamente."}
      </p>
    </section>
  );
}
