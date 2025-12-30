from __future__ import annotations

import argparse
import os
from pathlib import Path

import joblib
import pandas as pd
from pandas.errors import ParserError


def _set_loky_cpu_default():
    # Only set a default if user didn't already configure it
    if "LOKY_MAX_CPU_COUNT" not in os.environ:
        os.environ["LOKY_MAX_CPU_COUNT"] = os.environ.get("QUICK_TEST_MAX_CPU_COUNT", "8")


def read_csv_auto(path: Path) -> pd.DataFrame:
    """
    Tries common delimiters first; if none work, falls back to pandas auto-detection.
    Raises a clear error if everything fails.
    """
    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    last_exc: Exception | None = None

    for sep in [",", ";", "\t", "|"]:
        try:
            df_try = pd.read_csv(path, sep=sep)
            if df_try.shape[1] > 1:
                return df_try
        except (ParserError, UnicodeDecodeError, ValueError) as exc:
            last_exc = exc
            continue

    # pandas "auto" delimiter detection
    try:
        return pd.read_csv(path, sep=None, engine="python")
    except Exception as exc:
        msg = (
            f"Failed to read CSV '{path}'. Tried delimiters [',',';','\\t','|'] and "
            "also pandas auto-detection (sep=None, engine='python')."
        )
        raise ValueError(msg) from (last_exc or exc)


def norm_col(s: str) -> str:
    # normalize spaces and case
    return " ".join(str(s).replace("\u00a0", " ").strip().split()).lower()


def main() -> int:
    _set_loky_cpu_default()

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="models/risk_model.joblib", help="Path to trained model bundle")
    parser.add_argument("--data", type=str, default="data/UCI_data.csv", help="Path to CSV dataset")
    args = parser.parse_args()

    model_path = Path(args.model)
    data_path = Path(args.data)

    if not model_path.is_file():
        print(f"Model bundle not found: {model_path}")
        print("Train first, e.g.: python scripts/train_lightgbm.py --data data/UCI_data.csv --outdir models")
        return 1

    try:
        bundle = joblib.load(model_path)
    except Exception as exc:
        print(f"Failed to load model bundle '{model_path}': {exc}")
        return 1

    model = bundle["model"]
    cols = bundle["feature_columns"]
    cat_cols = set(bundle.get("categorical_features", []))

    try:
        df = read_csv_auto(data_path)
    except Exception as exc:
        print(f"{exc}")
        return 1

    df.columns = [str(c) for c in df.columns]

    # detect target col like training did
    target_col = "Target" if "Target" in df.columns else ("target" if "target" in df.columns else df.columns[-1])
    X = df.drop(columns=[target_col], errors="ignore")

    # build a rename map using normalized names
    rename_map = {norm_col(c): c for c in X.columns}
    aligned = pd.DataFrame(index=X.index)

    missing: list[str] = []
    for want in cols:
        key = norm_col(want)
        if key in rename_map:
            aligned[want] = X[rename_map[key]]
        else:
            missing.append(want)
            aligned[want] = "unknown" if want in cat_cols else 0.0

    if missing:
        print("Missing columns filled with defaults (first 10):", missing[:10])
        print("Total missing filled:", len(missing))

    # enforce categorical dtype and numeric coercion
    for c in aligned.columns:
        if c in cat_cols:
            aligned[c] = aligned[c].astype(str).str.strip().astype("category")
        else:
            aligned[c] = pd.to_numeric(aligned[c], errors="coerce").fillna(0.0)

    row = aligned.head(1)
    proba = model.predict_proba(row)[:, 1][0]
    print("Predicted dropout risk probability:", float(proba))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
