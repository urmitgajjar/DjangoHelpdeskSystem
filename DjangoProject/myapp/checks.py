from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def ai_config_checks(app_configs, **kwargs):
    issues = []

    timeout = getattr(settings, "GROQ_TIMEOUT_SECONDS", 10)
    retries = getattr(settings, "GROQ_MAX_RETRIES", 1)
    api_key = str(getattr(settings, "GROQ_API_KEY", "") or "").strip().strip('"').strip("'")

    if not isinstance(timeout, int) or timeout <= 0:
        issues.append(
            Error(
                "GROQ_TIMEOUT_SECONDS must be a positive integer.",
                id="myapp.E001",
            )
        )

    if not isinstance(retries, int) or retries < 0:
        issues.append(
            Error(
                "GROQ_MAX_RETRIES must be a non-negative integer.",
                id="myapp.E002",
            )
        )

    if isinstance(retries, int) and retries > 5:
        issues.append(
            Warning(
                "GROQ_MAX_RETRIES is high; this may slow ticket creation noticeably.",
                id="myapp.W001",
            )
        )

    if not api_key:
        issues.append(
            Warning(
                "GROQ_API_KEY is not set; AI priority prediction will be skipped.",
                id="myapp.W002",
            )
        )
    elif not api_key.startswith("gsk_"):
        issues.append(
            Warning(
                "GROQ_API_KEY format looks invalid; expected it to start with 'gsk_'.",
                id="myapp.W003",
            )
        )

    return issues
