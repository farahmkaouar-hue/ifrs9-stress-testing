import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_prep import OUTPUT_DIR, PREPROCESSING_REPORTS_DIR, save_clean_data_quality_reports  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerer les rapports EDA/preprocessing depuis le parquet nettoye."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=OUTPUT_DIR / "loan_clean.parquet",
        help="Chemin du parquet nettoye.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PREPROCESSING_REPORTS_DIR,
        help="Dossier de sortie des rapports CSV.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Dataset nettoye introuvable: {args.input}. Lancez d'abord 02_Preprocessing.ipynb."
        )

    df = pd.read_parquet(args.input)
    paths = save_clean_data_quality_reports(df, reports_dir=args.output_dir)

    print(f"{len(paths)} rapports EDA/preprocessing generes dans {args.output_dir}")
    for name, path in sorted(paths.items()):
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
