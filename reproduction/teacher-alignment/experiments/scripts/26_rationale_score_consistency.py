#!/usr/bin/env python3
"""Score-rationale consistency (C2) on the four JWE `rationale` runs, at n_examples=40.

    python experiments/scripts/26_rationale_score_consistency.py --check
    python experiments/scripts/26_rationale_score_consistency.py
    python experiments/scripts/26_rationale_score_consistency.py --judge-verdicts <path>

The question is whether the sentence a model wrote into `reason` agrees with the binary
verdict it wrote into `correct` (lifted to `re_eval_score` by 23_parse_structured_fields.py).
The prompt (`experiments/config/prompts/rationale.txt`,
sha256 f6bc2511b635f8002a198e47f089a20c0e1d5866f196701eca6234c31c0c1c2e) requires the keys in
the order `reason`, `correct`, `confidence`, so in a left-to-right decoder the verdict token is
conditioned on the rationale that precedes it. A contradiction therefore means the verdict
departed from the sentence the model had already committed to.

How it is measured, and why exactly this way:

**A frozen three-way lexicon, not a forced binary.** Each `reason` is matched against two
pre-declared cue lists (bilingual, because Qwen3.8 writes 76 of its 450 reasons in German).
Only defect cues fire -> `defect`; only acceptable cues -> `acceptable`; both -> `mixed`;
neither -> `nocue`. Consistency is read only on the covered rows (defect or acceptable). The
hedged sentence "correct, but lacks examples" is exactly the contested case, and the instrument
abstains on it instead of guessing, which turns the ambiguity into a reported quantity rather
than a hidden error source. Coverage is reported with every number.

**The lexicon was frozen before any polarity x score crosstab existed.** It is pinned verbatim
in this file, its two pattern strings are hashed by `test_rationale_score_consistency.py`, and
LEXICON_VERSION records the freeze date. Tuning a cue list on the same 450 rows it scores would
make the whole read circular; freezing it first is the only defence available to a lexical
instrument.

**Two sensitivity variants.** S1 is the forced binary (any defect cue -> 0, else 1) with no
abstention, so the cost of the abstention band is visible. S2 resolves `mixed` rows by their
last clause after a contrastive marker ("but", "aber", ...), which is the most defensible
single-clause reading of a hedged sentence.

**n_examples == 40, all 450 rows, key (QuestionID, user_id, answer_text).** That is the
pre-registered operating point. `task_ordinal` is a running index over the task space and
(QuestionID, user_id) is not unique (students answered the same question more than once: 98
duplicate (QuestionID, user_id) groups hold 225 of the 450 rows), so only the 3-part key aligns
the four models. The four models cover the identical 450 items, so a per-item matrix across
models is free.

**Denominator 450, including phi-4's one unparsable row.** That row's `reason` is empty, it
classifies as `nocue`, it is not covered and therefore not a contradiction. The covered n is the
denominator only for the covered-agreement rate. Fixed here before the first number was seen.

**Exploratory.** The rationale condition was queued after the plan was committed (ANALYSIS_PLAN
D13, rule 2). Estimates with intervals, no confirmatory test, no p-value in running text. The
reference scale is the temperature-0.2 re-run discordance of 12 of 450 from D10; all four
rationale runs are t0.2 (verified from each run's `99_meta/run_meta.json`), so the t0 cells of
2026-09-01 must not be tabled beside these.
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import math
import random
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from scipy import stats

csv.field_size_limit(10**7)

# --------------------------------------------------------------------------------------
# FROZEN LEXICON -- do not edit. Frozen 2026-09-08 before any polarity x score crosstab
# existed. The two pattern strings are hashed by test_rationale_score_consistency.py.
# --------------------------------------------------------------------------------------

LEXICON_VERSION = "2026-09-08-frozen"

DEFECT_PATTERN = r"\b(incorrect(?:ly)?|wrong(?:ly)?|inaccurate(?:ly)?|fails?|failed|does not|do not|did not|doesn'?t|don'?t|didn'?t|cannot|can'?t|not|no|never|missing|misses|omits|lacks?|lacking|incomplete|insufficient|vague|unclear|confuses?|confused|conflates?|misunderstands?|misunderstanding|misidentifies|mischaracteri[sz]es|irrelevant|unrelated|off-topic|partial(?:ly)?|only|instead of|rather than|should have|invalid|nonsensical|mistaken|erroneous|errors?|contradicts?|falsch|fälschlich(?:erweise)?|fehlt|fehlen|fehlende[nrs]?|nicht|kein(?:e|en|em|er|es)?|unvollständig|ungenau|verwechselt|vage|unklar|fehlerhaft|nur|statt|anstatt|teilweise)\b"

ACCEPTABLE_PATTERN = r"\b(correct(?:ly)?|accurate(?:ly)?|acceptable|valid|appropriate(?:ly)?|adequate(?:ly)?|sufficient(?:ly)?|complete(?:ly)?|clear(?:ly)?|concise(?:ly)?|right|properly|well|good|matches|aligns|consistent with|korrekt(?:e|en|er)?|richtig(?:e|en|er)?|zutreffend|akzeptabel|angemessen|vollständig(?:e|en)?|klar|präzise|gültig(?:e|en)?|passend(?:e|en)?)\b"

CONTRASTIVE_PATTERN = r"\b(but|however|although|though|yet|while|whereas|aber|jedoch|allerdings|doch|obwohl|während)\b"

DEFECT_RE = re.compile(DEFECT_PATTERN, re.I)
ACCEPTABLE_RE = re.compile(ACCEPTABLE_PATTERN, re.I)
CONTRASTIVE_RE = re.compile(CONTRASTIVE_PATTERN, re.I)

# Pinned cases (also asserted by the test file). The sixth is a known false-mixed
# ("clearly" fires as an acceptable cue inside a negated clause); it is documented, not patched.
PINNED_CASES = [
    ("The answer is clear and correct, but lacks specific examples.", "mixed"),
    ("The answer is generally correct but lacks specific examples and clarity.", "mixed"),
    (
        "The answer correctly explains the purpose of .gitignore and provides valid examples of files to ignore.",
        "acceptable",
    ),
    (
        "Die Antwort beschreibt die Funktion der .gitignore-Datei falsch (sie sammelt keine Dateien, "
        "sondern definiert Muster zum Ignorieren) und liefert kein konkretes Beispiel für einen Eintrag.",
        "defect",
    ),
    ("Correctly describes the main difference between git fetch and git pull", "acceptable"),
    (
        "The answer is vague and does not clearly explain the purpose of .gitignore or provide a specific example.",
        "mixed",
    ),
    ("", "nocue"),
]
PINNED_S2_CASES = [
    ("The answer is clear and correct, but lacks specific examples.", "defect"),
]

# --------------------------------------------------------------------------------------
# Pinned inputs
# --------------------------------------------------------------------------------------

MODELS = [
    ("Qwen/Qwen3.6-27B", "2026-08-18_jwe-onprem-rationale-qwen-qwen3.6-27b"),
    ("Qwen/Qwen3.8-27B", "2026-08-18_jwe-onprem-rationale-qwen-qwen3.8-27b"),
    ("microsoft/phi-4:16k", "2026-08-18_jwe-onprem-rationale-microsoft-phi-4-16k"),
    (
        "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
        "2026-08-18_jwe-onprem-rationale-mistralai-mistral-small-3.2-24b-instruct-2506",
    ),
]

N_EXAMPLES = 40
EXPECTED_ROWS_N40 = 450
EXPECTED_ROWS_TOTAL = 4950
NOISE_FLOOR_K = 12  # ANALYSIS_PLAN D10: same-endpoint re-run discordance at temperature 0.2
NOISE_FLOOR_N = 450
ANCHOR_CEILING = 0.9044  # source_score == human_answer_correct, 407/450
DEFAULT_SEED = 20260908
BOOTSTRAP_RESAMPLES = 2000
JUDGE_PER_MODEL = 40
JUDGE_PER_CELL = 7

KEY_COLS = ["QuestionID", "user_id", "answer_text"]
USE_COLS = [
    "QuestionID",
    "user_id",
    "answer_text",
    "n_examples",
    "cv_fold",
    "re_eval_score",
    "confidence",
    "parsable",
    "human_answer_correct",
    "source_score",
    "reason",
]

# --------------------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------------------


def classify(reason: str) -> str:
    """Primary three-way polarity of a rationale string."""
    text = "" if reason is None else str(reason)
    if text.strip().lower() in {"", "nan"}:
        return "nocue"
    d = bool(DEFECT_RE.search(text))
    a = bool(ACCEPTABLE_RE.search(text))
    if d and not a:
        return "defect"
    if a and not d:
        return "acceptable"
    if d and a:
        return "mixed"
    return "nocue"


def classify_s1(reason: str) -> int:
    """S1 forced binary: any defect cue -> 0, else 1. Acceptable cues ignored."""
    text = "" if reason is None else str(reason)
    return 0 if DEFECT_RE.search(text) else 1


def classify_s2(reason: str) -> str:
    """S2: mixed rows resolved by the clause after the LAST contrastive marker."""
    primary = classify(reason)
    if primary != "mixed":
        return primary
    text = str(reason)
    matches = list(CONTRASTIVE_RE.finditer(text))
    if not matches:
        return "mixed"
    tail = text[matches[-1].end():]
    d = bool(DEFECT_RE.search(tail))
    a = bool(ACCEPTABLE_RE.search(tail))
    if d and not a:
        return "defect"
    if a and not d:
        return "acceptable"
    return "mixed"


POLARITY_AS_BINARY = {"defect": 0, "acceptable": 1}


def is_contradiction(polarity: str, score) -> bool:
    if polarity not in POLARITY_AS_BINARY:
        return False
    if pd.isna(score):
        return False
    return int(POLARITY_AS_BINARY[polarity]) != int(score)


# --------------------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------------------


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    lo = 0.0 if k == 0 else stats.beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else stats.beta.ppf(1 - alpha / 2, k + 1, n - k)
    return (float(lo), float(hi))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p (binomial on the discordant pairs)."""
    if b + c == 0:
        return 1.0
    return float(stats.binomtest(b, b + c, 0.5, alternative="two-sided").pvalue)


