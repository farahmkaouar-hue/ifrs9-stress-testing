import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.dfast_report import generate_dfast_report


if __name__ == "__main__":
    path = generate_dfast_report()
    print(f"Rapport DFAST-like genere : {path}")
