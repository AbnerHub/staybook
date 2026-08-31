// Indicador de carga genérico y reutilizable.
// No contiene lógica de negocio; solo muestra un estado de carga accesible.
export default function Loading({ label = "Cargando…" }) {
  return (
    <div className="loading" role="status" aria-live="polite">
      <span className="loading__spinner" aria-hidden="true" />
      <span className="loading__label">{label}</span>
    </div>
  );
}
