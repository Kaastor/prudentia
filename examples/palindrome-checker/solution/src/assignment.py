"""Teacher-only implementation for the palindrome checker assignment."""


def is_palindrome(text: str) -> bool:
    """Return whether text is a palindrome after ignoring case and punctuation."""
    normalized = "".join(character.lower() for character in text if character.isalnum())
    return normalized == normalized[::-1]
