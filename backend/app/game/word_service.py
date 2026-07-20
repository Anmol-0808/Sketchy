import json
import random
from pathlib import Path


WORD_CATEGORIES = {
    "animals": [
        "dog", "cat", "elephant", "lion", "tiger", "bear", "panda", "giraffe", "zebra", "monkey",
        "kangaroo", "penguin", "owl", "eagle", "parrot", "shark", "whale", "dolphin", "octopus", "frog",
        "turtle", "snake", "crocodile", "butterfly", "bee", "spider", "rabbit", "horse", "cow", "duck",
    ],
    "food": [
        "apple", "banana", "pizza", "burger", "sandwich", "taco", "noodles", "pancake", "donut", "cookie",
        "ice cream", "coffee", "tea", "cake", "candy", "sushi", "bread", "cheese", "egg", "salad",
    ],
    "objects": [
        "umbrella", "camera", "bicycle", "pencil", "backpack", "computer", "phone", "clock", "chair", "table",
        "lamp", "key", "lock", "watch", "glasses", "helmet", "book", "scissors", "hammer", "ladder",
    ],
    "places": [
        "castle", "house", "school", "hospital", "library", "museum", "airport", "farm", "beach", "island",
        "mountain", "river", "forest", "desert", "volcano", "cave", "park", "zoo", "hotel", "station",
    ],
    "actions": [
        "running", "jumping", "dancing", "singing", "sleeping", "cooking", "painting", "fishing", "swimming", "climbing",
        "reading", "writing", "driving", "flying", "skating", "surfing", "digging", "throwing", "catching", "waving",
    ],
}


class WordService:
    def __init__(self) -> None:
        path = Path(__file__).resolve().parents[1] / "data" / "words.json"
        self.words = json.loads(path.read_text(encoding="utf-8"))

    def choices(self, count: int, categories: list[str] | None = None, custom_words: list[str] | None = None) -> list[str]:
        pool = self.pool(categories, custom_words)
        count = min(count, len(pool))
        return random.sample(pool, count)

    def pool(self, categories: list[str] | None = None, custom_words: list[str] | None = None) -> list[str]:
        selected = [category for category in categories or [] if category in WORD_CATEGORIES]
        words = []
        if selected:
            for category in selected:
                words.extend(WORD_CATEGORIES[category])
        else:
            words.extend(self.words)
        words.extend(custom_words or [])
        return sorted(set(words))

    def replace_words(self, words: list[str]) -> None:
        clean_words = [word.strip().lower() for word in words if word.strip()]
        if clean_words:
            self.words = clean_words


word_service = WordService()
