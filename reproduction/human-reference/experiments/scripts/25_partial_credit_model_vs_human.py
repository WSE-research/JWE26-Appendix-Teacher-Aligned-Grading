#!/usr/bin/env python3
"""Manifest-bound exploratory partial-credit model comparison at n_examples=40.

Requires two complete raw rater logs, their exact archived pre-adjudication report,
all disputed items resolved, and 439 final human items. Each requested cell pins its
prediction file, run metadata, source pool, model, prompt and decoding. No timestamp
discovery is allowed. The 450 prediction rows must reproduce the pinned source pool's
multiset of (QuestionID, user_id, answer-text hash) identities before human labels
broadcast by (QuestionID, answer-text hash). Repeated student answers are retained.

Pooled ordinal metrics use 450 prediction rows after broadcast, while unique human
coverage is 439; per-question denominators report both. This weighting is descriptive
and requires an author decision before a paper claim. Binary accuracy context carries
the majority-class and incumbent-agreement reference lines. Existing JSON entries are
retained only when manifest and raw-label snapshots match exactly.

E5 operational rule of 12.10.2026, opt-in with --allow-adjacent-residual: disagreements of two or
more steps must be adjudicated, adjacent ones (exactly one step) may stay unresolved. The model
comparison then uses an explicit three-level reference instead of a single consensus label:
agreed and adjudicated items carry their level; an adjacent residual inside the 1-3 band maps to
"partial" for both raters and is determined; an adjacent residual on a category boundary (3/4 or
0/1) is undetermined and resolved by a declared policy. Primary policy "soft": the item enters
with weight 1/2 for each rater's class (the categorical form of averaging the two ratings, no
rounding rule). Sensitivity policies: "strict" (lower class), "lenient" (higher class),
"exclude_boundary" (item dropped). Every policy reports weighted QWK3, exact and within-1, pooled
with a percentile bootstrap over unique answer texts (rows of one text move together) and per
question. Without the flag nothing changes.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import manual_eval_utils as meu  # noqa: E402
import jwe_run_manifest as manifest  # noqa: E402

_spec = importlib.util.spec_from_file_location("label_partial_credit", HERE / "21_label_partial_credit.py")
assert _spec and _spec.loader
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)

REPO_ROOT = cli.REPO_ROOT
ADJUDICATED = cli.LABEL_DIR / "partial_credit_adjudicated.csv"
DEFAULT_PRED_ROOT = REPO_ROOT / "experiments" / "outputs" / "jwe"
DEFAULT_OUT_DIR = REPO_ROOT / "experiments" / "data" / "manual_eval" / "analysis"

# ANALYSIS_PLAN.md section 3: mandatory on every accuracy table. Binary-accuracy references.
REFERENCE_LINES = {
    "incumbent_agreement_binary_accuracy": 0.9044,   # 407/450, trivial oracle repeating the deployed grader
    "majority_class_binary_accuracy": 0.5600,      # 252/450, always predict "correct"
}
PREREGISTERED_N = 40
REFERENCE_POLICIES = ("soft", "strict", "lenient", "exclude_boundary")
PRIMARY_POLICY = "soft"
BOOTSTRAP = {"resamples": 10000, "seed": 42, "unit": "unique (QuestionID, answer_text_sha256)", "interval": "percentile 95%"}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:   # outside the repo, e.g. a custom --out-dir or a test fixture
        return str(path)


def sha256_text(text: str) -> str:
    """The pool's hash convention: exact string, UTF-8, no normalisation."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_rater_maps(only: list[str] | None) -> dict[str, dict[tuple[str, str], str]]:
    files = sorted(cli.LABEL_DIR.glob("partial_credit__*.csv"))
    named = {f.stem.split("__", 1)[1]: f for f in files}
    if only:
        want = [r.lower() for r in only]
        missing = [r for r in want if r not in named]
        if missing:
            sys.exit(f"No label file for rater(s): {', '.join(missing)} in {cli.LABEL_DIR}")
        named = {r: named[r] for r in want}
    if len(named) > 2:
        sys.exit(f"Found {len(named)} rater files ({', '.join(sorted(named))}); the agreement "
                 "rule is defined for exactly two. Use --raters to pick the two that count.")
    return {name: cli.load_labels(path, warn=False) for name, path in sorted(named.items())}


