def _build_history(
    conversation: Conversation,
    exclude_message_id: int,
) -> list[dict[str, str]]:
    """
    Build a compact history for the AI.

    Only the most recent messages are sent to the model in order to
    reduce token usage and avoid hitting free-tier limits.
    """

    history: list[dict[str, str]] = []

    messages = sorted(
        conversation.messages,
        key=lambda m: m.timestamp,
    )

    # Keep only the last 10 messages
    recent_messages = messages[-10:]

    for m in recent_messages:
        if m.id == exclude_message_id:
            continue

        history.append(
            {
                "sender": m.sender,
                "content": (m.content or "")[:500],
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
