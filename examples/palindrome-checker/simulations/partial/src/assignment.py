"""Partial simulated submission: checks raw reversed text only."""


def is_palindrome(text: str) -> bool:
    return text == text[::-1]
