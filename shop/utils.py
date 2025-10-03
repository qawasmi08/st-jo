import re
from typing import Optional

from django.core.exceptions import ValidationError


PHONE_PATTERN = re.compile(r"^\+9627\d{8}$")


def normalize_jordan_phone(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    digits = re.sub(r"[^0-9+]", "", value)
    if digits.startswith("+962"):
        normalized = "+962" + digits[4:]
    elif digits.startswith("00962"):
        normalized = "+962" + digits[5:]
    elif digits.startswith("07"):
        normalized = "+962" + digits[1:]
    elif digits.startswith("7") and len(digits) == 9:
        normalized = "+962" + digits
    else:
        raise ValidationError("رقم الهاتف الأردني غير صالح")

    if not PHONE_PATTERN.match(normalized):
        raise ValidationError("رقم الهاتف الأردني غير صالح")
    return normalized
