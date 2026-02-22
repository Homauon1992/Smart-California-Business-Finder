import re
from typing import Optional


EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)

# Accepts: (123) 456-7890, 123-456-7890, 1234567890, +1 123-456-7890
US_PHONE_REGEX = re.compile(
    r"^(?:\+1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}$"
)


def normalize_us_phone(value: str) -> Optional[str]:
    """Normalize various US phone formats to +1XXXXXXXXXX."""
    if not value:
        return None

    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None

    formatted = f"+1{digits}"
    if is_valid_us_phone(formatted):
        return formatted
    return None


def is_valid_us_phone(value: str) -> bool:
    if not value:
        return False

    if value.startswith("+1") and len(value) == 12 and value[2:].isdigit():
        return True
    return bool(US_PHONE_REGEX.match(value.strip()))


def extract_first_valid_email(text: str) -> Optional[str]:
    if not text:
        return None
    matches = EMAIL_REGEX.findall(text)
    for email in matches:
        email_lower = email.lower()
        if email_lower.endswith((".png", ".jpg", ".jpeg", ".svg")):
            continue
        return email_lower
    return None


def is_valid_email(email: str) -> bool:
    return bool(email and EMAIL_REGEX.fullmatch(email.strip()))
