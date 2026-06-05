"""Standalone runner: load numeric_math_guess puzzles from a CSV and generate
chain-of-thought reasoning for each row.

Usage (simple):
    python run_equation_numeric.py

    By default it looks for  numeric_math_guess_puzzles.csv  next to this
    script.  Override with a positional argument:

    python run_equation_numeric.py /path/to/your/puzzles.csv

    Optionally specify the output path as a second argument:

    python run_equation_numeric.py puzzles.csv output_cot.csv

Output:
    A CSV named  <input_stem>_cot.csv  written to the same folder as the
    input file (or the current directory if that folder is not writable).
    Extra columns added:
        - cot       : full chain-of-thought text (None when no rule found)
        - predicted : final answer extracted from the cot
        - correct   : True/False comparison against the 'answer' column

Expected CSV columns: id, prompt, answer, category
Prompt format (Alice's Wonderland style):
    "...Below are a few examples:\\n79-12 = 67\\n...\\nNow, determine the result for: 06@77"
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Make sure store_types and equation_numeric are importable when the runner
# is launched from a different working directory.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from store_types import Example, Problem                 # noqa: E402
#from equation_numeric import reasoning_equation_numeric  # noqa: E402
#from equation_numeric1 import reasoning_equation_numeric
from equation_numeric2 import reasoning_equation_numeric

# ---------------------------------------------------------------------------
# Prompt parser
# ---------------------------------------------------------------------------
_EXAMPLE_LINE_RE = re.compile(r"^(.+?)\s*=\s*(.+)$")
_QUESTION_RE = re.compile(
    r"Now,\s+determine\s+the\s+result\s+for:\s*(.+)$", re.IGNORECASE
)
_EXAMPLES_HEADER_RE = re.compile(r"Below are a few examples:\s*", re.IGNORECASE)


def parse_prompt(prompt: str) -> tuple[list[Example], str] | None:
    """Extract (examples, question) from an Alice's Wonderland prompt string.

    Returns None if the prompt cannot be parsed.
    """
    header_match = _EXAMPLES_HEADER_RE.search(prompt)
    if not header_match:
        return None
    body = prompt[header_match.end():]

    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]

    examples: list[Example] = []
    question: str | None = None

    for line in lines:
        q_m = _QUESTION_RE.match(line)
        if q_m:
            question = q_m.group(1).strip()
            continue
        ex_m = _EXAMPLE_LINE_RE.match(line)
        if ex_m:
            examples.append(Example(ex_m.group(1).strip(), ex_m.group(2).strip()))

    if not examples or question is None:
        return None
    return examples, question


def row_to_problem(row: pd.Series) -> Problem | None:
    """Convert a CSV row into a Problem object."""
    parsed = parse_prompt(str(row["prompt"]))
    if parsed is None:
        return None
    examples, question = parsed
    return Problem(
        id=str(row["id"]),
        category="equation_numeric_guess",
        examples=examples,
        question=question,
        answer=str(row["answer"]),
        prompt=str(row["prompt"]),
    )


# ---------------------------------------------------------------------------
# Output path helper
# ---------------------------------------------------------------------------

def _resolve_output(csv_path: Path, override: str | Path | None) -> Path:
    """Return a writable output path for the results CSV."""
    if override is not None:
        return Path(override).resolve()
    # Try to write next to the input file; fall back to current directory.
    candidate = csv_path.parent / (csv_path.stem + "_cot.csv")
    try:
        candidate.touch(exist_ok=True)
        return candidate
    except OSError:
        return Path.cwd() / (csv_path.stem + "_cot.csv")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(csv_path: str | Path, out_path: str | Path | None = None) -> None:
    csv_path = Path(csv_path).resolve()
    if not csv_path.exists():
        print(f"[ERROR] File not found: {csv_path}")
        sys.exit(1)

    print(f"Loading: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"  {len(df)} rows found.")

    cot_col:       list[str | None]  = []
    predicted_col: list[str | None]  = []
    correct_col:   list[bool | None] = []

    for idx, row in df.iterrows():
        problem = row_to_problem(row)
        if problem is None:
            print(f"  [{idx}] SKIP — could not parse prompt for id={row.get('id', '?')}")
            cot_col.append(None)
            predicted_col.append(None)
            correct_col.append(None)
            continue

        cot = reasoning_equation_numeric(problem)

        # Extract final answer from the last \boxed{...} in the CoT
        predicted: str | None = None
        if cot:
            box_matches = re.findall(r"\\boxed\{([^}]*)\}", cot)
            if box_matches:
                predicted = box_matches[-1].strip()

        expected = str(row["answer"]).strip()
        is_correct: bool | None = (
            predicted == expected if predicted is not None else None
        )

        status = "✓" if is_correct else ("✗" if is_correct is False else "?")
        print(
            f"  [{idx}] id={row['id']}  "
            f"expected={expected}  predicted={predicted}  {status}"
        )

        cot_col.append(cot)
        predicted_col.append(predicted)
        correct_col.append(is_correct)

    df["cot"]       = cot_col
    df["predicted"] = predicted_col
    df["correct"]   = correct_col

    final_out = _resolve_output(csv_path, out_path)
    df.to_csv(final_out, index=False)
    print(f"\nOutput written to: {final_out}")

    answered  = sum(1 for v in correct_col if v is not None)
    correct_n = sum(1 for v in correct_col if v is True)
    if answered:
        print(f"Accuracy: {correct_n}/{answered}  ({100 * correct_n / answered:.1f}%)")
    else:
        print("No rows were answered.")


if __name__ == "__main__":
    # -----------------------------------------------------------------------
    # Argument parsing (intentionally simple — no argparse dependency needed)
    #   argv[1]  — path to input CSV          (optional, defaults shown below)
    #   argv[2]  — path for output CSV         (optional)
    # -----------------------------------------------------------------------
    default_csv = r"C:\Users\Ashutosh Agarwal\Downloads\numeric_math_guess_puzzles (1).csv"
    default_out_csv = r"numeric_math_guess_cot_out.csv"

    input_csv  = Path(sys.argv[1]) if len(sys.argv) > 1 else default_csv
    output_csv = default_out_csv  # Path(sys.argv[2]) if len(sys.argv) > 2 else default_out_csv

    main(input_csv, output_csv)
