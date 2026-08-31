/**
 * Punto único de extensión para autenticación.
 *
 * En esta fase (frontend foundation) no se implementa JWT: `getToken()` es un
 * stub que retorna `null`. Cuando se implemente la autenticación, solo cambiará
 * `getToken()` (y quién setea el token); el cliente de API y los componentes no
 * se tocan.
 */

/**
 * Retorna el token de sesión actual.
 * Stub para la futura implementación de JWT. Hoy siempre retorna `null`.
 * @returns {string|null}
 */
export function getToken() {
  return null;
}

/**
 * Construye el encabezado `Authorization` a partir del token actual.
 * Único lugar donde se añadirá el `Bearer` cuando exista sesión.
 * @returns {{ Authorization: string } | {}}
 */
export function authHeader() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
