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
