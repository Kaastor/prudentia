"""Misconception simulated submission: checks only first and last normalized characters."""


def is_palindrome(text: str) -> bool:
    normalized = "".join(character.lower() for character in text if character.isalnum())
    if not normalized:
        return True
    return normalized[0] == normalized[-1]
