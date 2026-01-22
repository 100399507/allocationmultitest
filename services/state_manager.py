import json
from pathlib import Path

DATA_PATH = Path("data")

def load_json(filename):
    with open(DATA_PATH / filename) as f:
        return json.load(f)

def save_json(filename, data):
    with open(DATA_PATH / filename, "w") as f:
        json.dump(data, f, indent=2)
