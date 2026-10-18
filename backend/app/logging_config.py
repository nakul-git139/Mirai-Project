from __future__ import annotations
import logging
import re
from typing import Set

# In-memory registry of secret patterns and registered keys to redact
_REGISTERED_SECRETS: Set[str] = set()

API_KEY_REGEX = re.compile(
    r"(sk-[a-zA-Z0-9_\-]{20,}|AIza[0-9A-Za-z-_]{35}|ant-[a-zA-Z0-9_\-]{20,})",
    re.IGNORECASE,
)


def register_secret_for_redaction(secret: str) -> None:
    if secret and len(secret.strip()) > 4:
        _REGISTERED_SECRETS.add(secret.strip())


class SensitiveDataFilter(logging.Filter):
    """
    Log filter that ensures no registered secret or standard API key
    pattern is printed to logs or standard output.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.sanitize(record.msg)
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(self.sanitize(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        return True

    @classmethod
    def sanitize(cls, text: str) -> str:
        if not isinstance(text, str):
            return text

        # Redact regex patterns
        text = API_KEY_REGEX.sub("[REDACTED_API_KEY]", text)

        # Redact exact registered secrets
        for secret in _REGISTERED_SECRETS:
            if secret in text:
                text = text.replace(secret, "[REDACTED_SECRET]")

        return text


def setup_secure_logging() -> None:
    sanitizer = SensitiveDataFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(sanitizer)
    
    # Also attach to uvicorn loggers
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logger = logging.getLogger(logger_name)
        logger.addFilter(sanitizer)