def bootstrap_diff_ci(a: list[int], b: list[int], rng: random.Random, resamples: int) -> tuple[float, float]:
    """Percentile CI for mean(a) - mean(b) under a paired item bootstrap."""
    n = len(a)
    if n == 0:
        return (float("nan"), float("nan"))
    diffs = []
    idx_range = range(n)
    for _ in range(resamples):
        idx = [rng.randrange(n) for _ in idx_range]
        diffs.append(sum(a[i] for i in idx) / n - sum(b[i] for i in idx) / n)
    diffs.sort()
    lo = diffs[int(0.025 * (resamples - 1))]
    hi = diffs[int(0.975 * (resamples - 1))]
    return (float(lo), float(hi))


# --------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------


def find_predictions_csv(repo_root: Path, run_dir_name: str) -> Path:
    pattern = str(
        repo_root
        / "experiments"
        / "outputs"
        / "jwe"
        / run_dir_name
        / "runs"
        / "*"
        / "02_predictions"
        / "*"
        / "in_context_predictions.csv"
    )
    hits = sorted(glob.glob(pattern))
    if len(hits) != 1:
        raise SystemExit(f"expected exactly one predictions CSV under {run_dir_name}, found {len(hits)}")
    return Path(hits[0])


def read_run_temperature(csv_path: Path) -> float:
    meta = csv_path.parents[2] / "99_meta" / "run_meta.json"
    with meta.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return float(data["llm_settings"]["temperature"])


