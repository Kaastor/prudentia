# Palindrome checker

## Learning objectives
- Write pure functions with clear input/output behavior
- Handle common string edge cases

## Task description
Write a function named `is_palindrome(text: str) -> bool` in `starter/src/assignment.py`.
The function should decide whether the supplied text reads the same forward and backward after normalizing it.

## Input and output expectations
- Input: a Python string named `text`.
- Output: `True` when the normalized text is a palindrome, otherwise `False`.
- Normalization means ignoring case and ignoring non-alphanumeric characters such as spaces and punctuation.
- The empty string counts as a palindrome after normalization.

## Constraints
- Use only the Python standard library.
- Implement a pure function with no input prompts or print calls.

## Examples
- `is_palindrome("racecar")` returns `True`.
- `is_palindrome("Race car!")` returns `True`.
- `is_palindrome("python")` returns `False`.

## Submission instructions
Edit only `starter/src/assignment.py` unless your teacher gives different instructions.
Run the visible pytest suite before submitting your work.
