"""Custom exceptions for the StayBook domain."""


class AppException(Exception):
    """Base exception para el dominio."""

    def __init__(self, detail: str, status_code: int):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class RoomNotFoundException(AppException):
    """Excepción lanzada cuando una habitación no existe."""

    def __init__(self):
        super().__init__(
            detail="La habitación no fue encontrada", status_code=404
        )


class RoomDuplicateException(AppException):
    """Excepción lanzada cuando el número de habitación ya está registrado."""

    def __init__(self):
        super().__init__(
            detail="El número de habitación ya está registrado", status_code=409
        )


class RoomOccupiedException(AppException):
    """Excepción lanzada cuando se intenta eliminar una habitación ocupada."""

    def __init__(self):
        super().__init__(
            detail="No se puede eliminar una habitación ocupada", status_code=409
        )


class GuestNotFoundException(AppException):
    """Excepción lanzada cuando un huésped no existe."""

    def __init__(self):
        super().__init__(
            detail="El huésped no fue encontrado", status_code=404
        )


class GuestEmailDuplicateException(AppException):
    """Excepción lanzada cuando el correo electrónico ya está registrado."""

    def __init__(self):
        super().__init__(
            detail="El correo electrónico ya está registrado", status_code=409
        )


class GuestIdentificationDuplicateException(AppException):
    """Excepción lanzada cuando el documento de identificación ya está registrado."""

    def __init__(self):
        super().__init__(
            detail="El documento de identificación ya está registrado",
            status_code=409,
        )


class ReservationNotFoundException(AppException):
    """Excepción lanzada cuando una reserva no existe."""

    def __init__(self):
        super().__init__(
            detail="La reserva no fue encontrada", status_code=404
        )


class ReservationInvalidDatesException(AppException):
    """Excepción lanzada cuando el rango de fechas de la reserva es inválido."""

    def __init__(self):
        super().__init__(
            detail="La fecha de salida debe ser posterior a la fecha de entrada",
            status_code=422,
        )


class ReservationOverlapException(AppException):
    """Excepción lanzada cuando la habitación ya está reservada en el rango."""

    def __init__(self):
        super().__init__(
            detail=(
                "La habitación ya está reservada en el rango de fechas solicitado"
            ),
            status_code=409,
        )


class ReservationCancelledNotEditableException(AppException):
    """Excepción lanzada cuando se intenta modificar una reserva cancelada."""

    def __init__(self):
        super().__init__(
            detail="Una reserva cancelada no puede ser modificada",
            status_code=409,
        )


class ReservationAlreadyCancelledException(AppException):
    """Excepción lanzada cuando se intenta cancelar una reserva ya cancelada."""

    def __init__(self):
        super().__init__(
            detail="La reserva ya se encuentra cancelada",
            status_code=409,
        )
