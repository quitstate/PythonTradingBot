from typing import Protocol


class INotificationChannel(Protocol):
    """
    Interface for notification channels.
    """

    def send_message(self, title: str, message: str) -> None:
        ...
