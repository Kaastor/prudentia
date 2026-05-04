from assignment import is_palindrome


def test_spaces_and_punctuation_are_ignored():
    assert is_palindrome("A man, a plan, a canal: Panama!") is True


def test_digits_are_considered_alphanumeric():
    assert is_palindrome("12ab!!a21") is True


def test_mixed_text_that_is_not_palindrome():
    assert is_palindrome("palindrome checker") is False


def test_only_punctuation_normalizes_to_empty():
    assert is_palindrome("... !!!") is True


def test_matching_ends_are_not_enough():
    assert is_palindrome("abca") is False
