"""
duplicate_by_q_op.py
--------------------
Reads a CSV file, prompts the user for a duplication count for each unique
value in the Q_op column, duplicates rows accordingly, and saves the result
to a new CSV file.

Usage:
    python duplicate_by_q_op.py [--input PATH] [--output PATH]

Defaults:
    --input   numeric_math_guess_puzzles__1__cot.csv
    --output  duplicated_output.csv
"""

import argparse
import sys
import pandas as pd


# ── CLI arguments ──────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Duplicate CSV rows per unique Q_op value based on user input."
    )
    parser.add_argument(
        "--input",
        default=r"C:\Users\Ashutosh Agarwal\Downloads\numeric_guess_files\reasoning 3\numeric_math_guess_cot_out.csv",
        help="Path to the input CSV file (default: numeric_math_guess_puzzles__1__cot.csv)",
    )
    parser.add_argument(
        "--output",
        default= "Upsampled_data.csv",
        help="Path for the output CSV file (default: duplicated_output.csv)",
    )
    return parser.parse_args()


# ── Helpers ────────────────────────────────────────────────────────────────────

def prompt_count(op_value: str, current_count: int) -> int:
    """
    Ask the user how many times rows with a given Q_op value should appear
    in the output (1 = keep original, 2 = one duplicate added, etc.).
    Keeps re-prompting until a valid positive integer is entered.
    """
    while True:
        raw = input(
            f"  Q_op = '{op_value}'  [{current_count} rows]  "
            f"→ how many times to repeat each row? (≥1): "
        ).strip()
        if raw.isdigit() and int(raw) >= 1:
            return int(raw)
        print("    ⚠  Please enter a whole number ≥ 1.")


def build_output(df: pd.DataFrame, counts: dict[str, int]) -> pd.DataFrame:
    """
    For each Q_op group, repeat its rows <count> times and concatenate
    all groups back together in the original order of first appearance.
    """
    parts: list[pd.DataFrame] = []
    for op_value, group in df.groupby("Q_op", sort=False):
        n = counts[op_value]
        repeated = pd.concat([group] * n, ignore_index=True)
        parts.append(repeated)
    return pd.concat(parts, ignore_index=True)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    # ── Load data ──────────────────────────────────────────────────────────────
    print(f"\n📂  Loading  : {args.input}")
    try:
        df = pd.read_csv(args.input)
    except FileNotFoundError:
        sys.exit(f"❌  File not found: {args.input}")
    except Exception as exc:
        sys.exit(f"❌  Could not read CSV: {exc}")

    if "Q_op" not in df.columns:
        sys.exit("❌  Column 'Q_op' not found in the CSV.")

    print(f"✅  Loaded {len(df):,} rows  |  {df['Q_op'].nunique()} unique Q_op values\n")

    # ── Collect duplication counts from the user ───────────────────────────────
    value_counts = df["Q_op"].value_counts()          # counts per unique value
    unique_ops   = df["Q_op"].unique().tolist()        # preserves first-seen order

    print("─" * 60)
    print(" Enter how many times each row should appear in the output.")
    print(" (Enter 1 to keep original rows unchanged, 2 to double, etc.)")
    print("─" * 60)

    counts: dict[str, int] = {}
    for op in unique_ops:
        counts[op] = prompt_count(op, value_counts[op])

    # ── Build & save output ────────────────────────────────────────────────────
    print("\n⚙️   Building output …")
    result = build_output(df, counts)

    print(f"💾  Saving   : {args.output}")
    try:
        result.to_csv(args.output, index=False)
    except Exception as exc:
        sys.exit(f"❌  Could not write CSV: {exc}")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print(f"{'Q_op':<12} {'Original':>10} {'Multiplier':>12} {'Output rows':>12}")
    print("─" * 60)
    for op in unique_ops:
        orig = value_counts[op]
        mult = counts[op]
        print(f"{op:<12} {orig:>10,} {mult:>12}x {orig * mult:>12,}")
    print("─" * 60)
    print(f"{'TOTAL':<12} {len(df):>10,} {'':>12} {len(result):>12,}")
    print("─" * 60)
    print(f"\n✅  Done!  Output saved to: {args.output}\n")


if __name__ == "__main__":
    main()
