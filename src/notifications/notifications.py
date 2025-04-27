from .interfaces.notification_channel import INotificationChannel
from .properties.properties import TelegramNotificationProperties, NotificationChannelBaseProperties
from .channels.telegram_notification_channel import TelegramNotificationChannel


class NotificationService:

    def __init__(self, properties: NotificationChannelBaseProperties) -> None:
        self._channel = self._get_channel(properties)

    def _get_channel(self, properties: NotificationChannelBaseProperties) -> INotificationChannel:
        """
        Get the notification channel based on the provided properties.
        """
        if isinstance(properties, TelegramNotificationProperties):
            return TelegramNotificationChannel(properties)
        else:
            raise NotImplementedError(f"Notification channel for {type(properties)} is not implemented.")

    def send_notification(self, title: str, message: str) -> None:
        """
        Send a notification using the specified channel.
        """
        self._channel.send_message(title, message)
