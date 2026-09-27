"""Envío de correo abstracto. En desarrollo solo se registra en logs; nunca se envían contraseñas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.core.config import Settings
from app.core.logging import get_logger

log = get_logger("app.email")


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    body_text: str


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None: ...


class ConsoleEmailSender:
    async def send(self, message: EmailMessage) -> None:
        log.info("email_sent", to=message.to, subject=message.subject)


@dataclass
class MemoryEmailSender:
    """Captura mensajes en memoria (pruebas)."""

    outbox: list[EmailMessage] = field(default_factory=list)

    async def send(self, message: EmailMessage) -> None:
        self.outbox.append(message)


def build_email_sender(settings: Settings) -> EmailSender:
    if settings.email_backend == "memory":
        return MemoryEmailSender()
    return ConsoleEmailSender()
