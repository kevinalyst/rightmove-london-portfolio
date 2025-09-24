import argparse
import json
import pandas as pd


def parse_args():
    p = argparse.ArgumentParser(description="Convert CSV to NDJSON and copy CSV")
    p.add_argument("--input", required=True, help="Input CSV path")
    p.add_argument("--csv-out", required=True, help="Output CSV path")
    p.add_argument("--ndjson-out", required=True, help="Output NDJSON path")
    return p.parse_args()


def main():
    args = parse_args()
    df = pd.read_csv(args.input)
    df.to_csv(args.csv_out, index=False)
    with open(args.ndjson_out, "w", encoding="utf-8") as f:
        for _, r in df.iterrows():
            obj = {k: (None if pd.isna(v) else v) for k, v in r.items()}
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"Created {args.csv_out} and {args.ndjson_out} (rows={len(df)})")


if __name__ == "__main__":
    main()


