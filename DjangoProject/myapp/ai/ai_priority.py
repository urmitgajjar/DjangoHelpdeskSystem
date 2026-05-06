import json
import logging
import re
from urllib import error, request

from django.conf import settings


logger = logging.getLogger(__name__)

ALLOWED_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "URGENT"}

URGENT_KEYWORDS = {
    "outage", "down", "breach", "security incident", "data loss", "critical",
    "production down", "production server", "server down", "service down",
    "all users", "cannot login", "payment failed", "payroll blocked",
}
HIGH_KEYWORDS = {
    "blocked", "cannot access", "failed", "error", "urgent", "invoice", "payroll",
    "database", "latency", "timeout", "customer impact", "major", "production issue",
}
LOW_KEYWORDS = {
    "typo", "ui issue", "alignment", "cosmetic", "enhancement", "suggestion",
    "minor", "small", "formatting",
}


def _extract_priority(raw_text: str) -> str | None:
    if not raw_text:
        return None

                              
    try:
        payload = json.loads(raw_text)
        value = str(payload.get("priority", "")).upper().strip()
        if value in ALLOWED_PRIORITIES:
            return value
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

                                               
    match = re.search(r"\b(LOW|MEDIUM|HIGH|URGENT)\b", raw_text.upper())
    if match:
        value = match.group(1)
        if value in ALLOWED_PRIORITIES:
            return value
    return None


def _extract_reason(raw_text: str) -> str:
    if not raw_text:
        return ""
    try:
        payload = json.loads(raw_text)
        reason = str(payload.get("reason", "")).strip()
        return reason[:400]
    except (json.JSONDecodeError, TypeError, AttributeError):
        return ""


def _safe_trim(value: str, limit: int) -> str:
    value = (value or "").strip()
    return value[:limit]


def _priority_rank(value: str | None) -> int:
    order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "URGENT": 4}
    return order.get((value or "").upper().strip(), 0)


def heuristic_priority_from_text(title: str, description: str) -> dict:
    text = f"{title or ''} {description or ''}".lower()

    urgent_hits = sum(1 for kw in URGENT_KEYWORDS if kw in text)
    high_hits = sum(1 for kw in HIGH_KEYWORDS if kw in text)
    low_hits = sum(1 for kw in LOW_KEYWORDS if kw in text)

    if urgent_hits >= 1:
        priority = "URGENT"
        reason = "Rule-based fallback detected outage/security/business-critical terms."
    elif high_hits >= 2:
        priority = "HIGH"
        reason = "Rule-based fallback detected significant impact/blocking signals."
    elif low_hits >= 1 and high_hits == 0:
        priority = "LOW"
        reason = "Rule-based fallback detected cosmetic/minor request terms."
    else:
        priority = "MEDIUM"
        reason = "Rule-based fallback defaulted to medium impact."

    return {
        "priority": priority,
        "reason": reason,
        "raw_text": "",
        "model": "heuristic-fallback",
        "error": "",
    }


def predict_ticket_priority_with_meta(title: str, description: str) -> dict:
    api_key = str(getattr(settings, "GROQ_API_KEY", "") or "").strip().strip('"').strip("'")
    model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")
    timeout = int(getattr(settings, "GROQ_TIMEOUT_SECONDS", 10))
    user_agent = getattr(
        settings,
        "GROQ_USER_AGENT",
        "HelpDeskAI/1.0 (+https://localhost; django-helpdesk)",
    )

    if not api_key:
        fallback = heuristic_priority_from_text(title, description)
        fallback["error"] = "missing_api_key"
        return fallback
    if not api_key.startswith("gsk_"):
        fallback = heuristic_priority_from_text(title, description)
        fallback["error"] = "invalid_api_key_format"
        logger.warning("Groq API key format invalid. Expected a key starting with 'gsk_'.")
        return fallback

    title = _safe_trim(title, 200)
    description = _safe_trim(description, 2500)

    prompt = (
        "Classify this helpdesk ticket priority into exactly one of: "
        "LOW, MEDIUM, HIGH, URGENT.\n"
        "Return strict JSON only in this format: "
        '{"priority":"LOW|MEDIUM|HIGH|URGENT","reason":"short reason"}.\n'
        "Use this rubric strictly:\n"
        "- URGENT: Production/service down, security breach, data loss, all users blocked.\n"
        "- HIGH: Major business impact, key workflows blocked for many users.\n"
        "- MEDIUM: Partial impact/workaround exists.\n"
        "- LOW: Cosmetic/minor enhancement.\n\n"
        f"Title: {title}\n"
        f"Description: {description}"
    )

    url = "https://api.groq.com/openai/v1/chat/completions"
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You classify helpdesk ticket priorities and return strict JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 80,
        "response_format": {"type": "json_object"},
    }

    req = request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": user_agent,
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        try:
            error_body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            error_body = ""
        last_error = f"HTTP {exc.code}: {exc.reason}"
        if error_body:
            last_error = f"{last_error} | {error_body[:500]}"
        logger.warning("Groq priority prediction failed: %s", last_error)
        fallback = heuristic_priority_from_text(title, description)
        fallback["error"] = last_error
        return fallback
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        last_error = str(exc)
        logger.warning("Groq priority prediction failed: %s", last_error)
        fallback = heuristic_priority_from_text(title, description)
        fallback["error"] = last_error or "prediction_failed"
        return fallback

    try:
        choice = result.get("choices", [])[0]
        message = choice.get("message", {})
        text = message.get("content", "")

        if not text:
            raise ValueError("Empty response text")

    except Exception as exc:
        logger.warning(
            "Groq response format unexpected for priority prediction: %s | Full response: %s",
            exc,
            result,
        )
        fallback = heuristic_priority_from_text(title, description)
        fallback["error"] = "invalid_response_format"
        return fallback

    model_priority = _extract_priority(text)
    heuristic = heuristic_priority_from_text(title, description)
    heuristic_priority = heuristic.get("priority")
    final_priority = model_priority

                                                                                          
    if _priority_rank(heuristic_priority) >= 3 and _priority_rank(model_priority) < _priority_rank(heuristic_priority):
        final_priority = heuristic_priority

    return {
        "priority": final_priority,
        "reason": _extract_reason(text),
        "raw_text": _safe_trim(text, 2000),
        "model": model,
        "error": "",
    }


def predict_ticket_priority(title: str, description: str) -> str | None:
    return predict_ticket_priority_with_meta(title=title, description=description).get("priority")
