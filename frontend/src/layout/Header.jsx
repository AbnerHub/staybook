/**
 * Header
 *
 * Encabezado de ancho completo del área administrativa. Muestra la marca/título
 * de la aplicación y reserva un slot para futuras acciones de sesión (por
 * ejemplo, un botón "Cerrar sesión").
 *
 * En esta fase el slot de sesión NO implementa lógica: es únicamente un punto
 * de extensión que se poblará cuando se implemente la spec de Authentication.
 *
 * Las clases coordinadas con styles/layout.css son:
 * `.admin-layout__header`, `.header__title`, `.header__session`.
 *
 * Requisitos: 4.5 (encabezado con marca y slot reservado para acciones de
 * sesión, sin lógica en esta fase).
 */
export default function Header() {
  return (
    <header className="admin-layout__header">
      <span className="header__title">StayBook</span>
      {/* Slot reservado para acciones de sesión (p. ej. botón "Cerrar sesión").
          Se poblará cuando se implemente la autenticación. Sin lógica por ahora. */}
      <div className="header__session" />
    </header>
  );
}
