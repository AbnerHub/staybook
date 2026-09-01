/**
 * Header
 *
 * Encabezado de ancho completo del área administrativa. Muestra la marca y
 * reserva un slot para futuras acciones de sesión (sin lógica en esta fase).
 */
export default function Header() {
  return (
    <header className="admin-layout__header">
      <span className="header__title">StayBook</span>
      {/* Slot reservado para acciones de sesión (p. ej. "Cerrar sesión"). */}
      <div className="header__session" />
    </header>
  );
}
