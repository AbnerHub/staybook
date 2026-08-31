// Constantes de rutas del backend de StayBook (todas bajo /api/v1, salvo docs).
// Centralizar las rutas evita strings dispersos en el código y documenta la
// superficie real del backend sin implementar sus llamadas de negocio.
export const ENDPOINTS = {
  rooms: "/api/v1/rooms/",
  room: (id) => `/api/v1/rooms/${id}`,
  roomsAvailable: "/api/v1/rooms/available",
  guests: "/api/v1/guests/",
  guest: (id) => `/api/v1/guests/${id}`,
  reservations: "/api/v1/reservations/",
  reservation: (id) => `/api/v1/reservations/${id}`,
  reservationCancel: (id) => `/api/v1/reservations/${id}/cancel`,
  reservationCheckIn: (id) => `/api/v1/reservations/${id}/check-in`,
  reservationCheckOut: (id) => `/api/v1/reservations/${id}/check-out`,
  availability: "/api/v1/availability",
  occupancyCurrent: "/api/v1/occupancy/current",
  occupancyRooms: "/api/v1/occupancy/rooms",
  historyReservations: "/api/v1/history/reservations",
  openapi: "/openapi.json",
};