def resolve_final_labels(
    rater_maps: dict[str, dict[tuple[str, str], str]],
    adjudicated: dict[tuple[str, str], str],
    pool_keys: set[tuple[str, str]],
) -> tuple[dict[tuple[str, str], int], dict[str, int]]:
    """Adjudicated > two-rater agreement > unresolved. Unresolved is counted, not dropped."""
    final: dict[tuple[str, str], int] = {}
    counts = {
        "pool_items": len(pool_keys),
        "from_adjudication": 0,
        "from_agreement": 0,
        "adjudicated_despite_agreement": 0,   # rater churn after adjudication; adjudication still wins
        "unresolved_disagreement": 0,
        "unresolved_partially_rated": 0,
        "unresolved_unrated": 0,
    }
    maps = list(rater_maps.values())
    for key in pool_keys:
        votes = [m[key] for m in maps if key in m]
        if key in adjudicated:
            final[key] = int(adjudicated[key])
            counts["from_adjudication"] += 1
            if len(votes) == 2 and votes[0] == votes[1]:
                counts["adjudicated_despite_agreement"] += 1
        elif len(votes) == 2 and votes[0] == votes[1]:
            final[key] = int(votes[0])
            counts["from_agreement"] += 1
        elif len(votes) == 2:
            counts["unresolved_disagreement"] += 1
        elif len(votes) == 1:
            counts["unresolved_partially_rated"] += 1
        else:
            counts["unresolved_unrated"] += 1
    counts["final_labels"] = len(final)
    return final, counts


def adjacent_residual(rater_maps: dict[str, dict[tuple[str, str], str]], final: dict[tuple[str, str], int],
                      pool_keys: set[tuple[str, str]]) -> dict[tuple[str, str], tuple[int, int]]:
    """Unresolved disagreements under E5 12.10.2026: allowed only exactly one step apart."""
    maps = list(rater_maps.values())
    residual, too_far = {}, []
    for key in sorted(pool_keys):
        if key in final:
            continue
        votes = [int(m[key]) for m in maps if key in m]
        if len(votes) != 2 or votes[0] == votes[1]:
            continue   # coverage gates elsewhere report these
        if abs(votes[0] - votes[1]) == 1:
            residual[key] = (votes[0], votes[1])
        else:
            too_far.append(f"{key[0]} {key[1][:12]}: {votes[0]} vs {votes[1]}")
    if too_far:
        sys.exit("Unresolved disagreements of two or more steps must be adjudicated, also under "
                 f"--allow-adjacent-residual: {len(too_far)} found, e.g. {too_far[:3]}")
    return residual


def build_reference(final: dict[tuple[str, str], int], residual: dict[tuple[str, str], tuple[int, int]],
                    policy: str) -> dict[tuple[str, str], tuple[tuple[int, float], ...]]:
    """Three-level reference: key -> ((class, weight), ...). Weights per item sum to 1 or the item is absent."""
    if policy not in REFERENCE_POLICIES:
        raise ValueError(f"Unknown reference policy {policy!r}")
    ref = {key: ((cli.aggregate_three_way(int(v)), 1.0),) for key, v in final.items()}
    for key, (x, y) in residual.items():
        a, b = cli.aggregate_three_way(x), cli.aggregate_three_way(y)
        if a == b:
            ref[key] = ((a, 1.0),)
        elif policy == "soft":
            ref[key] = ((min(a, b), 0.5), (max(a, b), 0.5))   # fixed order: stable export
        elif policy == "strict":
            ref[key] = ((min(a, b), 1.0),)
        elif policy == "lenient":
            ref[key] = ((max(a, b), 1.0),)
    return ref


