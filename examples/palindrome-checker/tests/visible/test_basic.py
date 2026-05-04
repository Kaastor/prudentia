from assignment import is_palindrome


def test_simple_palindrome_word():
    assert is_palindrome("racecar") is True


def test_simple_non_palindrome_word():
    assert is_palindrome("python") is False


def test_case_is_ignored():
    assert is_palindrome("Level") is True


def test_empty_string_is_palindrome():
    assert is_palindrome("") is True
