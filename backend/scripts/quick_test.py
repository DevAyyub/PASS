from pathlib import Path
import joblib
import pandas as pd
import os
os.environ["LOKY_MAX_CPU_COUNT"] = "8"


def read_csv_auto(path: Path) -> pd.DataFrame:
    for sep in [",", ";", "\t", "|"]:
        try:
            df_try = pd.read_csv(path, sep=sep)
            if df_try.shape[1] > 1:
                return df_try
        except Exception:
            pass
    return pd.read_csv(path, sep=None, engine="python")


def norm_col(s: str) -> str:
    # normalize spaces and case
    return " ".join(str(s).replace("\u00a0", " ").strip().split()).lower()


def main():
    bundle = joblib.load(Path("models") / "risk_model.joblib")
    model = bundle["model"]
    cols = bundle["feature_columns"]
    cat_cols = set(bundle.get("categorical_features", []))

    data_path = Path("data") / "UCI_data.csv"
    df = read_csv_auto(data_path)
    df.columns = [str(c) for c in df.columns]

    # detect target col like training did
    target_col = "Target" if "Target" in df.columns else ("target" if "target" in df.columns else df.columns[-1])
    X = df.drop(columns=[target_col], errors="ignore")

    # build a rename map using normalized names
    rename_map = {norm_col(c): c for c in X.columns}
    aligned = pd.DataFrame(index=X.index)

    missing = []
    for want in cols:
        key = norm_col(want)
        if key in rename_map:
            aligned[want] = X[rename_map[key]]
        else:
            missing.append(want)
            # create a safe default
            aligned[want] = "unknown" if want in cat_cols else 0

    # quick debug prints
    if missing:
        print("⚠️ Missing columns filled with defaults (first 10):", missing[:10])
        print("Total missing filled:", len(missing))

    # IMPORTANT: make categorical columns "category" type like training
    for c in aligned.columns:
        if c in cat_cols:
            aligned[c] = aligned[c].astype(str).str.strip().astype("category")

    row = aligned.head(1)
    proba = model.predict_proba(row)[:, 1][0]
    print("✅ Predicted dropout risk probability:", float(proba))


if __name__ == "__main__":
    main()
