from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def read_csv_auto(path: Path) -> pd.DataFrame:
    """Try common separators (comma/semicolon/tab)."""
    for sep in [",", ";", "\t"]:
        df = pd.read_csv(path, sep=sep)
        if df.shape[1] > 1:
            return df
    # fallback (pandas default)
    return pd.read_csv(path)


def find_target_column(df: pd.DataFrame) -> str:
    candidates = ["target", "Target", "outcome", "Outcome", "label", "Label", "class", "Class"]
    for c in candidates:
        if c in df.columns:
            return c
    # also try case-insensitive match
    lowered = {c.lower(): c for c in df.columns}
    if "target" in lowered:
        return lowered["target"]
    raise ValueError(f"Could not find target column. Columns are: {list(df.columns)}")


def make_binary_target(series: pd.Series) -> pd.Series:
    """
    Convert target to binary:
    - Dropout -> 1
    - Enrolled/Graduate -> 0
    Handles string or numeric encodings.
    """
    if series.dtype == object:
        s = series.astype(str).str.strip().str.lower()
        mapping = {"dropout": 1, "enrolled": 0, "graduate": 0}
        if not set(s.unique()).issubset(set(mapping.keys())):
            # if unexpected labels, still try "drop" keyword
            return s.apply(lambda x: 1 if "drop" in x else 0).astype(int)
        return s.map(mapping).astype(int)

    # numeric case: assume the "worst" class is dropout.
    # If values are 0/1 already -> keep.
    uniq = sorted(series.dropna().unique().tolist())
    if set(uniq).issubset({0, 1}):
        return series.fillna(0).astype(int)

    # If 0/1/2 (or similar), we treat the minimum as "Dropout" only if you know that.
    # Safer heuristic: treat the smallest value as dropout only if there are exactly 3 classes.
    # Otherwise treat the maximum as dropout.
    if len(uniq) == 3:
        dropout_value = uniq[0]
    else:
        dropout_value = uniq[-1]
    return (series == dropout_value).astype(int)


def minmax_scale_numeric(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    out = df.copy()
    for c in numeric_cols:
        col = out[c].astype(float)
        mn, mx = col.min(), col.max()
        if pd.isna(mn) or pd.isna(mx) or mn == mx:
            out[c] = 0.0
        else:
            out[c] = (col - mn) / (mx - mn)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=str, required=True, help="Path to raw UCI CSV")
    parser.add_argument("--out", type=str, default="data/dropout.csv", help="Output path (relative to backend/)")
    parser.add_argument("--numeric-only", action="store_true", help="Keep only numeric features (recommended for your current demo predictor).")
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parents[1]
    raw_path = (backend_dir / args.raw).resolve()
    out_path = (backend_dir / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = read_csv_auto(raw_path)

    target_col = find_target_column(df)
    df["target"] = make_binary_target(df[target_col])
    if target_col != "target":
        df = df.drop(columns=[target_col])

    # Optional: drop non-numeric columns so your current demo predictor (random 0..1 features) stays consistent
    if args.numeric_only:
        keep = df.select_dtypes(include=["number"]).columns.tolist()
        df = df[keep]

    # Scale numeric features to 0..1 so random demo inputs are in the same range as training data
    df = minmax_scale_numeric(df)

    df.to_csv(out_path, index=False)
    print(f"Saved prepared dataset to: {out_path}")
    print(f"Shape: {df.shape}, target mean(dropout rate): {df['target'].mean():.3f}")


if __name__ == "__main__":
    main()
