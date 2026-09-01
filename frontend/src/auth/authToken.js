/**
 * Punto único de extensión para autenticación.
 *
 * En esta fase (frontend foundation) no se implementa JWT: `getToken()` es un
 * stub que retorna `null`. Cuando se implemente la autenticación, solo cambiará
 * `getToken()` (y quién setea el token); el cliente de API y los componentes no
 * se tocan.
 */

export function getToken() {
  return null;
}

export function authHeader() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
