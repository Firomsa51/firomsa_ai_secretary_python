"""
Telethon event handlers — wired up after a successful authorisation.

Each handler is a placeholder that will be expanded in Phase 2 when the
AI layer is integrated. For now they log incoming events and return early.
"""

import logging

from telethon import TelegramClient, events
from telethon.tl.types import Message

logger = logging.getLogger(__name__)


def register_handlers(client: TelegramClient) -> None:
    """
    Register all Telegram event handlers on the given client.
    Called once the client confirms it is authorised.
    """
    logger.info("Registering Telegram event handlers…")

    @client.on(events.NewMessage(incoming=True))
    async def on_new_message(event: events.NewMessage.Event) -> None:
        """
        Fires whenever a new incoming message arrives in any chat.

        Phase 1: log the event.
        Phase 2: persist to DB + route through AI agent.
        """
        msg: Message = event.message
        sender = await event.get_sender()
        logger.info(
            "New message from %s (id=%s): %.120s",
            getattr(sender, "username", None) or getattr(sender, "first_name", "unknown"),
            getattr(sender, "id", "?"),
            msg.text or "<non-text>",
        )
        # TODO Phase 2: persist message → run AI agent → optionally auto-reply

    @client.on(events.MessageEdited(incoming=True))
    async def on_message_edited(event: events.MessageEdited.Event) -> None:
        """Fires when an incoming message is edited."""
        logger.debug("Message edited: id=%s", event.message.id)
        # TODO Phase 2: update stored message content

    @client.on(events.MessageRead)
    async def on_message_read(event: events.MessageRead.Event) -> None:
        """Fires when messages are marked as read."""
        logger.debug("Messages read up to id=%s in peer=%s", event.max_id, event.peer)
        # TODO Phase 2: update read-status in DB

    logger.info("Telegram event handlers registered.")
