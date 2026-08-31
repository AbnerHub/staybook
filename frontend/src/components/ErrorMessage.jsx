/**
 * Componente reutilizable para mostrar errores al usuario.
 *
 * Recibe un error (normalmente un `ApiError`, pero tolera strings u objetos
 * simples) y muestra un mensaje orientado al usuario. Nunca expone trazas
 * internas (stack), causas subyacentes ni cuerpos crudos de respuesta.
 *
 * Requirements: 8.2, 8.3, 8.6
 */

const GENERIC_MESSAGE = "Ocurrió un error";
const NETWORK_MESSAGE = "No se pudo conectar con el servidor";

/**
 * Deriva un mensaje seguro y legible a partir del error recibido.
 *
 * @param {*} error - `ApiError`, string u objeto/valor arbitrario.
 * @returns {string}
 */
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
    // Objeto de error sin forma conocida: usar `detail`/`message` si existen,
    // pero nunca `stack`, `cause` ni `payload`.
    if (typeof error.detail === "string" && error.detail) {
      return error.detail;
    }
    if (typeof error.message === "string" && error.message) {
      return error.message;
    }
  }

  return GENERIC_MESSAGE;
}

/**
 * @param {Object} props
 * @param {*} [props.error] - Error a mostrar. Si es falsy, no renderiza nada.
 */
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
