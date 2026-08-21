"""Audit logging module for StayBook.

Provides a structured audit logging function that records
operations on rooms. Never logs tokens, passwords, or PII.
"""

import logging
from datetime import UTC, datetime

logger = logging.getLogger("staybook.audit")


def audit_log(
    operation: str,
    room_id: int | None,
    result: str,
) -> None:
    """
    Registra operación de auditoría.
    Excluye datos sensibles (tokens, contraseñas, PII).

    Args:
        operation: "create" | "update" | "delete"
        room_id: ID de la habitación afectada
        result: "success" | "failure"
    """
    logger.info(
        "audit_event",
        extra={
            "timestamp": datetime.now(UTC).isoformat(),
            "operation": operation,
            "room_id": room_id,
            "result": result,
        },
    )
