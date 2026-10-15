"""Script 13 — Pairwise significance testing for teacher-aligned accuracy.

Computes:
- Paired McNemar test for every model pair at a selected n_examples value.
- Bootstrap confidence intervals (10 000 resamples) for pairwise accuracy differences.

Outputs (all written to <base-output-dir>/analysis/):
- significance_mcnemar__n<N>__parsable_only.csv      — McNemar table (all pairs)
- significance_bootstrap__n<N>__parsable_only.csv     — bootstrap CI table (all pairs)
- significance_summary__n<N>__parsable_only.md        — plain-text summary for paper writing
- significance_mcnemar__n<N>__parsable_only.meta.json — run metadata

Usage example:
    python scripts/13_significance_testing.py \
        --base-output-dir outputs/incremental_in_context_eval_consolidated \
        --n-value 40 \
        --n-bootstrap 10000 \
        --seed 42

Dependencies: pandas, scipy, numpy
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from scipy.stats import chi2


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_ORDER = [
    "anthropic_claude-haiku-4.5",
    "deepseek_deepseek-v3.2",
    "qwen_qwen3.5-397b-a17b",
    "google_gemini-2.5-flash-lite",
    "z-ai_glm-4.7-flash",
    "Qwen_Qwen3-32B",
    "Qwen_Qwen3.5-27B",
]

MODEL_LABELS = {
    "anthropic_claude-haiku-4.5": "Claude Haiku 4.5",
    "deepseek_deepseek-v3.2": "DeepSeek V3.2",
    "qwen_qwen3.5-397b-a17b": "Qwen 3.5 397B A17B",
    "google_gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
    "z-ai_glm-4.7-flash": "GLM 4.7 Flash",
    "Qwen_Qwen3-32B": "Qwen3-32B (local)",
    "Qwen_Qwen3.5-27B": "Qwen3.5-27B (local)",
}


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pairwise McNemar + bootstrap significance testing for teacher-aligned grading accuracy."
    )
    parser.add_argument(
        "--max-dropped-frac",
        type=float,
        default=0.02,
        help=(
            "Abort if any arm loses more than this fraction of its rows when intersecting on the "
            "alignment key. A stray unparsable row is fine; a large loss means the arms are not "
            "the same experiment and must not be compared."
        ),
    )
    parser.add_argument(
        "--base-output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "outputs" / "incremental_in_context_eval_consolidated",
        help="Base output directory (contains runs/ and analysis/).",
    )
    parser.add_argument(
        "--run-name",
        type=str,
        default="",
        help="Explicit consolidated run name. Defaults to latest_run.txt or newest directory.",
    )
    parser.add_argument(
        "--n-value",
        type=int,
        default=40,
        help="n_examples value at which to perform paired tests (default: 40 = protocol ceiling).",
    )
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=10000,
        help="Number of bootstrap resamples (default: 10000).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance level alpha (default: 0.05).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Run resolution
# ---------------------------------------------------------------------------

def resolve_run(base_output_dir: Path, run_name_arg: str) -> tuple[str, Path]:
    runs_root = base_output_dir / "runs"
    if not runs_root.exists():
        raise FileNotFoundError(f"Runs root missing: {runs_root}")
    if run_name_arg.strip():
        run_name = run_name_arg.strip()
    else:
        latest_path = base_output_dir / "latest_run.txt"
        if latest_path.exists():
            token = latest_path.read_text(encoding="utf-8").strip()
            run_name = Path(token).name if token else ""
        else:
            run_name = ""
        if not run_name:
            run_name = sorted([p.name for p in runs_root.iterdir() if p.is_dir()])[-1]
    run_dir = runs_root / run_name
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    return run_name, run_dir


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_predictions(run_dir: Path, model_safe: str) -> pd.DataFrame:
    pred_path = run_dir / "02_predictions" / model_safe / "in_context_predictions.csv"
    if not pred_path.exists():
        raise FileNotFoundError(f"Predictions missing: {pred_path}")
    df = pd.read_csv(pred_path)
    for col in ["n_examples", "parsable", "re_eval_score", "human_answer_correct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def get_binary_outcomes(run_dir: Path, model_safe: str, n_value: int) -> pd.DataFrame:
    """Return one row per parsable prediction at n_value.

    Columns: [task_ordinal, QuestionID, cv_fold, user_id, answer_text, correct].
    Alignment across arms happens on the SEMANTIC key (QuestionID, cv_fold, user_id, answer_text),
    not on task_ordinal and not on row position. task_ordinal is positional within a run and only
    comparable across runs whose task space is byte-identical; it is kept for an integrity check."""
    df = load_predictions(run_dir, model_safe)
    sub = df[(df["n_examples"] == n_value) & (df["parsable"] == 1)].copy()
    if sub.empty:
        raise ValueError(f"No parsable rows at n={n_value} for {model_safe}")
    sub["correct"] = (sub["re_eval_score"] == sub["human_answer_correct"]).astype(int)
    # task_ordinal is unique per run — use it as the alignment key.
    # answer_text is part of the key on purpose: (QuestionID, cv_fold, user_id) has 24 duplicate
    # rows per run, because a student can answer the same question more than once.
    sub = sub[["task_ordinal", "QuestionID", "cv_fold", "user_id", "answer_text", "correct"]].copy()
    sub = sub.sort_values("task_ordinal").reset_index(drop=True)
    return sub


# ---------------------------------------------------------------------------
# Multiple-comparison correction
# ---------------------------------------------------------------------------

def holm_bonferroni(p_values: list[float], alpha: float) -> tuple[list[float], list[bool]]:
    """Holm-Bonferroni step-down correction for a family of m tests.

    Returns:
        p_adjusted: Holm-adjusted p-values (capped at 1.0).
        reject:     Whether each test is significant after correction.

    Algorithm:
        1. Sort tests by raw p-value (ascending), rank 1..m.
        2. Test rank k is rejected iff ALL p_i for i <= k satisfy p_i <= alpha/(m-i+1).
        3. Adjusted p-value for rank k = max over i in 1..k of (m-i+1)*p_i, capped at 1.
    """
    m = len(p_values)
    sorted_idx = sorted(range(m), key=lambda i: p_values[i])
    p_adj = [0.0] * m
    reject = [False] * m

    for rank, idx in enumerate(sorted_idx):
        p_adj[idx] = min(1.0, max((m - r) * p_values[sorted_idx[r]] for r in range(rank + 1)))

    # Reject if adjusted p < alpha; enforce monotonicity: once rejected stays rejected
    # (Holm is step-down: stop rejecting as soon as a test fails)
    stop = False
    for rank, idx in enumerate(sorted_idx):
        if stop or p_adj[idx] >= alpha:
            stop = True
            reject[idx] = False
        else:
            reject[idx] = True

    return p_adj, reject


# ---------------------------------------------------------------------------
# Statistical tests
# ---------------------------------------------------------------------------

def mcnemar_test(a: np.ndarray, b: np.ndarray) -> dict[str, Any]:
    """Compute McNemar's test for two binary arrays of equal length.

    Contingency table (rows=model A, cols=model B):
        correct/correct  |  correct/wrong
        wrong/correct    |  wrong/wrong

    b = discordant pairs where A wrong, B correct
    c = discordant pairs where A correct, B wrong
    Test statistic: chi2 = (|b - c| - 1)^2 / (b + c)   [with continuity correction]
    """
    assert len(a) == len(b), f"Arrays must be same length: {len(a)} vs {len(b)}"
    n00 = int(((a == 0) & (b == 0)).sum())  # both wrong
    n01 = int(((a == 0) & (b == 1)).sum())  # A wrong, B correct
    n10 = int(((a == 1) & (b == 0)).sum())  # A correct, B wrong
    n11 = int(((a == 1) & (b == 1)).sum())  # both correct
    discordant = n01 + n10
    if discordant == 0:
        # No discordant pairs: cannot reject H0, p=1
        return {
            "n_pairs": len(a),
            "n00": n00, "n01": n01, "n10": n10, "n11": n11,
            "discordant": discordant,
            "chi2_statistic": 0.0,
            "p_value": 1.0,
        }
    chi2_stat = (abs(n01 - n10) - 1.0) ** 2 / discordant
    p_value = float(1.0 - chi2.cdf(chi2_stat, df=1))
    return {
        "n_pairs": len(a),
        "n00": n00, "n01": n01, "n10": n10, "n11": n11,
        "discordant": discordant,
        "chi2_statistic": float(chi2_stat),
        "p_value": p_value,
    }


def bootstrap_accuracy_difference(
    a: np.ndarray,
    b: np.ndarray,
    n_bootstrap: int,
    seed: int,
    alpha: float,
) -> dict[str, Any]:
    """Bootstrap CI for the difference in accuracy acc(A) - acc(B).

    Resamples pairs (a_i, b_i) with replacement. Returns the observed difference,
    bootstrap mean, and (alpha/2, 1-alpha/2) percentile interval.
    """
    rng = np.random.default_rng(seed)
    n = len(a)
    obs_diff = float(a.mean() - b.mean())
    diffs = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        diffs[i] = a[idx].mean() - b[idx].mean()
    lo = float(np.percentile(diffs, 100 * alpha / 2))
    hi = float(np.percentile(diffs, 100 * (1 - alpha / 2)))
    return {
        "n_pairs": n,
        "obs_acc_a": float(a.mean()),
        "obs_acc_b": float(b.mean()),
        "obs_diff_a_minus_b": obs_diff,
        "bootstrap_mean_diff": float(diffs.mean()),
        "bootstrap_ci_low": lo,
        "bootstrap_ci_high": hi,
        "alpha": alpha,
        "n_bootstrap": n_bootstrap,
    }


# ---------------------------------------------------------------------------
# Main analysis loop
# ---------------------------------------------------------------------------

def run_analysis(
    run_dir: Path,
    n_value: int,
    n_bootstrap: int,
    seed: int,
    alpha: float,
    max_dropped_frac: float = 0.02,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    raw_frames: dict[str, pd.DataFrame] = {}
    accuracies: dict[str, float] = {}
    n_rows: dict[str, int] = {}

    for model_safe in MODEL_ORDER:
        try:
            df_m = get_binary_outcomes(run_dir, model_safe, n_value)
        except (FileNotFoundError, ValueError) as e:
            print(f"  WARNING: skipping {model_safe}: {e}")
            continue
        # Sort consistently by (QuestionID, cv_fold, user_id, task_ordinal) for alignment.
        df_m = df_m.sort_values(["QuestionID", "cv_fold", "user_id", "task_ordinal"]).reset_index(drop=True)
        raw_frames[model_safe] = df_m
        accuracies[model_safe] = float(df_m["correct"].mean())
        n_rows[model_safe] = int(len(df_m))
        print(f"  {MODEL_LABELS[model_safe]}: {len(df_m)} rows at n={n_value}, acc={accuracies[model_safe]:.4f}")

    if not raw_frames:
        raise ValueError("No model data loaded.")

    # Align on the semantic key, never on row position. The previous implementation trimmed every
    # arm to the shortest one and zipped by index: a single dropped unparsable row shifts every
    # later element, so arms compare DIFFERENT items from that point on. Measured on phi-4
    # (450 rows) against phi-4 rationale (449), 139 of 449 positions compared different items,
    # which moved McNemar from b/c 49/19 to 54/24 without any warning.
    KEY = ["QuestionID", "cv_fold", "user_id", "answer_text"]
    keyed: dict[str, pd.DataFrame] = {}
    for model_safe, df_m in raw_frames.items():
        dup = int(df_m.duplicated(KEY).sum())
        if dup:
            raise ValueError(
                f"{model_safe}: {dup} duplicate rows on {KEY} at n={n_value}. "
                "The alignment key is not unique; refusing to produce paired tests."
            )
        keyed[model_safe] = df_m.set_index(KEY).sort_index()

    common = None
    for df_m in keyed.values():
        common = df_m.index if common is None else common.intersection(df_m.index)
    if len(common) == 0:
        raise ValueError("No items are shared by all arms; nothing to compare.")

    dropped = {m: len(df_m) - len(common) for m, df_m in keyed.items()}
    if any(dropped.values()):
        print("  NOTE: aligning on the shared item set:")
        for m, d in sorted(dropped.items(), key=lambda kv: -kv[1]):
            print(f"    {m}: {len(keyed[m])} rows, {d} not shared")
        worst = max(dropped.values()) / len(common)
        if worst > max_dropped_frac:
            raise ValueError(
                f"An arm loses {worst:.1%} of its rows in the intersection, above the "
                f"--max-dropped-frac of {max_dropped_frac:.1%}. That is an arm mismatch, not a "
                "parse failure; refusing to compare."
            )

    common = common.sort_values()
    aligned: dict[str, np.ndarray] = {
        m: keyed[m].loc[common, "correct"].values.astype(float) for m in keyed
    }

    # Integrity check: where the task space really is identical, task_ordinal must agree too.
    ords = {m: keyed[m].loc[common, "task_ordinal"].values for m in keyed}
    ref_m, ref = next(iter(ords.items()))
    for m, v in ords.items():
        n_mismatch = int((v != ref).sum())
        if n_mismatch:
            print(f"  NOTE: {m} vs {ref_m}: task_ordinal differs on {n_mismatch} shared items "
                  "(different task space; the semantic key still aligns them correctly).")

    index_ref = range(len(common))

    models_present = [m for m in MODEL_ORDER if m in aligned]
    pairs = list(combinations(models_present, 2))
    print()

    mcnemar_rows = []
    bootstrap_rows = []

    for m_a, m_b in pairs:
        arr_a = aligned[m_a]
        arr_b = aligned[m_b]

        mc = mcnemar_test(arr_a, arr_b)
        boot = bootstrap_accuracy_difference(arr_a, arr_b, n_bootstrap=n_bootstrap, seed=seed, alpha=alpha)

        mcnemar_rows.append({
            "model_a": m_a,
            "model_a_label": MODEL_LABELS[m_a],
            "model_b": m_b,
            "model_b_label": MODEL_LABELS[m_b],
            "n_examples": n_value,
            "acc_a": accuracies[m_a],
            "acc_b": accuracies[m_b],
            "acc_diff_a_minus_b": accuracies[m_a] - accuracies[m_b],
            "n_pairs": mc["n_pairs"],
            "n00_both_wrong": mc["n00"],
            "n01_a_wrong_b_correct": mc["n01"],
            "n10_a_correct_b_wrong": mc["n10"],
            "n11_both_correct": mc["n11"],
            "discordant": mc["discordant"],
            "chi2_statistic": mc["chi2_statistic"],
            "p_value": mc["p_value"],
            "significant": mc["p_value"] < alpha,
            "alpha": alpha,
        })

        bootstrap_rows.append({
            "model_a": m_a,
            "model_a_label": MODEL_LABELS[m_a],
            "model_b": m_b,
            "model_b_label": MODEL_LABELS[m_b],
            "n_examples": n_value,
            "obs_acc_a": boot["obs_acc_a"],
            "obs_acc_b": boot["obs_acc_b"],
            "obs_diff_a_minus_b": boot["obs_diff_a_minus_b"],
            "bootstrap_mean_diff": boot["bootstrap_mean_diff"],
            f"bootstrap_ci_{int((1-alpha)*100)}_low": boot["bootstrap_ci_low"],
            f"bootstrap_ci_{int((1-alpha)*100)}_high": boot["bootstrap_ci_high"],
            "ci_excludes_zero": not (boot["bootstrap_ci_low"] <= 0 <= boot["bootstrap_ci_high"]),
            "alpha": alpha,
            "n_bootstrap": n_bootstrap,
        })

    mcnemar_df = pd.DataFrame(mcnemar_rows)
    bootstrap_df = pd.DataFrame(bootstrap_rows)

    # Apply Holm-Bonferroni correction across the family of pairwise McNemar tests.
    if not mcnemar_df.empty:
        raw_ps = mcnemar_df["p_value"].tolist()
        p_adj, reject_holm = holm_bonferroni(raw_ps, alpha=alpha)
        mcnemar_df["p_value_holm"] = p_adj
        mcnemar_df["significant_holm"] = reject_holm

    meta: dict[str, Any] = {
        "script": "13_significance_testing.py",
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "n_value": n_value,
        "n_bootstrap": n_bootstrap,
        "seed": seed,
        "alpha": alpha,
        "models_included": models_present,
        "model_accuracies_at_n": {m: float(accuracies[m]) for m in models_present},
        "n_evaluation_rows": {m: int(n_rows[m]) for m in models_present},
        "n_aligned_pairs": int(min_rows),
    }

    return mcnemar_df, bootstrap_df, meta


# ---------------------------------------------------------------------------
# Summary markdown
# ---------------------------------------------------------------------------

def build_summary_md(
    mcnemar_df: pd.DataFrame,
    bootstrap_df: pd.DataFrame,
    meta: dict[str, Any],
    alpha: float,
) -> str:
    lines = [
        "# Significance Testing Summary",
        f"",
        f"**n_examples evaluated:** {meta['n_value']}",
        f"**Bootstrap resamples:** {meta['n_bootstrap']:,}",
        f"**Seed:** {meta['seed']}",
        f"**Alpha:** {alpha}",
        f"**Generated (UTC):** {meta['generated_utc']}",
        f"",
        "## Model Accuracies at n={n}".format(n=meta['n_value']),
        f"",
    ]
    for m, acc in meta["model_accuracies_at_n"].items():
        lines.append(f"- {MODEL_LABELS[m]}: {acc:.4f} ({acc * 100:.2f}%)")

    lines += [
        "",
        "## McNemar Pairwise Results (continuity-corrected, with Holm-Bonferroni correction)",
        "",
        f"{'Model A':<28} {'Model B':<28} {'Acc A':>7} {'Acc B':>7} {'Diff':>7} {'b':>5} {'c':>5} {'chi2':>7} {'p_raw':>8} {'p_holm':>8} {'Sig(holm)':>10}",
        "-" * 115,
    ]
    has_holm = "p_value_holm" in mcnemar_df.columns
    for _, row in mcnemar_df.iterrows():
        sig_raw = "YES" if row["significant"] else "no"
        if has_holm:
            sig_holm = "YES" if row["significant_holm"] else "no"
            p_holm_str = f"{row['p_value_holm']:>8.4f}"
        else:
            sig_holm = sig_raw
            p_holm_str = "    n/a "
        lines.append(
            f"{row['model_a_label']:<28} {row['model_b_label']:<28} "
            f"{row['acc_a']:>7.4f} {row['acc_b']:>7.4f} {row['acc_diff_a_minus_b']:>+7.4f} "
            f"{int(row['n01_a_wrong_b_correct']):>5} {int(row['n10_a_correct_b_wrong']):>5} "
            f"{row['chi2_statistic']:>7.3f} {row['p_value']:>8.4f} {p_holm_str} {sig_holm:>10}"
        )

    lines += [
        "",
        "## Bootstrap CIs for Accuracy Difference (A − B)",
        "",
    ]
    ci_col_low = [c for c in bootstrap_df.columns if c.endswith("_low")][0]
    ci_col_high = [c for c in bootstrap_df.columns if c.endswith("_high")][0]
    ci_label = ci_col_low.replace("_low", "").replace("bootstrap_ci_", "")

    lines.append(
        f"{'Model A':<28} {'Model B':<28} {'Obs Diff':>9} {ci_label + ' CI low':>14} {ci_label + ' CI high':>15} {'Excl. 0':>8}"
    )
    lines.append("-" * 100)
    for _, row in bootstrap_df.iterrows():
        excl = "YES" if row["ci_excludes_zero"] else "no"
        lines.append(
            f"{row['model_a_label']:<28} {row['model_b_label']:<28} "
            f"{row['obs_diff_a_minus_b']:>+9.4f} "
            f"{row[ci_col_low]:>14.4f} {row[ci_col_high]:>15.4f} {excl:>8}"
        )

    lines += [
        "",
        "## Interpretation Notes",
        "",
        "- McNemar test uses continuity correction (|b-c|-1)^2 / (b+c).",
        "  b = cases where model A is wrong and model B is correct.",
        "  c = cases where model A is correct and model B is wrong.",
        f"- Bootstrap CI uses {meta['n_bootstrap']:,} resamples of (prediction, prediction) pairs with replacement.",
        "- 'Excl. 0' = True when the bootstrap CI for the accuracy difference does not contain 0.",
        f"  This corresponds to a {int((1-alpha)*100)}% bootstrap CI.",
        "- Holm-Bonferroni correction (step-down) is applied across the family of m pairwise McNemar tests.",
        "  p_holm = max over ranks 1..k of (m - rank + 1) * p_raw, capped at 1.0.",
        "  'Sig(holm)' = YES when p_holm < alpha after step-down correction.",
        "- Note: both tests operate on flattened prediction rows across all questions and folds.",
        "  Per-question tests are not corrected for multiple comparisons here.",
        "- Tests at n=40 characterize performance at the protocol ceiling (maximum training budget).",
        "  Results at other n-values are not reported here but can be obtained via --n-value.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    run_name, run_dir = resolve_run(args.base_output_dir, args.run_name)
    analysis_dir = args.base_output_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    tag = f"n{args.n_value}__parsable_only"
    mcnemar_out = analysis_dir / f"significance_mcnemar__{tag}.csv"
    bootstrap_out = analysis_dir / f"significance_bootstrap__{tag}.csv"
    summary_out = analysis_dir / f"significance_summary__{tag}.md"
    meta_out = analysis_dir / f"significance_mcnemar__{tag}.meta.json"

    print(f"Run: {run_name}")
    print(f"n_value: {args.n_value}  |  n_bootstrap: {args.n_bootstrap}  |  seed: {args.seed}  |  alpha: {args.alpha}")
    print()

    mcnemar_df, bootstrap_df, meta = run_analysis(
        run_dir=run_dir,
        n_value=args.n_value,
        n_bootstrap=args.n_bootstrap,
        seed=args.seed,
        alpha=args.alpha,
        max_dropped_frac=args.max_dropped_frac,
    )

    mcnemar_df.to_csv(mcnemar_out, index=False)
    bootstrap_df.to_csv(bootstrap_out, index=False)
    meta_out.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    summary_md = build_summary_md(mcnemar_df, bootstrap_df, meta, alpha=args.alpha)
    summary_out.write_text(summary_md, encoding="utf-8")

    print(summary_md)
    print()
    print(f"Wrote: {mcnemar_out}")
    print(f"Wrote: {bootstrap_out}")
    print(f"Wrote: {summary_out}")
    print(f"Wrote: {meta_out}")


if __name__ == "__main__":
    main()
