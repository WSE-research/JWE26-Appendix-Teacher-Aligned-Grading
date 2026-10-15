from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np
import pandas as pd

RESPONSE_KEYS = ["QuestionID", "question_text", "user_id", "answer_text"]


@dataclass(frozen=True)
class ManualEvalBundle:
    sources: pd.DataFrame
    long_df: pd.DataFrame
    response_df: pd.DataFrame
    raters: list[str]


def coerce_binary(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.where(numeric.isin([0, 1]))


def coerce_ordinal(series: pd.Series) -> pd.Series:
    """Ordinal sibling of :func:`coerce_binary` for the 0/1/2 partial-credit scale.

    ``coerce_binary`` maps anything outside {0, 1} to NaN, so every ``level == 2`` — the
    top partial-credit grade — is silently dropped to NaN, turning "fully correct" into
    missing data wherever a partial-credit level is fed through the binary coercion. This
    keeps {0, 1, 2} and nulls the rest, so the middle-and-top ordinal levels survive into
    downstream analysis (e.g. QWK against the human 0/1/2 labels).
    """
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.where(numeric.isin([0, 1, 2]))


def parse_rater_name(path: Path) -> str:
    stem = path.stem
    round_match = re.search(r"round[_-]?(\d+)", stem, flags=re.IGNORECASE)
    if round_match:
        return f"human_{round_match.group(1)}"

    ree_match = re.search(r"re_eval[_-]?(\d+)", stem, flags=re.IGNORECASE)
    if ree_match:
        return f"human_{ree_match.group(1)}"

    return stem


def _load_single_csv(csv_path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    df = pd.read_csv(csv_path)
    validation_cols = [c for c in df.columns if c.startswith("validation")]
    if not validation_cols:
        raise ValueError(f"No validation column found in {csv_path}")
    val_col = validation_cols[0]

    ratings = coerce_binary(df[val_col])
    if "score" in df.columns:
        score_binary = coerce_binary(df["score"])
    else:
        score_binary = pd.Series(np.nan, index=df.index, dtype="float64")

    # validation_* captures whether the lecturer agrees with the LLM score.
    # Convert this to the actual lecturer label about answer correctness.
    # If lecturer agrees (1): human_correct = score
    # If lecturer disagrees (0): human_correct = 1 - score
    answer_correct = score_binary.where(ratings == 1, 1 - score_binary)
    answer_correct = answer_correct.where(ratings.notna())
    rater = parse_rater_name(csv_path)

    working = df.assign(
        rater=rater,
        validation_raw=df[val_col],
        review_agrees_llm=ratings,
        llm_score_binary=score_binary,
        answer_correct_numeric=answer_correct,
        source_file=csv_path.name,
    )

    llm_feedback = working.get("llm_feedback", pd.Series("", index=working.index)).fillna("").astype(str)
    question_id = working.get("QuestionID", pd.Series("", index=working.index)).astype(str)
    filtered_mask = question_id.str.startswith("r1") & llm_feedback.str.strip().ne("")

    meta = {
        "rater": rater,
        "source_file": csv_path.name,
        "rows_total": int(len(df)),
        "rows_filtered": int(filtered_mask.sum()),
        "ratings_available_total": int(ratings.notna().sum()),
        "ratings_available_filtered": int((ratings.notna() & filtered_mask).sum()),
        "answer_labels_available_total": int(answer_correct.notna().sum()),
        "answer_labels_available_filtered": int((answer_correct.notna() & filtered_mask).sum()),
        "validation_column": val_col,
    }
    return working, meta


def load_manual_bundle(input_dir: Path) -> ManualEvalBundle:
    csv_paths = sorted(input_dir.glob("*.csv"))
    if not csv_paths:
        raise FileNotFoundError(f"No CSV files found in {input_dir}")

    frames: list[pd.DataFrame] = []
    source_rows: list[dict[str, object]] = []
    for csv_path in csv_paths:
        frame, meta = _load_single_csv(csv_path)
        frames.append(frame)
        source_rows.append(meta)

    long_df = pd.concat(frames, ignore_index=True, sort=False)
    long_df["QuestionID"] = long_df["QuestionID"].astype(str)
    long_df["question_text"] = long_df["question_text"].fillna("").astype(str)
    long_df["answer_text"] = long_df["answer_text"].fillna("").astype(str)
    long_df["llm_feedback"] = long_df["llm_feedback"].fillna("").astype(str)
    long_df["user_id"] = pd.to_numeric(long_df["user_id"], errors="coerce").astype("Int64")
    long_df["review_agrees_llm"] = pd.to_numeric(long_df["review_agrees_llm"], errors="coerce")
    long_df["llm_score_binary"] = pd.to_numeric(long_df["llm_score_binary"], errors="coerce")
    long_df["answer_correct_numeric"] = pd.to_numeric(long_df["answer_correct_numeric"], errors="coerce")

    filtered = long_df[
        long_df["QuestionID"].str.startswith("r1")
        & long_df["llm_feedback"].str.strip().ne("")
    ].copy()

    base_responses = filtered[RESPONSE_KEYS].drop_duplicates().reset_index(drop=True)

    # Keep unrated rows as explicit candidates so single-rater analyses can compute deficits.
    per_rater = (
        filtered.groupby(RESPONSE_KEYS + ["rater"], as_index=False)["answer_correct_numeric"]
        .first()
    )
    rated_wide = per_rater.pivot(index=RESPONSE_KEYS, columns="rater", values="answer_correct_numeric").reset_index()
    rated_wide.columns.name = None

    response_df = base_responses.merge(rated_wide, on=RESPONSE_KEYS, how="left")

    raters = sorted([c for c in response_df.columns if c not in RESPONSE_KEYS])
    response_df["n_raters"] = response_df[raters].notna().sum(axis=1)
    response_df["any_rated"] = response_df["n_raters"] >= 1
    response_df["all_rated"] = response_df["n_raters"] == len(raters)
    response_df["multi_rater"] = response_df["n_raters"] >= 2

    sources = pd.DataFrame(source_rows).sort_values("rater").reset_index(drop=True)
    return ManualEvalBundle(sources=sources, long_df=long_df, response_df=response_df, raters=raters)


def compute_question_coverage(response_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        response_df.groupby(["QuestionID", "question_text"], as_index=False)
        .agg(
            responses_total=("answer_text", "count"),
            responses_any_rating=("any_rated", "sum"),
            responses_all_raters=("all_rated", "sum"),
            responses_with_multi_rater=("multi_rater", "sum"),
        )
        .sort_values("QuestionID")
        .reset_index(drop=True)
    )
    summary["any_rated_share"] = summary["responses_any_rating"] / summary["responses_total"]
    summary["all_rated_share"] = summary["responses_all_raters"] / summary["responses_total"]
    summary["multi_rater_share"] = summary["responses_with_multi_rater"] / summary["responses_total"]
    return summary


def compute_rater_coverage(response_df: pd.DataFrame, raters: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total = len(response_df)
    for rater in raters:
        rated = int(response_df[rater].notna().sum())
        positives = int((response_df[rater] == 1).sum())
        negatives = int((response_df[rater] == 0).sum())
        rows.append(
            {
                "rater": rater,
                "responses_total": total,
                "responses_rated": rated,
                "coverage_share": rated / total if total else np.nan,
                "positives": positives,
                "negatives": negatives,
                "positive_share": positives / rated if rated else np.nan,
            }
        )
    return pd.DataFrame(rows)
