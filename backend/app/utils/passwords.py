"""Bcrypt has a byte limit, not a character limit. Never truncate passwords."""


def validate_password_bytes(value: str) -> str:
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("Password must contain valid Unicode characters") from None
    if not encoded or len(encoded) > 72 or b"\0" in encoded:
        raise ValueError(
            "Password must be 1–72 UTF-8 bytes and contain no null characters"
        )
    return value