def qwk_from_matrix(O: np.ndarray) -> np.ndarray:
    """Quadratic weighted kappa from (..., k, k) observed matrices with possibly fractional cells."""
    k = O.shape[-1]
    W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)], dtype=float) / (k - 1) ** 2
    n = O.sum(axis=(-2, -1))
    E = O.sum(axis=-1)[..., :, None] * O.sum(axis=-2)[..., None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        den = (W * E).sum(axis=(-2, -1)) / n
        return np.where(den > 0, 1.0 - (W * O).sum(axis=(-2, -1)) / den, np.nan)


def weighted_qwk(h: list[int], m: list[int], w: list[float], k: int = 3) -> float:
    if not (len(h) == len(m) == len(w)) or any(x not in range(k) for x in list(h) + list(m)):
        raise ValueError("Weighted QWK requires aligned labels within the explicit scale")
    if not h:
        return float("nan")
    O = np.zeros((k, k))
    np.add.at(O, (np.asarray(h), np.asarray(m)), np.asarray(w, dtype=float))
    return float(qwk_from_matrix(O))


def _item_matrices(rows: list[tuple]) -> tuple[list, np.ndarray]:
    """Per unique item: summed weighted confusion counts over its (broadcast) prediction rows."""
    keys = sorted({r[1] for r in rows})
    pos = {k: i for i, k in enumerate(keys)}
    M = np.zeros((len(keys), 3, 3))
    for _, key, h, m, w in rows:
        M[pos[key], h, m] += w
    return keys, M


def reference_block(sl: pd.DataFrame, ref: dict, n_boot: int, seed: int) -> dict:
    """Weighted metrics of the model level against one three-level reference, pooled (with bootstrap) and per question."""
    rows, row_ids = [], set()
    for idx, qid, key, ml in zip(sl.index, sl["QuestionID"], sl["key"], sl["model_level"]):
        if pd.isna(ml):
            continue
        for h, w in ref.get(key, ()):
            rows.append((qid, key, int(h), int(ml), float(w)))
            row_ids.add(idx)

    def summary(rs: list[tuple]) -> dict:
        if not rs:
            return {"qwk": None, "exact": None, "within_1": None, "weight": 0.0}
        h = [r[2] for r in rs]; m = [r[3] for r in rs]; w = np.array([r[4] for r in rs])
        q = weighted_qwk(h, m, list(w))
        diff = np.abs(np.array(h) - np.array(m))
        return {"qwk": None if math.isnan(q) else q, "exact": float(w[diff == 0].sum() / w.sum()),
                "within_1": float(w[diff <= 1].sum() / w.sum()), "weight": float(w.sum())}

    out = summary(rows)
    out.update(n_rows=len(row_ids), n_items=len({r[1] for r in rows}), qwk_ci=None, exact_ci=None)
    if rows and n_boot:
        keys, M = _item_matrices(rows)
        rng = np.random.default_rng(seed)
        draws = rng.integers(0, len(keys), size=(n_boot, len(keys)))
        counts = np.stack([np.bincount(d, minlength=len(keys)) for d in draws]).astype(float)
        Ob = np.tensordot(counts, M, axes=(1, 0))            # (n_boot, 3, 3)
        q = qwk_from_matrix(Ob)
        ex = np.trace(Ob, axis1=1, axis2=2) / Ob.sum(axis=(1, 2))
        q = q[~np.isnan(q)]
        out["qwk_ci"] = [float(np.percentile(q, 2.5)), float(np.percentile(q, 97.5))] if len(q) else None
        out["exact_ci"] = [float(np.percentile(ex, 2.5)), float(np.percentile(ex, 97.5))]
    out["questions"] = {}
    for qid in sorted({r[0] for r in rows}):
        rs = [r for r in rows if r[0] == qid]
        qs = summary(rs)
        qs.update(n_rows=int(sum(1 for i, x in zip(sl.index, sl["QuestionID"]) if x == qid and i in row_ids)),
                  n_items=len({r[1] for r in rs}))
        out["questions"][qid] = qs
    return out


def discover_runs(pred_root: Path) -> dict[str, Path]:
    """Deprecated: discovery cannot determine which scientific run was planned."""
    raise ValueError("Run discovery is forbidden; supply --manifest and --cells")


def model_metrics(pred_csv: Path, final: dict[tuple[str, str], int],
                  pool_keys: set[tuple[str, str]], n_examples: int, *, strict=False,
                  source_pool_csv: Path | None = None, references: dict | None = None,
                  n_boot: int = 0, seed: int = 42) -> dict:
    df = pd.read_csv(pred_csv, keep_default_na=False,
                     dtype={"answer_text": str, "QuestionID": str, "user_id": str})
    sl = df[df["n_examples"] == n_examples].copy()
    if sl.empty:
        sys.exit(f"{pred_csv} has no rows at n_examples == {n_examples}; "
                 f"present: {sorted(df['n_examples'].unique().tolist())}")
    sl["answer_text"] = sl["answer_text"].fillna("").astype(str)
    sl["key"] = list(zip(sl["QuestionID"].astype(str), sl["answer_text"].map(sha256_text)))

    # The pool is pinned; the prediction slice must hash to exactly the same universe.
    # A mismatch means the texts differ from what the raters graded, and every broadcast
    # after that point would be a lie, so this is fatal rather than a warning.
    slice_keys = set(sl["key"])
    if slice_keys != pool_keys:
        sys.exit(f"{pred_csv}: prediction texts do not reproduce the pinned pool "
                 f"({len(slice_keys - pool_keys)} keys not in pool, "
                 f"{len(pool_keys - slice_keys)} pool keys missing).")
    if strict and (len(sl) != 450 or len(slice_keys) != 439):
        sys.exit(f"{pred_csv}: expected 450 n=40 rows broadcasting to 439 unique pool items; "
                 f"got {len(sl)} rows and {len(slice_keys)} items")
    if strict:
        if source_pool_csv is None:
            sys.exit("Strict model join needs the pinned 450-row source pool")
        source = pd.read_csv(source_pool_csv, keep_default_na=False,
                             dtype={"QuestionID": str, "user_id": str, "answer_text": str})
        if len(source) != 450 or "user_id" not in sl:
            sys.exit("Source identity gate requires 450 pool rows and prediction user IDs")
        def identities(frame):
            return Counter((str(q), str(u), sha256_text(str(a)))
                           for q, u, a in zip(frame["QuestionID"], frame["user_id"], frame["answer_text"]))
        source_ids, prediction_ids = identities(source), identities(sl)
        if source_ids != prediction_ids:
            missing = sum((source_ids - prediction_ids).values())
            extra = sum((prediction_ids - source_ids).values())
            sys.exit(f"{pred_csv}: 450-row source identity/multiplicity mismatch "
                     f"({missing} missing, {extra} extra)")

    sl["human_level_raw_0_4"] = sl["key"].map(final)
    aggregated = {key: cli.aggregate_three_way(value) for key, value in final.items()}
    sl["human_level"] = sl["key"].map(aggregated)
    sl["model_level"] = meu.coerce_ordinal(sl["level"]) if "level" in sl.columns else float("nan")

    # Context metric: the existing binary accuracy over aligned pairs, unchanged.
    binary = pd.DataFrame({
        "pred": meu.coerce_binary(sl["re_eval_score"]),
        "gold": meu.coerce_binary(sl["human_answer_correct"]),
    }).dropna()
    binary_acc = float((binary["pred"] == binary["gold"]).mean()) if len(binary) else None

    pairs = sl.dropna(subset=["human_level", "model_level"])
    out = {
        "predictions_csv": rel(pred_csv),
        "run": pred_csv.parents[2].name,
        "n_examples": n_examples,
        "label_scale": cli.LABEL_SCALE,
        "analysis_scale": "0/1/2, mapping 0/1/1/1/2",
        "n_rows": int(len(sl)),
        "n_distinct_items": int(len(slice_keys)),
        "model_level_parse_failures": int(sl["model_level"].isna().sum()),
        "n_rows_with_human_label": int(len(pairs)),
        "n_items_with_human_label": int(len(set(pairs["key"]))),
        "qwk": None, "exact_agreement": None, "within_1_agreement": None,
        "binary_accuracy": binary_acc,
        "n_binary_aligned_pairs": int(len(binary)),
    }
    if len(pairs):
        h = pairs["human_level"].astype(int).tolist()
        m = pairs["model_level"].astype(int).tolist()
        qwk = cli.quadratic_weighted_kappa(h, m, k=3)
        out["qwk"] = None if math.isnan(qwk) else float(qwk)
        out["exact_agreement"] = float(sum(1 for a, b in zip(h, m) if a == b) / len(h))
        out["within_1_agreement"] = float(sum(1 for a, b in zip(h, m) if abs(a - b) <= 1) / len(h))
    out["questions"] = {}
    for qid, group in sorted(sl.groupby("QuestionID")):
        aligned = group.dropna(subset=["human_level", "model_level"])
        h = aligned["human_level"].astype(int).tolist()
        m = aligned["model_level"].astype(int).tolist()
        qwk = cli.quadratic_weighted_kappa(h, m, k=3) if h else float("nan")
        out["questions"][qid] = {
            "model_rows": int(len(group)), "unique_human_items": int(len(set(group["key"]))),
            "aligned_rows": int(len(aligned)), "qwk3": None if math.isnan(qwk) else qwk,
            "exact": sum(x == y for x, y in zip(h, m)) / len(h) if h else None,
            "within_1": sum(abs(x-y) <= 1 for x, y in zip(h, m)) / len(h) if h else None,
        }
    if references:
        # E5 adjacent-residual mode: the headline fields describe the primary reference, never the
        # consensus-only subset; every policy is kept beside it.
        blocks = {name: reference_block(sl, ref, n_boot, seed) for name, ref in references.items()}
        p = blocks[PRIMARY_POLICY]
        out.update(qwk=p["qwk"], exact_agreement=p["exact"], within_1_agreement=p["within_1"],
                   n_rows_with_human_label=p["n_rows"], n_items_with_human_label=p["n_items"],
                   primary_reference=PRIMARY_POLICY, reference_policies=blocks,
                   questions={q: {"model_rows": out["questions"][q]["model_rows"],
                                  "unique_human_items": out["questions"][q]["unique_human_items"],
                                  "aligned_rows": v["n_rows"], "qwk3": v["qwk"], "exact": v["exact"],
                                  "within_1": v["within_1"]} for q, v in p["questions"].items()})
    return out


def merge_summary(json_path: Path, payload: dict) -> dict:
    """Retain same-manifest cell entries from an earlier partial invocation."""
    merged_models: dict[str, dict] = {}
    if json_path.exists():
        try:
            merged_models = dict(json.loads(json_path.read_text(encoding="utf-8")).get("models", {}))
        except (json.JSONDecodeError, AttributeError, TypeError):
            raise ValueError(f"{json_path}: unreadable existing report; preserve and restore it first.")
    merged_models.update(payload["models"])
    payload["models"] = {k: merged_models[k] for k in sorted(merged_models)}
    return payload


def fmt(v, pct: bool = False) -> str:
    if v is None:
        return "-"
    return f"{v:.1%}" if pct else f"{v:.3f}"


def render_markdown(payload: dict) -> str:
    hl = payload["human_labels"]
    lines = [
        "# Partial credit: model `level` vs human five-level label aggregated to 0/1/2",
        "",
        f"Generated {payload['generated_at_utc']}. Current invocation operating point: **n_examples == "
        f"{payload['operating_point']['n_examples']}**"
        + (" (the pre-registered operating point, ANALYSIS_PLAN.md)."
           if payload["operating_point"]["preregistered"] else " (NOT the pre-registered operating point)."),
        "",
        f"Human labels: {hl['final_labels']} of {hl['pool_items']} pool items resolved "
        f"({hl['from_adjudication']} adjudicated, {hl['from_agreement']} by agreement); "
        f"unresolved: {hl['unresolved_disagreement']} disagreements, "
        f"{hl['unresolved_partially_rated']} rated by one rater, "
        f"{hl['unresolved_unrated']} unrated.",
        "",
        "Retained entries are marked STALE when their operating point or label snapshot differs.",
        "",
        "| model | run | n_examples | snapshot | items labelled | QWK | exact | within-1 | binary acc (context) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for model, m in payload["models"].items():
        current = (m.get("n_examples") == payload["operating_point"]["n_examples"]
                   and json.dumps(m.get("human_label_state"), sort_keys=True)
                   == json.dumps(hl, sort_keys=True))
        snapshot = "current" if current else "STALE: different operating point or label snapshot"
        lines.append(
            f"| {model} | {m['run']} | {m.get('n_examples', 'unknown')} | {snapshot} | {m['n_rows_with_human_label']}/{m['n_rows']} rows | "
            f"{fmt(m['qwk'])} | {fmt(m['exact_agreement'], pct=True)} | "
            f"{fmt(m['within_1_agreement'], pct=True)} | {fmt(m['binary_accuracy'])} |")
    lines.extend(["", "## Per-question ordinal comparison", "",
                  "| cell | question | model rows | distinct human items | aligned rows | QWK3 | exact | within-1 |",
                  "|---|---|---:|---:|---:|---:|---:|---:|"])
    for cell_id, m in payload["models"].items():
        for question, q in m.get("questions", {}).items():
            lines.append(f"| {cell_id} | {question} | {q['model_rows']} | {q['unique_human_items']} | "
                         f"{q['aligned_rows']} | {fmt(q['qwk3'])} | {fmt(q['exact'], pct=True)} | "
                         f"{fmt(q['within_1'], pct=True)} |")
    if any("reference_policies" in m for m in payload["models"].values()):
        lines.extend(["", "## Reference policies (E5 12.10.2026, adjacent residual disagreement)", "",
                      f"Primary: **{PRIMARY_POLICY}**. Boundary items (3/4, 0/1) left unresolved: "
                      f"{hl.get('adjacent_residual_boundary')}; adjacent inside the 1-3 band (determined): "
                      f"{hl.get('adjacent_residual_within_band')}. Bootstrap: {BOOTSTRAP['resamples']} resamples "
                      f"over unique answer texts, seed {BOOTSTRAP['seed']}, percentile 95%.", "",
                      "| cell | policy | rows | weight | QWK3 | 95% CI | exact | 95% CI | within-1 |",
                      "|---|---|---:|---:|---:|---|---:|---|---:|"])
        ci = lambda c, pct=False: "-" if not c else f"[{fmt(c[0], pct)}, {fmt(c[1], pct)}]"
        for cell_id, m in payload["models"].items():
            for pol, b in m.get("reference_policies", {}).items():
                lines.append(f"| {cell_id} | {pol} | {b['n_rows']} | {b['weight']:.1f} | {fmt(b['qwk'])} | {ci(b['qwk_ci'])} | "
                             f"{fmt(b['exact'], pct=True)} | {ci(b['exact_ci'], True)} | {fmt(b['within_1'], pct=True)} |")
    lines += [
        "",
        "Reference lines (mandatory, ANALYSIS_PLAN.md section 3; they bound the binary",
        "accuracy column, not the QWK):",
        "",
        f"- incumbent-agreement reference: **{REFERENCE_LINES['incumbent_agreement_binary_accuracy']:.4f}** "
        "(407/450, a trivial oracle repeating the deployed grader)",
        f"- majority class: **{REFERENCE_LINES['majority_class_binary_accuracy']:.4f}** "
        "(252/450, always predict \"correct\")",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pred-root", type=Path, default=DEFAULT_PRED_ROOT,
                    help="root containing the *partial_credit* run directories")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                    help="where the JSON and markdown summaries are written")
    ap.add_argument("--raters", nargs="+", help="restrict to these raters' label files")
    ap.add_argument("--agreement-report", type=Path, required=True,
                    help="immutable pre-adjudication report matching the raw logs")
    ap.add_argument("--n-examples", type=int, default=PREREGISTERED_N,
                    help=f"operating point (default {PREREGISTERED_N}, the pre-registered one)")
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--cells", nargs="+", required=True, help="explicit cell IDs in the pinned manifest")
    ap.add_argument("--allow-adjacent-residual", action="store_true",
                    help="E5 12.10.2026: adjacent disagreements may stay unresolved; reference policies apply")
    args = ap.parse_args()
    with cli.label_safety.session_lock(cli.LABEL_DIR / ".session"), cli.label_safety.session_lock(args.out_dir / ".analysis"):
        return run_analysis(args)


def run_analysis(args) -> int:
    pool = cli.load_pool()   # validates the pinned sha256 / row count / question count
    pool_keys = {(r["QuestionID"], r["answer_text_sha256"]) for r in pool}

    rater_maps = load_rater_maps(args.raters)
    if len(rater_maps) != 2:
        sys.exit("Exactly two complete rater files are required before model comparison.")
    for labels in rater_maps.values():
        cli.validate_coverage(labels, pool_keys, complete=True)
    cli.validate_agreement_archive(args.agreement_report, list(rater_maps))
    adjudicated = cli.load_adjudicated(ADJUDICATED, rater_maps, pool_keys)
    unknown = set(adjudicated) - pool_keys
    if unknown:
        sys.exit(f"{ADJUDICATED.name} contains {len(unknown)} key(s) outside the pinned pool.")
    final, counts = resolve_final_labels(rater_maps, adjudicated, pool_keys)
    residual = adjacent_residual(rater_maps, final, pool_keys) if args.allow_adjacent_residual else {}
    if (counts["unresolved_disagreement"] - len(residual) or counts["final_labels"] + len(residual) != len(pool_keys)
            or len(pool_keys) != 439):
        sys.exit("Final model comparison blocked: unresolved disputes or fewer than 439 final labels"
                 + ("" if args.allow_adjacent_residual else " (E5 adjacent residual needs --allow-adjacent-residual)"))
    references = None
    if residual:
        references = {pol: build_reference(final, residual, pol) for pol in REFERENCE_POLICIES}
        boundary = sum(1 for x, y in residual.values() if cli.aggregate_three_way(x) != cli.aggregate_three_way(y))
        counts["adjacent_residual"] = len(residual)
        counts["adjacent_residual_boundary"] = boundary
        counts["adjacent_residual_within_band"] = len(residual) - boundary
        counts["e5_rule"] = "2026-10-12: adjudicate gaps >= 2, adjacent disagreements may stay unresolved"
        counts["primary_reference"] = PRIMARY_POLICY
        counts["bootstrap"] = BOOTSTRAP

    print(f"Human label state ({', '.join(rater_maps) or 'no rater files yet'}):")
    print(f"  {counts['final_labels']} of {counts['pool_items']} pool items resolved "
          f"({counts['from_adjudication']} adjudicated, {counts['from_agreement']} by agreement)")
    print(f"  unresolved: {counts['unresolved_disagreement']} disagreements, "
          f"{counts['unresolved_partially_rated']} rated by one rater, "
          f"{counts['unresolved_unrated']} unrated")
    if residual:
        print(f"  E5 adjacent residual: {counts['adjacent_residual']} ({counts['adjacent_residual_boundary']} on a "
              f"three-level boundary, {counts['adjacent_residual_within_band']} inside the 1-3 band); primary reference "
              f"'{PRIMARY_POLICY}', sensitivities {', '.join(p for p in REFERENCE_POLICIES if p != PRIMARY_POLICY)}")
    if counts["adjudicated_despite_agreement"]:
        print(f"  note: {counts['adjudicated_despite_agreement']} adjudication(s) override a "
              "current rater agreement (a rater changed a label after adjudication)")

    manifest_doc, selected = manifest.validate(args.manifest, args.cells, root=REPO_ROOT,
                                                n_examples=args.n_examples, pool_sha256=cli.POOL_SHA256)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    label_state = dict(counts)
    label_state["label_scale"] = cli.LABEL_SCALE
    label_state["analysis_mapping"] = cli.THREE_WAY
    label_state["raw_labels_sha256"] = hashlib.sha256(json.dumps(
        {name: sorted((q, h, v) for (q, h), v in labels.items())
         for name, labels in sorted(rater_maps.items())}, sort_keys=True).encode()).hexdigest()
    label_state["adjudicated_sha256"] = hashlib.sha256(json.dumps(
        sorted((q, h, v) for (q, h), v in adjudicated.items())).encode()).hexdigest()
    models = {}
    for cell_id, (cell, pred_csv) in sorted(selected.items()):
        m = model_metrics(pred_csv, final, pool_keys, args.n_examples, strict=True,
                          source_pool_csv=cell["_source_pool_path"], references=references,
                          n_boot=BOOTSTRAP["resamples"], seed=BOOTSTRAP["seed"])
        m["cell_id"] = cell_id
        m["model_id"] = cell["model"]
        m["prompt"] = cell["prompt"]
        m["decoding"] = cell["decoding"]
        m["predictions_sha256"] = cell["predictions_sha256"]
        m["manifest_sha256"] = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
        m["generated_at_utc"] = now
        m["human_label_state"] = label_state
        models[cell_id] = m

    preregistered = args.n_examples == PREREGISTERED_N
    print(f"\nOperating point: n_examples == {args.n_examples}"
          + (" (the pre-registered operating point)" if preregistered
             else "  ** NOT the pre-registered operating point (40) **"))
    header = f"{'model':<44} {'labelled':>10} {'QWK':>7} {'exact':>7} {'w/in-1':>7} {'bin acc':>8}"
    print("\n" + header)
    print("-" * len(header))
    for model, m in models.items():
        print(f"{model:<44} {m['n_rows_with_human_label']:>6}/{m['n_rows']:<3} "
              f"{fmt(m['qwk']):>7} {fmt(m['exact_agreement'], pct=True):>7} "
              f"{fmt(m['within_1_agreement'], pct=True):>7} {fmt(m['binary_accuracy']):>8}")
    print("\nReference lines (mandatory, ANALYSIS_PLAN.md section 3; binary-accuracy references,")
    print("they bound the last column, not the QWK):")
    print(f"  incumbent-agreement reference  {REFERENCE_LINES['incumbent_agreement_binary_accuracy']:.4f}  "
          "(407/450, trivial oracle repeating the deployed grader)")
    print(f"  majority class     {REFERENCE_LINES['majority_class_binary_accuracy']:.4f}  "
          "(252/450, always predict \"correct\")")

    payload = {
        "generated_at_utc": now,
        "operating_point": {"n_examples": args.n_examples, "preregistered": preregistered},
        "pool_sha256": cli.POOL_SHA256,
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "analysis_plan_sha256": manifest_doc["analysis_plan_sha256"],
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "agreement_report_sha256": hashlib.sha256(args.agreement_report.read_bytes()).hexdigest(),
        "agreement_archive_sha256": hashlib.sha256(cli.agreement_archive_path(args.agreement_report).read_bytes()).hexdigest(),
        "adjudication_log_sha256": hashlib.sha256(ADJUDICATED.read_bytes()).hexdigest() if ADJUDICATED.exists() else None,
        "label_scale": cli.LABEL_SCALE,
        "reference_lines": REFERENCE_LINES,
        "human_labels": label_state,
        "raters": sorted(rater_maps),
        "models": models,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "partial_credit_model_vs_human_five_level.json"
    if json_path.exists():
        old = json.loads(json_path.read_text(encoding="utf-8"))
        if old.get("manifest_sha256") != payload["manifest_sha256"] or old.get("human_labels") != label_state:
            raise ValueError("Existing report has a different manifest or raw-label state; use a fresh output directory")
        payload = merge_summary(json_path, payload)
    # Lossless analysis export: retain both five-level consensus and its derived model scale.
    import csv
    import io
    with io.StringIO(newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["QuestionID", "answer_text_sha256", "human_level_0_4",
                                          "human_level_0_2", "label_scale", "pool_sha256"])
        w.writeheader()
        for (qid, sha), value in sorted(final.items()):
            w.writerow({"QuestionID": qid, "answer_text_sha256": sha, "human_level_0_4": value,
                        "human_level_0_2": cli.aggregate_three_way(value),
                        "label_scale": cli.LABEL_SCALE, "pool_sha256": cli.POOL_SHA256})
        cli.label_safety.atomic_write(args.out_dir / "partial_credit_consensus_five_level.csv", fh.getvalue())
    if residual:
        # Lossless reference export for all 439 items: resolution, both raw levels, mean, three-level class or soft weights.
        names = sorted(rater_maps)
        with io.StringIO(newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["QuestionID", "answer_text_sha256", "resolution",
                                              *[f"{n}_0_4" for n in names], "human_level_0_4", "human_mean_0_4",
                                              "human_level_0_2", "soft_0_2", "label_scale", "pool_sha256"])
            w.writeheader()
            soft = references["soft"]
            for key in sorted(pool_keys):
                lv = {n: int(rater_maps[n][key]) for n in names}
                if key in residual:
                    res, level, mean = "adjacent_residual", "", sum(lv.values()) / 2
                else:
                    res = "adjudicated" if key in adjudicated else "agreement"
                    level, mean = final[key], float(final[key])
                classes = soft[key]
                w.writerow({"QuestionID": key[0], "answer_text_sha256": key[1], "resolution": res,
                            **{f"{n}_0_4": lv[n] for n in names}, "human_level_0_4": level, "human_mean_0_4": mean,
                            "human_level_0_2": classes[0][0] if len(classes) == 1 else "",
                            "soft_0_2": ";".join(f"{c}:{wt:g}" for c, wt in classes),
                            "label_scale": cli.LABEL_SCALE, "pool_sha256": cli.POOL_SHA256})
            cli.label_safety.atomic_write(args.out_dir / "partial_credit_reference_adjacent_residual.csv", fh.getvalue())
    cli.label_safety.atomic_write(json_path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    md_path = args.out_dir / "partial_credit_model_vs_human_five_level.md"
    cli.label_safety.atomic_write(md_path, render_markdown(payload))
    print(f"\nsummary -> {rel(json_path)}")
    print(f"table   -> {rel(md_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
