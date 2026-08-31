import { Link } from "react-router-dom";

/**
 * Contenido 404 para rutas desconocidas (Req 3.5, 11.5).
 *
 * Renderiza un mensaje legible "Página no encontrada" y un enlace de regreso
 * al Dashboard, de modo que ninguna ruta válida ni la ruta catch-all quede en
 * blanco. No contiene lógica de negocio.
 */
export default function NotFound() {
  return (
    <section className="not-found">
      <p className="not-found__code">404</p>
      <h1 className="not-found__title">Página no encontrada</h1>
      <p className="not-found__message">
        La página que buscas no existe o fue movida.
      </p>
      <Link to="/dashboard" className="not-found__link">
        Volver al Dashboard
      </Link>
    </section>
  );
}
