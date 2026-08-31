/**
 * PlaceholderPage
 *
 * Componente base reutilizable para las páginas placeholder de secciones
 * (Dashboard, Rooms, Guests, Reservations, Availability, History, Login).
 *
 * Muestra el título de la sección y una indicación de que la funcionalidad
 * está pendiente. No contiene lógica de negocio ni llamadas de datos reales
 * (Requerimientos 5.1, 5.2, 5.3, 5.4).
 *
 * @param {Object} props
 * @param {string} props.title - Título identificable de la sección.
 * @param {string} [props.description] - Nota opcional; por defecto indica que
 *   la sección estará disponible próximamente.
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
