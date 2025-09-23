from __future__ import annotations

import glob
import os
import sys


def main(argv: list[str]) -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--dir", required=True, help="Path to sql directory")
    args = p.parse_args(argv)

    sql_files = sorted(
        [
            *glob.glob(os.path.join(args.dir, "*.sql")),
            *glob.glob(os.path.join(args.dir, "views", "*.sql")),
        ]
    )
    if not sql_files:
        print("No SQL files found.")
        return 0

    # Mock: print out filenames; users should paste into Snowflake Worksheet
    print("Apply these SQL files in order:")
    for f in sql_files:
        print(f" - {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


