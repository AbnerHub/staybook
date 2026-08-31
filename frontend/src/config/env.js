/**
 * Configuración de entorno centralizada.
 *
 * Única fuente de la URL base del backend FastAPI. Los módulos de la app
 * (p. ej. el cliente de API) deben obtener la base desde aquí y no leer
 * `import.meta.env` directamente.
 */

// Fallback local documentado para desarrollo cuando VITE_API_BASE_URL no está definida.
const DEFAULT_LOCAL = "http://127.0.0.1:8000";

/**
 * Devuelve la URL base del backend.
 *
 * - Usa `VITE_API_BASE_URL` cuando está definida y no está vacía.
 * - Recorta las barras finales para construir URLs de forma consistente.
 * - Cae al fallback local (`http://127.0.0.1:8000`) en caso contrario.
 *
 * @returns {string} URL base sin barra final.
 */
export function getApiBaseUrl() {
  const raw = import.meta.env.VITE_API_BASE_URL;
  return raw && raw.trim() ? raw.replace(/\/+$/, "") : DEFAULT_LOCAL;
}
