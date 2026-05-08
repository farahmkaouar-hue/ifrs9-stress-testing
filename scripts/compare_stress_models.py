import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.stress_model_comparison import compare_stress_testing_models


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs"


if __name__ == "__main__":
    path = OUTPUT_DIR / "ecl_baseline.parquet"
    if not path.exists():
        path = OUTPUT_DIR / "loan_clean.parquet"
    if not path.exists():
        raise FileNotFoundError("Executez d'abord le preprocessing/ECL baseline.")

    try:
        df = pd.read_parquet(path)
    except ImportError as exc:
        raise SystemExit(
            "Lecture Parquet impossible: installez pyarrow/fastparquet ou "
            "recreez le .venv avec `pip install -r requirements.txt`."
        ) from exc
    scored, champion = compare_stress_testing_models(df)
    print(scored.to_string(index=False))
    print(f"\nChampion stress testing: {champion}")
