import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.validation_report import generate_validation_report


if __name__ == "__main__":
    path = generate_validation_report()
    print(f"Rapport genere : {path}")
