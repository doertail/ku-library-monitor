import json
import os


def load_seen_ids(path: str) -> set:
    """Load set of IDs from JSON file. Returns empty set if file missing or invalid."""
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except json.JSONDecodeError:
        print(f"[WARN] Corrupted JSON in {path}, returning empty set")
        return set()


def save_seen_ids(path: str, seen: set) -> None:
    """Save set of IDs to JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(seen), f)
