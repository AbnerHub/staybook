/**
 * Componente reutilizable para mostrar errores al usuario.
 * Nunca expone trazas internas (stack), causas ni cuerpos crudos.
 */

const GENERIC_MESSAGE = "Ocurrió un error";
const NETWORK_MESSAGE = "No se pudo conectar con el servidor";

function resolveMessage(error) {
  if (typeof error === "string") {
    return error;
  }

  if (error && typeof error === "object") {
    if (error.kind === "network") {
      return NETWORK_MESSAGE;
    }
    if (error.kind === "http") {
      return error.detail || GENERIC_MESSAGE;
    }
    if (typeof error.detail === "string" && error.detail) {
      return error.detail;
    }
    if (typeof error.message === "string" && error.message) {
      return error.message;
    }
  }

  return GENERIC_MESSAGE;
}

export default function ErrorMessage({ error }) {
  if (!error) {
    return null;
  }

  return (
    <div className="error-message" role="alert">
      {resolveMessage(error)}
    </div>
  );
}
