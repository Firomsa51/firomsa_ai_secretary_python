@staticmethod
def _parse_classification(raw: str) -> dict:
    """
    Parse JSON even if the LLM wraps it with explanations or markdown.
    """
    import json
    import logging

    logger = logging.getLogger(__name__)

    if not raw:
        return {}

    try:
        cleaned = raw.strip()

        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1]

        if "```" in cleaned:
            cleaned = cleaned.split("```", 1)[0]

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start != -1 and end != -1:
            cleaned = cleaned[start:end + 1]

        return json.loads(cleaned)

    except Exception as exc:
        logger.exception("Failed to parse classification JSON")
        logger.error("RAW RESPONSE:\n%s", raw)
        return {}
