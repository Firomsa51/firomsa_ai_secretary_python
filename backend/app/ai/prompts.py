"""
Prompt management — all system and user prompt templates live here.

Keeping prompts in one place makes it easy to iterate on personality,
tone, and instruction sets without touching business logic.
"""

from string import Template


# ── System prompts ────────────────────────────────────────────────────────────

SYSTEM_BASE = """\
You are Firomsa, a highly capable and discreet personal AI secretary.
You help your owner manage their Telegram communications professionally.

Your principles:
- Be concise, accurate, and professional.
- Respect privacy — never share information beyond what is necessary.
- Adapt your tone to match the conversation context.
- When uncertain, ask a clarifying question rather than guessing.
- Write in the language the owner uses in this conversation unless instructed otherwise.
"""

SYSTEM_REPLY_DRAFTER = """\
You are Firomsa, drafting a reply on behalf of your owner.
Your goal is to write a reply that sounds natural, professional, and
matches the owner's communication style.

Rules:
- Draft only — do NOT add "Draft:" or similar prefixes.
- Keep it concise unless the context calls for a detailed response.
- Mirror the formality level of the incoming message.
- If information needed for the reply is missing, state what is needed.
"""

SYSTEM_CATEGORISER = """\
You are Firomsa, analysing a Telegram conversation.
Classify the conversation and return ONLY valid JSON matching this schema:

{
  "category": "<work|personal|networking|support|spam|other>",
  "priority":  "<low|normal|high|urgent>",
  "summary":   "<one sentence summary of the conversation topic>"
}
"""


# ── User prompt templates ─────────────────────────────────────────────────────

_DRAFT_REPLY_TEMPLATE = Template(
    "Conversation so far:\n$history\n\nLatest message from $sender:\n$latest_message\n\n"
    "Draft a reply from the owner's perspective."
)

_CATEGORISE_TEMPLATE = Template(
    "Conversation history:\n$history\n\nClassify this conversation."
)

_MEMORY_INJECT_TEMPLATE = Template(
    "Relevant facts about this user:\n$memories\n\n$base_prompt"
)


# ── Builder helpers ───────────────────────────────────────────────────────────

def build_draft_reply_messages(
    history: str,
    sender: str,
    latest_message: str,
    memories: str | None = None,
) -> list[dict[str, str]]:
    """
    Return a messages list ready for AIProvider.chat() that asks the model
    to draft a reply.
    """
    system = SYSTEM_REPLY_DRAFTER
    if memories:
        system = _MEMORY_INJECT_TEMPLATE.substitute(
            memories=memories, base_prompt=system
        )

    user_content = _DRAFT_REPLY_TEMPLATE.substitute(
        history=history,
        sender=sender,
        latest_message=latest_message,
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


def build_categorise_messages(history: str) -> list[dict[str, str]]:
    """
    Return a messages list ready for AIProvider.chat() that asks the model
    to categorise and summarise the conversation.
    """
    return [
        {"role": "system", "content": SYSTEM_CATEGORISER},
        {"role": "user", "content": _CATEGORISE_TEMPLATE.substitute(history=history)},
    ]


def format_history(messages: list[dict[str, str]]) -> str:
    """
    Convert a list of {"sender": ..., "content": ...} dicts into a
    readable conversation string for prompt injection.
    """
    lines: list[str] = []
    for m in messages:
        role = m.get("sender", "unknown").upper()
        lines.append(f"[{role}]: {m.get('content', '')}")
    return "\n".join(lines)
