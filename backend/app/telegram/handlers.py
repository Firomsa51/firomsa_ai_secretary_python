def _build_history(
    conversation: Conversation,
    exclude_message_id: int,
) -> list[dict[str, str]]:
    """
    Build only the recent conversation history.

    Sending the full Telegram history to the LLM quickly exhausts free
    token limits. We therefore keep only the latest few exchanges.
    """

    history: list[dict[str, str]] = []

    messages = sorted(
        conversation.messages,
        key=lambda m: m.created_at or datetime.min.replace(tzinfo=timezone.utc),
    )

    recent_messages = messages[-10:]   # keep only last 10 messages

    for m in recent_messages:
        if m.id == exclude_message_id:
            continue

        history.append(
            {
                "sender": m.sender,
                "content": (m.content or "")[:500],   # max 500 chars
            }
        )

        if (
            m.draft_status in ("pending", "approved")
            and (m.edited_draft or m.draft_reply)
        ):
            history.append(
                {
                    "sender": "ai",
                    "content": (m.edited_draft or m.draft_reply)[:500],
                }
            )

    return history