def load_model(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, usecols=USE_COLS, engine="python")
    df["reason"] = df["reason"].fillna("")
    return df


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_sha(repo_root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:  # pragma: no cover - provenance is best-effort
        return "unknown"


# --------------------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------------------


def analyse_model(model: str, run_dir: str, csv_path: Path, seed: int) -> dict:
    full = load_model(csv_path)
    df = full[full["n_examples"] == N_EXAMPLES].copy()
    df = df.sort_values(KEY_COLS, kind="mergesort").reset_index(drop=True)

    df["polarity"] = df["reason"].map(classify)
    df["polarity_s2"] = df["reason"].map(classify_s2)
    df["pred_s1"] = df["reason"].map(classify_s1)
    df["contradiction"] = [
        is_contradiction(p, s) for p, s in zip(df["polarity"], df["re_eval_score"])
    ]
    df["contradiction_s2"] = [
        is_contradiction(p, s) for p, s in zip(df["polarity_s2"], df["re_eval_score"])
    ]

    n = len(df)
    counts = {c: int((df["polarity"] == c).sum()) for c in ("defect", "acceptable", "mixed", "nocue")}
    covered = counts["defect"] + counts["acceptable"]
    k = int(df["contradiction"].sum())
    lo, hi = clopper_pearson(k, n)

    covered_mask = df["polarity"].isin(POLARITY_AS_BINARY)
    cov_k = k
    cov_lo, cov_hi = clopper_pearson(cov_k, covered) if covered else (float("nan"), float("nan"))

    # --- crosstab polarity x re_eval_score
    crosstab = {}
    for pol in ("defect", "acceptable", "mixed", "nocue"):
        sub = df[df["polarity"] == pol]
        crosstab[pol] = {
            "score_0": int((sub["re_eval_score"] == 0).sum()),
            "score_1": int((sub["re_eval_score"] == 1).sum()),
        }

    # --- S1 forced binary
    s1_agree = int((df["pred_s1"] == df["re_eval_score"]).sum())
    s1_disagree_idx = df.index[df["pred_s1"] != df["re_eval_score"]]
    s1_disagree_mixed = int((df.loc[s1_disagree_idx, "polarity"] == "mixed").sum())
    s1_ct = {
        "pred0_score0": int(((df["pred_s1"] == 0) & (df["re_eval_score"] == 0)).sum()),
        "pred0_score1": int(((df["pred_s1"] == 0) & (df["re_eval_score"] == 1)).sum()),
        "pred1_score0": int(((df["pred_s1"] == 1) & (df["re_eval_score"] == 0)).sum()),
        "pred1_score1": int(((df["pred_s1"] == 1) & (df["re_eval_score"] == 1)).sum()),
    }

    # --- S2 last-clause resolution
    counts_s2 = {
        c: int((df["polarity_s2"] == c).sum()) for c in ("defect", "acceptable", "mixed", "nocue")
    }
    covered_s2 = counts_s2["defect"] + counts_s2["acceptable"]
    k_s2 = int(df["contradiction_s2"].sum())
    lo_s2, hi_s2 = clopper_pearson(k_s2, n)
    recovered = int(((df["polarity"] == "mixed") & (df["polarity_s2"] != "mixed")).sum())

    # --- T4 information gain on covered rows
    def gain_block(sub: pd.DataFrame) -> dict:
        sub = sub[sub["human_answer_correct"].notna()]
        if len(sub) == 0:
            return {"n": 0}
        pol_bin = [POLARITY_AS_BINARY[p] for p in sub["polarity"]]
        human = [int(h) for h in sub["human_answer_correct"]]
        score = [int(s) for s in sub["re_eval_score"]]
        src = [int(s) for s in sub["source_score"]]
        pol_hit = [int(p == h) for p, h in zip(pol_bin, human)]
        score_hit = [int(s == h) for s, h in zip(score, human)]
        b = sum(1 for ph, sh in zip(pol_hit, score_hit) if ph == 1 and sh == 0)
        c = sum(1 for ph, sh in zip(pol_hit, score_hit) if ph == 0 and sh == 1)
        rng = random.Random(seed)
        blo, bhi = bootstrap_diff_ci(pol_hit, score_hit, rng, BOOTSTRAP_RESAMPLES)
        maj = max(sum(human), len(human) - sum(human)) / len(human)
        return {
            "n": len(sub),
            "acc_polarity": sum(pol_hit) / len(sub),
            "acc_score": sum(score_hit) / len(sub),
            "diff": (sum(pol_hit) - sum(score_hit)) / len(sub),
            "diff_ci95": [blo, bhi],
            "mcnemar_b": b,
            "mcnemar_c": c,
            "mcnemar_p_exact": mcnemar_exact(b, c),
            "anchor_ceiling": sum(int(s == h) for s, h in zip(src, human)) / len(sub),
            "majority_class": maj,
        }

    covered_df = df[covered_mask]
    flip_all = df[df["source_score"] != df["human_answer_correct"]]
    flip_covered = covered_df[covered_df["source_score"] != covered_df["human_answer_correct"]]

    binary_acc_all = float((df["re_eval_score"] == df["human_answer_correct"]).mean())
    anchor_all = float((df["source_score"] == df["human_answer_correct"]).mean())

    return {
        "model": model,
        "run_dir": run_dir,
        "predictions_csv": str(csv_path),
        "temperature": read_run_temperature(csv_path),
        "rows_total": int(len(full)),
        "rows_n40": n,
        "unparsable_n40": int((full[full["n_examples"] == N_EXAMPLES]["parsable"] == 0).sum()),
        "empty_reason_n40": int((df["reason"].str.strip() == "").sum()),
        "distinct_reasons_n40": int(df["reason"].nunique()),
        "re_eval_score_1": int((df["re_eval_score"] == 1).sum()),
        "re_eval_score_0": int((df["re_eval_score"] == 0).sum()),
        "binary_accuracy_vs_human": binary_acc_all,
        "anchor_ceiling_all": anchor_all,
        "flip_items": int(len(flip_all)),
        "primary": {
            "counts": counts,
            "covered": covered,
            "coverage": covered / n,
            "contradictions": k,
            "contradictions_of_450": f"{k} von {n}",
            "contradictions_pp": 100.0 * k / n,
            "ci95_of_450": [lo, hi],
            "contradictions_rate_covered": (cov_k / covered) if covered else float("nan"),
            "ci95_covered": [cov_lo, cov_hi],
            "crosstab": crosstab,
        },
        "s1_forced_binary": {
            "agreement": s1_agree / n,
            "agree": s1_agree,
            "disagree": n - s1_agree,
            "disagree_in_mixed_band": s1_disagree_mixed,
            "disagree_in_mixed_band_share": (s1_disagree_mixed / (n - s1_agree)) if n - s1_agree else float("nan"),
            "crosstab": s1_ct,
        },
        "s2_last_clause": {
            "counts": counts_s2,
            "covered": covered_s2,
            "coverage": covered_s2 / n,
            "mixed_recovered": recovered,
            "contradictions": k_s2,
            "contradictions_pp": 100.0 * k_s2 / n,
            "ci95_of_450": [lo_s2, hi_s2],
            "delta_vs_primary": k_s2 - k,
        },
        "information_gain_covered": gain_block(covered_df),
        "information_gain_flip_subgroup": gain_block(flip_covered),
        "_df": df,
        "_full": full,
    }


def per_n_stability(model: str, full: pd.DataFrame) -> list[dict]:
    rows = []
    for n_ex in sorted(full["n_examples"].unique()):
        sub = full[full["n_examples"] == n_ex].copy()
        pol = sub["reason"].map(classify)
        contra = [is_contradiction(p, s) for p, s in zip(pol, sub["re_eval_score"])]
        n = len(sub)
        k = int(sum(contra))
        rows.append(
            {
                "model": model,
                "n_examples": int(n_ex),
                "rows": n,
                "covered": int(pol.isin(POLARITY_AS_BINARY).sum()),
                "mixed": int((pol == "mixed").sum()),
                "nocue": int((pol == "nocue").sum()),
                "contradictions": k,
                "contradictions_pp": round(100.0 * k / n, 4),
            }
        )
    return rows


def build_judge_sample(results: list[dict], seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = random.Random(seed)
    blind_rows, key_rows = [], []
    for res in results:
        df = res["_df"]
        picked_idx: list[int] = []
        for score in (0, 1):
            for pol in ("defect", "acceptable", "mixed"):
                cell = df.index[(df["re_eval_score"] == score) & (df["polarity"] == pol)].tolist()
                cell.sort()
                take = min(JUDGE_PER_CELL, len(cell))
                picked_idx.extend(rng.sample(cell, take))
        if len(picked_idx) > JUDGE_PER_MODEL:
            picked_idx = rng.sample(sorted(picked_idx), JUDGE_PER_MODEL)
        elif len(picked_idx) < JUDGE_PER_MODEL:
            leftover = df.index[
                (~df.index.isin(picked_idx)) & (df["polarity"] != "nocue")
            ].tolist()
            leftover.sort()
            need = min(JUDGE_PER_MODEL - len(picked_idx), len(leftover))
            picked_idx.extend(rng.sample(leftover, need))
        for i in sorted(picked_idx):
            row = df.loc[i]
            jid = str(uuid.UUID(int=rng.getrandbits(128), version=4))
            blind_rows.append({"judge_id": jid, "QuestionID": row["QuestionID"], "reason": row["reason"]})
            key_rows.append(
                {
                    "judge_id": jid,
                    "model": res["model"],
                    "QuestionID": row["QuestionID"],
                    "user_id": row["user_id"],
                    "answer_text": row["answer_text"],
                    "polarity": row["polarity"],
                    "polarity_s2": row["polarity_s2"],
                    "re_eval_score": row["re_eval_score"],
                }
            )
    blind = pd.DataFrame(blind_rows)
    key = pd.DataFrame(key_rows)
    order = list(range(len(blind)))
    rng.shuffle(order)
    blind = blind.iloc[order].reset_index(drop=True)
    return blind, key


def cohens_kappa(a: list[str], b: list[str], labels: list[str]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(lbl) / n) * (b.count(lbl) / n) for lbl in labels)
    if pe == 1.0:
        return float("nan")
    return (po - pe) / (1 - pe)


def judge_validation(verdicts_path: Path, key: pd.DataFrame) -> dict:
    if verdicts_path.suffix.lower() == ".jsonl":
        recs = [json.loads(line) for line in verdicts_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        ver = pd.DataFrame(recs)
    else:
        ver = pd.read_csv(verdicts_path)
    merged = key.merge(ver[["judge_id", "verdict"]], on="judge_id", how="inner")
    labels = ["defect", "acceptable", "ambiguous"]
    lex = ["ambiguous" if p in ("mixed", "nocue") else p for p in merged["polarity"]]
    jud = list(merged["verdict"])
    agree = sum(1 for x, y in zip(lex, jud) if x == y)
    confusion = {}
    for lbl in labels:
        confusion[lbl] = {j: int(sum(1 for x, y in zip(lex, jud) if x == lbl and y == j)) for j in labels}
    lex_contra = int(
        sum(
            1
            for p, s in zip(merged["polarity"], merged["re_eval_score"])
            if is_contradiction(p, s)
        )
    )
    jud_contra = int(
        sum(
            1
            for v, s in zip(merged["verdict"], merged["re_eval_score"])
            if v in POLARITY_AS_BINARY and int(POLARITY_AS_BINARY[v]) != int(s)
        )
    )
    per_model = {}
    for m in sorted(merged["model"].unique()):
        sub = merged[merged["model"] == m]
        sub_lex = ["ambiguous" if p in ("mixed", "nocue") else p for p in sub["polarity"]]
        sub_jud = list(sub["verdict"])
        per_model[m] = {
            "n": int(len(sub)),
            "agreement": sum(1 for x, y in zip(sub_lex, sub_jud) if x == y) / len(sub),
        }
    jud_contra_by_lex = {}
    for lbl in labels:
        jud_contra_by_lex[lbl] = int(
            sum(
                1
                for l, v, s in zip(lex, merged["verdict"], merged["re_eval_score"])
                if l == lbl and v in POLARITY_AS_BINARY and int(POLARITY_AS_BINARY[v]) != int(s)
            )
        )
    jud_contra_by_model = {
        m: int(
            sum(
                1
                for v, s in zip(
                    merged[merged["model"] == m]["verdict"],
                    merged[merged["model"] == m]["re_eval_score"],
                )
                if v in POLARITY_AS_BINARY and int(POLARITY_AS_BINARY[v]) != int(s)
            )
        )
        for m in sorted(merged["model"].unique())
    }
    ambiguous_band = [v for l, v in zip(lex, jud) if l == "ambiguous"]
    return {
        "n_judged": int(len(merged)),
        "agreement_3class": agree / len(merged) if len(merged) else float("nan"),
        "cohens_kappa": cohens_kappa(lex, jud, labels),
        "confusion_lexicon_rows_judge_cols": confusion,
        "lexical_contradictions_on_sample": lex_contra,
        "judge_contradictions_on_sample": jud_contra,
        "judge_contradictions_by_lexicon_class": jud_contra_by_lex,
        "judge_contradictions_by_model": jud_contra_by_model,
        "sample_composition_lexicon_3class": {lbl: int(lex.count(lbl)) for lbl in labels},
        "judge_verdict_on_lexicon_ambiguous_band": {
            lbl: int(ambiguous_band.count(lbl)) for lbl in labels
        },
        "sampling_note": (
            "Stratifiziert nach (Modell x Primärklasse x re_eval_score), das mixed-Band ist "
            "gegenüber seinem Anteil in den 450 Zeilen überrepräsentiert. Die Stichprobengewichte "
            "sind hier NICHT zurückgerechnet; aus diesen Zählungen wird keine Populationsschätzung "
            "abgeleitet."
        ),
        "per_model_agreement": per_model,
        "framing": (
            "Einzelrater, agentisch, verblindet gegenüber Modell und Score, nicht verblindet "
            "gegenüber dem Studienziel, n=160; validiert das Instrument, ist keine Ergebniszahl."
        ),
    }


# --------------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------------


def fmt(x, nd=4):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:.{nd}f}"


def render_markdown(payload: dict) -> str:
    L = []
    A = L.append
    A("# Score-Rationale-Konsistenz (C2), n_examples = 40")
    A("")
    A(f"Erzeugt: {payload['generated_at']} | Skript-SHA256: `{payload['script_sha256'][:16]}...` | "
      f"Git HEAD: `{payload['git_head'][:12]}` | Lexikon: `{payload['lexicon_version']}`")
    A("")
    A("> Explorativ: die rationale-Kondition wurde nach dem Präregistrierungs-Commit vom 18.08. "
      "eingereiht (D13, Regel 2); Schätzwerte mit Intervallen, kein konfirmatorischer Test.")
    A("")
    A(f"Referenzskala: {NOISE_FLOOR_K} von {NOISE_FLOOR_N} "
      f"({100.0*NOISE_FLOOR_K/NOISE_FLOOR_N:.2f} pp) Wiederholungsdiskordanz bei Temperatur 0.2 (D10).")
    A("")
    A("## T1 Klassenverteilung und Abdeckung")
    A("")
    A("| Modell | Temp. | n | defect | acceptable | mixed | nocue | abgedeckt | Abdeckung |")
    A("|---|---|---|---|---|---|---|---|---|")
    for r in payload["models"]:
        p = r["primary"]
        c = p["counts"]
        A(f"| {r['model']} | {r['temperature']} | {r['rows_n40']} | {c['defect']} | {c['acceptable']} | "
          f"{c['mixed']} | {c['nocue']} | {p['covered']} | {fmt(p['coverage'],3)} |")
    A("")
    A("## T2 Widersprüche (Primärregel)")
    A("")
    A("| Modell | Temp. | Widersprüche / 450 | pp | 95 % CI (pp) | Rate auf abgedeckten | Referenzskala |")
    A("|---|---|---|---|---|---|---|")
    for r in payload["models"]:
        p = r["primary"]
        A(f"| {r['model']} | {r['temperature']} | {p['contradictions']} / {r['rows_n40']} | "
          f"{p['contradictions_pp']:.2f} | [{100*p['ci95_of_450'][0]:.2f}, {100*p['ci95_of_450'][1]:.2f}] | "
          f"{fmt(p['contradictions_rate_covered'],4)} ({p['contradictions']}/{p['covered']}) | "
          f"{NOISE_FLOOR_K} von 450 |")
    A("")
    A("| Modell | defect/Score 0 | defect/Score 1 | acceptable/Score 0 | acceptable/Score 1 |")
    A("|---|---|---|---|---|")
    for r in payload["models"]:
        ct = r["primary"]["crosstab"]
        A(f"| {r['model']} | {ct['defect']['score_0']} | {ct['defect']['score_1']} | "
          f"{ct['acceptable']['score_0']} | {ct['acceptable']['score_1']} |")
    A("")
    A("## T3 Sensitivität")
    A("")
    A("### S1 erzwungene Binärregel (keine Enthaltung)")
    A("")
    A("| Modell | Übereinstimmung | uneinig | davon im mixed-Band | Anteil |")
    A("|---|---|---|---|---|")
    for r in payload["models"]:
        s = r["s1_forced_binary"]
        A(f"| {r['model']} | {fmt(s['agreement'])} | {s['disagree']} | {s['disagree_in_mixed_band']} | "
          f"{fmt(s['disagree_in_mixed_band_share'],3)} |")
    A("")
    A("### S2 Auflösung des letzten Teilsatzes")
    A("")
    A("| Modell | mixed aufgelöst | abgedeckt | Abdeckung | Widersprüche / 450 | pp | Delta zur Primärregel |")
    A("|---|---|---|---|---|---|---|")
    for r in payload["models"]:
        s = r["s2_last_clause"]
        A(f"| {r['model']} | {s['mixed_recovered']} | {s['covered']} | {fmt(s['coverage'],3)} | "
          f"{s['contradictions']} / {r['rows_n40']} | {s['contradictions_pp']:.2f} | {s['delta_vs_primary']:+d} |")
    A("")
    A("## T4 Trägt die Begründung Signal, den der Score wegwirft?")
    A("")
    A("Alle Werte auf den abgedeckten Zeilen der Primärregel.")
    A("")
    A("| Modell | n | acc(Begründung) | acc(Score) | Differenz | 95 % CI | b | c | Ankerdecke | Mehrheitsklasse |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for r in payload["models"]:
        g = r["information_gain_covered"]
        A(f"| {r['model']} | {g['n']} | {fmt(g['acc_polarity'])} | {fmt(g['acc_score'])} | "
          f"{g['diff']:+.4f} | [{g['diff_ci95'][0]:+.4f}, {g['diff_ci95'][1]:+.4f}] | {g['mcnemar_b']} | "
          f"{g['mcnemar_c']} | {fmt(g['anchor_ceiling'])} | {fmt(g['majority_class'])} |")
    A("")
    A("Kipp-Items (source_score != human_answer_correct), geschnitten mit den abgedeckten Zeilen:")
    A("")
    A("| Modell | n | acc(Begründung) | acc(Score) | Differenz | 95 % CI | b | c |")
    A("|---|---|---|---|---|---|---|---|")
    for r in payload["models"]:
        g = r["information_gain_flip_subgroup"]
        if g["n"] == 0:
            A(f"| {r['model']} | 0 | n/a | n/a | n/a | n/a | n/a | n/a |")
            continue
        A(f"| {r['model']} | {g['n']} | {fmt(g['acc_polarity'])} | {fmt(g['acc_score'])} | "
          f"{g['diff']:+.4f} | [{g['diff_ci95'][0]:+.4f}, {g['diff_ci95'][1]:+.4f}] | {g['mcnemar_b']} | "
          f"{g['mcnemar_c']} |")
    A("")
    A("## T5 Instrumentvalidierung (verblindete Stichprobe)")
    A("")
    jv = payload.get("judge_validation")
    if not jv:
        A("Noch keine Urteile eingelesen. Blinddatei erzeugt, Urteile fehlen.")
    else:
        A(jv["framing"])
        A("")
        A(f"n = {jv['n_judged']}, 3-Klassen-Übereinstimmung = {fmt(jv['agreement_3class'])}, "
          f"Cohens Kappa = {fmt(jv['cohens_kappa'])}.")
        A("")
        A("| Lexikon \\ Urteil | defect | acceptable | ambiguous |")
        A("|---|---|---|---|")
        for lbl in ("defect", "acceptable", "ambiguous"):
            row = jv["confusion_lexicon_rows_judge_cols"][lbl]
            A(f"| {lbl} | {row['defect']} | {row['acceptable']} | {row['ambiguous']} |")
        A("")
        A(f"Widersprüche auf denselben {jv['n_judged']} Zeilen: lexikalisch {jv['lexical_contradictions_on_sample']}, "
          f"agentisch {jv['judge_contradictions_on_sample']}.")
        A("")
        cb = jv["judge_contradictions_by_lexicon_class"]
        A(f"Die {jv['judge_contradictions_on_sample']} agentischen Widersprüche liegen zu "
          f"{cb['defect']} in der Lexikon-Klasse defect, zu {cb['acceptable']} in acceptable und zu "
          f"{cb['ambiguous']} im Enthaltungsband.")
        A("")
        sc = jv["sample_composition_lexicon_3class"]
        ab = jv["judge_verdict_on_lexicon_ambiguous_band"]
        A(f"Stichprobenzusammensetzung nach Lexikon: defect {sc['defect']}, acceptable "
          f"{sc['acceptable']}, ambiguous {sc['ambiguous']}. Im Enthaltungsband liest der Agent "
          f"{ab['defect']} als defect, {ab['acceptable']} als acceptable und {ab['ambiguous']} "
          "ebenfalls als mehrdeutig.")
        A("")
        A(jv["sampling_note"])
        A("")
        A("| Modell | n | Übereinstimmung | agentische Widersprüche |")
        A("|---|---|---|---|")
        for m, v in jv["per_model_agreement"].items():
            A(f"| {m} | {v['n']} | {fmt(v['agreement'])} | {jv['judge_contradictions_by_model'][m]} |")
        A("")
    A("")
    A("## Kontext je Modell")
    A("")
    A("| Modell | Zeilen gesamt | Zeilen n=40 | unparsbar n=40 | leere reason | verschiedene reason | "
      "Score 1/0 | Genauigkeit vs. Mensch | Ankerdecke | Kipp-Items |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for r in payload["models"]:
        A(f"| {r['model']} | {r['rows_total']} | {r['rows_n40']} | {r['unparsable_n40']} | "
          f"{r['empty_reason_n40']} | {r['distinct_reasons_n40']} | {r['re_eval_score_1']}/{r['re_eval_score_0']} | "
          f"{fmt(r['binary_accuracy_vs_human'])} | {fmt(r['anchor_ceiling_all'])} | {r['flip_items']} |")
    A("")
    A("## Item-Matrix")
    A("")
    im = payload["item_matrix_summary"]
    A("| in wie vielen Modellen widersprüchlich | Items |")
    A("|---|---|")
    for k in sorted(im["items_by_contradiction_count"], key=int):
        A(f"| {k} | {im['items_by_contradiction_count'][k]} |")
    A("")
    A("| Frage | Widersprüche über alle vier Modelle |")
    A("|---|---|")
    for q in sorted(im["contradictions_per_question"]):
        A(f"| {q} | {im['contradictions_per_question'][q]} |")
    A("")
    A("## Gefrorenes Lexikon")
    A("")
    A(f"`LEXICON_VERSION = {payload['lexicon_version']}`, eingefroren am 2026-09-08, bevor irgendeine "
      "Kreuztabelle Polarität x Score existierte.")
    A("")
    A("```")
    A(f"DEFECT     = {DEFECT_PATTERN}")
    A("")
    A(f"ACCEPTABLE = {ACCEPTABLE_PATTERN}")
    A("")
    A(f"CONTRASTIVE = {CONTRASTIVE_PATTERN}")
    A("```")
    A("")
    A(f"sha256(DEFECT) = `{payload['defect_pattern_sha256']}`")
    A("")
    A(f"sha256(ACCEPTABLE) = `{payload['acceptable_pattern_sha256']}`")
    A("")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------


def run_self_test() -> list[str]:
    problems = []
    for text, expected in PINNED_CASES:
        got = classify(text)
        if got != expected:
            problems.append(f"classify({text[:45]!r}) = {got}, expected {expected}")
    for text, expected in PINNED_S2_CASES:
        got = classify_s2(text)
        if got != expected:
            problems.append(f"classify_s2({text[:45]!r}) = {got}, expected {expected}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--judge-verdicts", default=None, help="CSV or JSONL with judge_id,verdict")
    ap.add_argument("--check", action="store_true", help="validate inputs and pinned cases, write nothing")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    out_dir = Path(args.out_dir) if args.out_dir else repo_root / "experiments" / "outputs" / "jwe" / "analysis" / "rationale_consistency"

    problems = run_self_test()
    if problems:
        for p in problems:
            print("PINNED CASE FAILED:", p)
        return 2
    print(f"pinned cases: {len(PINNED_CASES) + len(PINNED_S2_CASES)}/{len(PINNED_CASES) + len(PINNED_S2_CASES)} ok")
    print(f"lexicon {LEXICON_VERSION}")
    print(f"  sha256(DEFECT)     = {sha256_text(DEFECT_PATTERN)}")
    print(f"  sha256(ACCEPTABLE) = {sha256_text(ACCEPTABLE_PATTERN)}")

    csv_paths = []
    for model, run_dir in MODELS:
        path = find_predictions_csv(repo_root, run_dir)
        csv_paths.append((model, run_dir, path))
        print(f"  input {model}: {path.relative_to(repo_root)}")

    if args.check:
        for model, run_dir, path in csv_paths:
            df = load_model(path)
            n40 = int((df["n_examples"] == N_EXAMPLES).sum())
            temp = read_run_temperature(path)
            flag = "" if (len(df) == EXPECTED_ROWS_TOTAL and n40 == EXPECTED_ROWS_N40 and temp == 0.2) else "  <-- UNEXPECTED"
            print(f"  {model}: rows={len(df)} n40={n40} temperature={temp}{flag}")
        print("--check: nothing written")
        return 0

    results = [analyse_model(m, r, p, args.seed) for m, r, p in csv_paths]

    # per-item matrix across models
    base = results[0]["_df"][KEY_COLS].copy()
    matrix = base.copy()
    for res in results:
        tag = res["model"].split("/")[-1]
        sub = res["_df"][KEY_COLS + ["polarity", "re_eval_score", "contradiction"]].rename(
            columns={
                "polarity": f"polarity__{tag}",
                "re_eval_score": f"score__{tag}",
                "contradiction": f"contradiction__{tag}",
            }
        )
        matrix = matrix.merge(sub, on=KEY_COLS, how="left")
    contra_cols = [c for c in matrix.columns if c.startswith("contradiction__")]
    matrix["n_models_contradicting"] = matrix[contra_cols].sum(axis=1).astype(int)
    items_by_count = matrix["n_models_contradicting"].value_counts().sort_index()
    per_question = (
        matrix.groupby("QuestionID")["n_models_contradicting"].sum().astype(int).to_dict()
    )

    stability_rows = []
    for res in results:
        stability_rows.extend(per_n_stability(res["model"], res["_full"]))

    blind, key = build_judge_sample(results, args.seed)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "experiments/scripts/26_rationale_score_consistency.py",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "git_head": git_sha(repo_root),
        "lexicon_version": LEXICON_VERSION,
        "defect_pattern": DEFECT_PATTERN,
        "acceptable_pattern": ACCEPTABLE_PATTERN,
        "contrastive_pattern": CONTRASTIVE_PATTERN,
        "defect_pattern_sha256": sha256_text(DEFECT_PATTERN),
        "acceptable_pattern_sha256": sha256_text(ACCEPTABLE_PATTERN),
        "n_examples": N_EXAMPLES,
        "seed": args.seed,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "noise_floor_reference": {"k": NOISE_FLOOR_K, "n": NOISE_FLOOR_N, "source": "ANALYSIS_PLAN D10, temperature 0.2"},
        "anchor_ceiling_plan": ANCHOR_CEILING,
        "status": "exploratory (ANALYSIS_PLAN rule 2, D13, D20)",
        "models": [{k: v for k, v in r.items() if not k.startswith("_")} for r in results],
        "item_matrix_summary": {
            "items": int(len(matrix)),
            "items_by_contradiction_count": {str(k): int(v) for k, v in items_by_count.items()},
            "contradictions_per_question": per_question,
        },
    }

    if args.judge_verdicts:
        payload["judge_validation"] = judge_validation(Path(args.judge_verdicts), key)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "rationale_consistency_n40.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "rationale_consistency_n40.md").write_text(render_markdown(payload), encoding="utf-8")
    matrix.to_csv(out_dir / "per_item_matrix_n40.csv", index=False, encoding="utf-8")
    pd.DataFrame(stability_rows).to_csv(out_dir / "per_n_stability.csv", index=False, encoding="utf-8")
    blind.to_csv(out_dir / "judge_sample_160_blind.csv", index=False, encoding="utf-8")
    key.to_csv(out_dir / "judge_sample_160_key.csv", index=False, encoding="utf-8")
    (out_dir / "cue_lexicon.json").write_text(
        json.dumps(
            {
                "lexicon_version": LEXICON_VERSION,
                "frozen_on": "2026-09-08",
                "frozen_before": "any polarity x re_eval_score crosstab existed",
                "defect": DEFECT_PATTERN,
                "acceptable": ACCEPTABLE_PATTERN,
                "contrastive": CONTRASTIVE_PATTERN,
                "defect_sha256": sha256_text(DEFECT_PATTERN),
                "acceptable_sha256": sha256_text(ACCEPTABLE_PATTERN),
                "rule": "d and not a -> defect; a and not d -> acceptable; d and a -> mixed; else nocue",
                "flags": "re.IGNORECASE",
                "pinned_cases": [{"reason": t, "expected": e} for t, e in PINNED_CASES],
                "pinned_s2_cases": [{"reason": t, "expected": e} for t, e in PINNED_S2_CASES],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    for r in results:
        p = r["primary"]
        print(
            f"{r['model']:48s} contradictions {p['contradictions']:3d}/{r['rows_n40']} "
            f"({p['contradictions_pp']:.2f} pp)  coverage {p['coverage']:.3f}  "
            f"S1 agree {r['s1_forced_binary']['agreement']:.4f}  S2 {r['s2_last_clause']['contradictions']}/{r['rows_n40']}"
        )
    print()
    print(f"wrote outputs to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
