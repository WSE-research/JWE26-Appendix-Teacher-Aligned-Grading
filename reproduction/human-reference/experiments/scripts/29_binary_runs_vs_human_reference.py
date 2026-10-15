#!/usr/bin/env python3
"""Exploratory: every selected binary JWE run against the binarised human reference (E5 of 12.10.2026).

    python experiments/scripts/29_binary_runs_vs_human_reference.py \
        --reference experiments/outputs/jwe_consensus/2026-10-12_e5_adjacent_residual/partial_credit_reference_adjacent_residual.csv \
        --out-dir experiments/outputs/jwe_consensus/2026-10-12_binary_runs_vs_reference

Only four runs used the partial-credit prompt (25_ compares their 0/1/2 levels). All other selected runs
grade binary (`re_eval_score`, correct/incorrect) and were so far compared only with the historical teacher
label. This script compares every non-diagnostic run of the pinned study selection
(`experiments/docs/jwe_study_run_selection_20260916.json`, LF-canonical predictions hashes checked) at
n_examples=40 with the human reference made binary:

* threshold 3 (primary): human level >= 3 counts as correct. Figure 8 of the pre-adjudication report shows
  that level >= 3 matches the historical binary label best; threshold 4 (only full credit counts) is the
  strict sensitivity.
* reference per item, as in 25_: agreement and adjudicated items carry their level; an adjacent residual
  disagreement is determined when both levels fall on the same side of the threshold, otherwise it enters
  with weight 1/2 for each side ("soft", the binary analogue of 25_'s primary policy). Under threshold 3
  that concerns the 2/3 pairs, under threshold 4 the 3/4 pairs.

Join: predictions map to pool items by (QuestionID, SHA-256 of the answer text). Fourteen later runs
(August 28 API runs, September 1 t0 runs) store the same answers with CRLF line breaks normalised to LF;
their rows are joined by the hash of the LF-normalised text, which must be unique within each question,
and the number of rows joined this way is reported per run.

Metrics per run (450 prediction rows, unparsable predictions dropped and counted): weighted accuracy and
Cohen's kappa against the reference, plain accuracy and kappa against the teacher label on the same rows,
and the difference. Kappa with percentile bootstrap over unique answer texts (rows of one text move
together), 2,000 resamples, seed 42. Human reference lines on the same 450 rows: Jonas and Andreas each
against the teacher label, and Jonas against Andreas (both binarised). Exploratory under ANALYSIS_PLAN.md
section 6; the threshold and the selection of headline arms are author decisions.
Thresholds 1 and 2 are computed as well, only to show how agreement depends on the cut.

Advisory-note sensitivity (with --protocol): the jointly adjudicated decisions taken while the
LLM advisory note (Claude) was visible are replaced by the two coders' halves (each coder's
binary class with weight 1/2, or weight 1 when both agree), at the primary threshold, for every
run and for the teacher label. Same item set; isolates the effect of those decisions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import manual_eval_utils as meu  # noqa: E402
from jwe_run_manifest import portable_text_sha256  # noqa: E402

SELECTION = REPO_ROOT / "experiments" / "docs" / "jwe_study_run_selection_20260916.json"
POOL = REPO_ROOT / "experiments" / "data" / "manual_eval" / "labelling_pool.csv"
N_EXAMPLES = "40"
THRESHOLDS = (1, 2, 3, 4)   # 3 primary, 4 strict; 1 and 2 only to show that no other cut fits better
PRIMARY_THRESHOLD = 3
BOOT = {"resamples": 2000, "seed": 42, "unit": "unique (QuestionID, answer_text_sha256)", "interval": "percentile 95%"}
# One binary base arm per model: the arms the selection names as each model's base condition at t0.2, n40.
HEADLINE_ROLES = ("original_base", "new_base", "s3_gate", "currency_tier")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_reference(path: Path) -> dict[tuple[str, str], dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    ref = {}
    for r in rows:
        key = (r["QuestionID"], r["answer_text_sha256"])
        if key in ref:
            raise ValueError(f"duplicate reference item {key}")
        j, a = int(r["jonas_0_4"]), int(r["andreas_0_4"])
        res = r["resolution"]
        if res not in ("agreement", "adjudicated", "adjacent_residual"):
            raise ValueError(f"unknown resolution {res!r}")
        level = None if res == "adjacent_residual" else int(r["human_level_0_4"])
        if res == "adjacent_residual" and abs(j - a) != 1:
            raise ValueError(f"{key}: residual disagreement is not adjacent")
        ref[key] = {"j": j, "a": a, "res": res, "level": level}
    return ref


def binary_reference(ref: dict, threshold: int) -> dict[tuple[str, str], tuple[tuple[int, float], ...]]:
    """key -> ((class, weight), ...); class 1 = correct (level >= threshold)."""
    out = {}
    for key, r in ref.items():
        if r["level"] is not None:
            out[key] = ((int(r["level"] >= threshold), 1.0),)
        else:
            bj, ba = int(r["j"] >= threshold), int(r["a"] >= threshold)
            out[key] = ((bj, 1.0),) if bj == ba else ((0, 0.5), (1, 0.5))
    return out


def kappa_from_matrix(O: np.ndarray) -> np.ndarray:
    """Cohen's kappa from (..., 2, 2) observed matrices with possibly fractional cells."""
    n = O.sum(axis=(-2, -1))
    po = (O[..., 0, 0] + O[..., 1, 1]) / n
    pe = (O.sum(axis=-1)[..., 0] * O.sum(axis=-2)[..., 0] + O.sum(axis=-1)[..., 1] * O.sum(axis=-2)[..., 1]) / n ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(pe < 1, (po - pe) / (1 - pe), np.nan)


