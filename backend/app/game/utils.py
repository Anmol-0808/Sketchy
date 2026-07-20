import re


def normalize_guess(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def mask_word(word: str) -> str:
    return " ".join("_" if char != " " else "/" for char in word)


def hint_word(word: str, revealed_count: int) -> str:
    letters = [index for index, char in enumerate(word) if char != " "]
    revealed = set(letters[: max(0, min(revealed_count, len(letters)))])
    return " ".join(char if index in revealed else ("/" if char == " " else "_") for index, char in enumerate(word))


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