def block(keys: list, pred: list[int], ref: dict, n_boot: int, seed: int) -> dict:
    """Weighted agreement of binary predictions (one per row) with a weighted reference, plus bootstrap."""
    rows = [(k, h, p, w) for k, p in zip(keys, pred) for h, w in ref[k]]
    items = sorted({r[0] for r in rows})
    pos = {k: i for i, k in enumerate(items)}
    M = np.zeros((len(items), 2, 2))
    for k, h, p, w in rows:
        M[pos[k], h, p] += w
    O = M.sum(axis=0)
    out = {"kappa": float(kappa_from_matrix(O)), "accuracy": float((O[0, 0] + O[1, 1]) / O.sum()),
           "rate_correct_reference": float(O[1].sum() / O.sum()), "rate_correct_model": float(O[:, 1].sum() / O.sum()),
           "n_rows": len(keys), "n_items": len(items), "kappa_ci": None, "accuracy_ci": None}
    if n_boot:
        rng = np.random.default_rng(seed)
        draws = rng.integers(0, len(items), size=(n_boot, len(items)))
        counts = np.stack([np.bincount(d, minlength=len(items)) for d in draws]).astype(float)
        Ob = np.tensordot(counts, M, axes=(1, 0))
        k = kappa_from_matrix(Ob); acc = (Ob[:, 0, 0] + Ob[:, 1, 1]) / Ob.sum(axis=(1, 2))
        k = k[~np.isnan(k)]
        out["kappa_ci"] = [float(np.percentile(k, 2.5)), float(np.percentile(k, 97.5))]
        out["accuracy_ci"] = [float(np.percentile(acc, 2.5)), float(np.percentile(acc, 97.5))]
    return out


def lf_index(pool_path: Path) -> dict[tuple[str, str], tuple[str, str]]:
    """(QuestionID, sha256 of the LF-normalised text) -> pool key; refuses collisions."""
    with pool_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = {}
    for r in rows:
        k = (r["QuestionID"], sha256_text(r["answer_text"].replace("\r\n", "\n")))
        if k in out:
            raise ValueError(f"LF-normalised text is not unique in {r['QuestionID']}")
        out[k] = (r["QuestionID"], r["answer_text_sha256"])
    return out


def load_slice(source: dict, pool_keys: set, lf: dict | None = None) -> pd.DataFrame:
    path = REPO_ROOT / source["files"]["predictions"]["path"]
    if portable_text_sha256(path) != source["files"]["predictions"]["sha256_lf"]:
        raise ValueError(f"{source['source_id']}: predictions hash differs from the pinned selection")
    df = pd.read_csv(path, keep_default_na=False, dtype=str)
    if "model" in df.columns:
        df = df[df["model"] == source["model"]]
    sl = df[df["n_examples"] == N_EXAMPLES].copy()
    keys, via_lf = [], 0
    for q, t in zip(sl["QuestionID"], sl["answer_text"]):
        k = (q, sha256_text(t))
        if k not in pool_keys and lf is not None:
            k2 = lf.get((q, sha256_text(t.replace("\r\n", "\n"))))
            if k2 is not None:
                k, via_lf = k2, via_lf + 1
        keys.append(k)
    sl["key"] = keys
    sl.attrs["rows_joined_via_lf"] = via_lf
    if len(sl) != 450 or set(sl["key"]) != pool_keys:
        raise ValueError(f"{source['source_id']}: n=40 slice is not the 450-row / 439-item pool ({len(sl)} rows)")
    sl["pred"] = meu.coerce_binary(sl["re_eval_score"])
    sl["teacher"] = meu.coerce_binary(sl["human_answer_correct"])
    return sl


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", type=Path, required=True, help="25_ export partial_credit_reference_adjacent_residual.csv")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--boot", type=int, default=BOOT["resamples"])
    ap.add_argument("--protocol", type=Path, help="adjudication meeting protocol (JSON) for the advisory-note sensitivity")
    args = ap.parse_args(argv)

    ref = load_reference(args.reference)
    if len(ref) != 439:
        sys.exit(f"reference has {len(ref)} items, expected 439")
    pool_keys = set(ref)
    refs = {T: binary_reference(ref, T) for T in THRESHOLDS}
    hint = None
    if args.protocol:
        proto = json.loads(args.protocol.read_text(encoding="utf-8"))
        visible = {tuple(e["key"].split("\x00")) for e in proto["events"] if e["advisory_note"]["visible_at_decision"]}
        if not visible <= {k for k, r in ref.items() if r["res"] == "adjudicated"}:
            sys.exit("advisory-visible decisions must be adjudicated reference items")
        hint = dict(refs[PRIMARY_THRESHOLD])
        for k in visible:
            bj, ba = int(ref[k]["j"] >= PRIMARY_THRESHOLD), int(ref[k]["a"] >= PRIMARY_THRESHOLD)
            hint[k] = ((bj, 1.0),) if bj == ba else ((0, 0.5), (1, 0.5))
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    sources = [s for s in selection["sources"] if s["role"] != "diagnostic"]
    lf = lf_index(POOL)

    teacher_by_key, results = None, []
    for s in sources:
        sl = load_slice(s, pool_keys, lf)
        teach = {k: int(v) for k, v in zip(sl["key"], sl["teacher"]) if not pd.isna(v)}
        if len(teach) != 439:
            sys.exit(f"{s['source_id']}: teacher label missing for some items")
        if teacher_by_key is None:
            teacher_by_key = teach
        elif teach != teacher_by_key:
            sys.exit(f"{s['source_id']}: teacher labels differ from the first run")
        ok = sl.dropna(subset=["pred"])
        keys, pred = list(ok["key"]), [int(x) for x in ok["pred"]]
        teacher_ref = {k: ((v, 1.0),) for k, v in teacher_by_key.items()}
        entry = {"source_id": s["source_id"], "run_id": s["run_id"], "model": s["model"], "role": s["role"],
                 "condition_id": s["condition_id"], "temperature": s["decoding"].get("temperature"),
                 "headline": s["role"] in HEADLINE_ROLES, "parse_failures": int(sl["pred"].isna().sum()),
                 "rows_joined_via_lf": sl.attrs["rows_joined_via_lf"],
                 "teacher": block(keys, pred, teacher_ref, 0, BOOT["seed"])}
        for T in THRESHOLDS:
            entry[f"reference_t{T}"] = block(keys, pred, refs[T], args.boot if entry["headline"] or T == PRIMARY_THRESHOLD else 0, BOOT["seed"])
        if hint is not None:
            entry["reference_t3_hint_halves"] = block(keys, pred, hint, 0, BOOT["seed"])
        entry["delta_kappa_reference_minus_teacher"] = entry[f"reference_t{PRIMARY_THRESHOLD}"]["kappa"] - entry["teacher"]["kappa"]
        results.append(entry)

    # human reference lines on the same 450 rows (row multiplicity of the first run)
    sl0 = load_slice(sources[0], pool_keys, lf)
    keys0 = list(sl0["key"])
    humans = {}
    for T in THRESHOLDS:
        bj = [int(ref[k]["j"] >= T) for k in keys0]; ba = [int(ref[k]["a"] >= T) for k in keys0]
        tref = {k: ((v, 1.0),) for k, v in teacher_by_key.items()}
        jref = {k: ((int(ref[k]["j"] >= T), 1.0),) for k in ref}
        humans[f"t{T}"] = {"jonas_vs_teacher": block(keys0, bj, tref, 0, 42), "andreas_vs_teacher": block(keys0, ba, tref, 0, 42),
                           "andreas_vs_jonas": block(keys0, ba, jref, BOOT["resamples"], BOOT["seed"]),
                           "teacher_vs_reference": block(keys0, [teacher_by_key[k] for k in keys0], refs[T], BOOT["resamples"], BOOT["seed"])}
    if hint is not None:
        humans["hint_halves_t3"] = {"teacher_vs_reference": block(keys0, [teacher_by_key[k] for k in keys0], hint, BOOT["resamples"], BOOT["seed"]),
                                    "advisory_visible_decisions": len(visible),
                                    "protocol_sha256": hashlib.sha256(args.protocol.read_bytes()).hexdigest()}
    counts = {f"t{T}": {"soft_items": sum(len(v) == 2 for v in refs[T].values()),
                        "reference_correct_rate_items": sum(sum(w for c, w in v if c == 1) for v in refs[T].values()) / 439} for T in THRESHOLDS}

    args.out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "status": "exploratory_binary_runs_vs_binarised_reference",
               "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "selection_sha256_lf": portable_text_sha256(SELECTION),
               "reference_csv": str(args.reference), "reference_sha256": hashlib.sha256(args.reference.read_bytes()).hexdigest(),
               "n_examples": int(N_EXAMPLES), "thresholds": list(THRESHOLDS), "primary_threshold": PRIMARY_THRESHOLD,
               "headline_roles": list(HEADLINE_ROLES), "bootstrap": BOOT, "reference_counts": counts,
               "humans": humans, "runs": results}
    (args.out_dir / "report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (args.out_dir / "runs.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "role", "condition_id", "temperature", "headline", "parse_failures", "kappa_teacher", "acc_teacher",
                    "kappa_ref_t3", "kappa_ref_t3_ci_low", "kappa_ref_t3_ci_high", "acc_ref_t3", "kappa_ref_t4", "acc_ref_t4",
                    "delta_kappa_t3_minus_teacher", "run_id"])
        for e in sorted(results, key=lambda e: (not e["headline"], -e["reference_t3"]["kappa"])):
            r3, r4, te = e["reference_t3"], e["reference_t4"], e["teacher"]
            w.writerow([e["model"], e["role"], e["condition_id"], e["temperature"], e["headline"], e["parse_failures"],
                        f"{te['kappa']:.4f}", f"{te['accuracy']:.4f}", f"{r3['kappa']:.4f}",
                        f"{r3['kappa_ci'][0]:.4f}" if r3["kappa_ci"] else "", f"{r3['kappa_ci'][1]:.4f}" if r3["kappa_ci"] else "",
                        f"{r3['accuracy']:.4f}", f"{r4['kappa']:.4f}", f"{r4['accuracy']:.4f}",
                        f"{e['delta_kappa_reference_minus_teacher']:+.4f}", e["run_id"]])
    print(f"{len(results)} runs, {sum(e['headline'] for e in results)} headline arms -> {args.out_dir}")
    for e in sorted((e for e in results if e["headline"]), key=lambda e: -e["reference_t3"]["kappa"]):
        r3 = e["reference_t3"]
        print(f"  {e['model']:<46} kappa ref(T3) {r3['kappa']:.3f} [{r3['kappa_ci'][0]:.3f}; {r3['kappa_ci'][1]:.3f}]  "
              f"teacher {e['teacher']['kappa']:.3f}  acc ref {r3['accuracy']:.3f}  T4 {e['reference_t4']['kappa']:.3f}  fail {e['parse_failures']}")
    for T in THRESHOLDS:
        h = humans[f"t{T}"]
        print(f"  humans T{T}: A vs J kappa {h['andreas_vs_jonas']['kappa']:.3f}, teacher vs ref {h['teacher_vs_reference']['kappa']:.3f}, "
              f"J vs teacher {h['jonas_vs_teacher']['kappa']:.3f}, A vs teacher {h['andreas_vs_teacher']['kappa']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
