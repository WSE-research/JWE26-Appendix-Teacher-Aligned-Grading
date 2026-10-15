#!/usr/bin/env python3
"""RQ1 evidence at n=40: agreement with the teacher label for every selected arm, recomputed from the
pinned prediction files, plus the reference lines, the S3 gate, the S6 subset split, P1 and an S1 check.

    python experiments/scripts/31_jwe_n40_agreement.py \
        --out-dir experiments/outputs/jwe_rq1_rq2_evidence/2026-10-13/rq1

Inputs are read from pinned commits only (jwe_pinned_inputs.py): the study selection and all JWE
prediction files from SELECTION_REF (hash-checked against the selection), the frozen ICWE n=40
accuracies from ICWE_REF, and, for a cross-check only, runs.csv of 29_binary_runs_vs_human_reference.py
from RUNS_CSV_REF.

Definitions (ANALYSIS_PLAN.md sections 2, 3, 5 and D5/D6/D10):
* agreement = share of parsable rows at n_examples=40 whose re_eval_score equals human_answer_correct
  (the operational teacher label). The all-rows variant keeps unparsable rows with their stored
  fallback score (how 29_ counted them); both are written.
* overruled items = rows whose deployed-grader score (source_score) differs from the teacher label
  (lecturer overruled the deployed grader); confirmed = the rest. Cross-checked against the pool's
  validation_lecturer.
* reference lines: majority class (always "correct") and the incumbent-agreement reference (reproduce
  the deployed grader's score; named "anchoring ceiling" before D6).
* P1: item-level pairing on (QuestionID, cv_fold, user_id, LF-normalised answer_text); McNemar exact and
  continuity-corrected; 90 % percentile bootstrap of the paired difference with the routine of
  13_significance_testing.py (numpy default_rng(42), 10,000 resamples, rows resampled); plus a cluster
  bootstrap over the 45 (QuestionID, cv_fold) prompt clusters (D7) as an added sensitivity.
* S1 check: base vs guided at n=40, recomputed only to verify the values recorded in ANALYSIS_PLAN.md.

Not computed here (inferential tests the plan prespecifies but no committed output exists for): the S2
McNemar family against Claude Haiku 4.5 (K=6), the S4 Fisher test, and the S6 Fisher tests for the two
new models (K=2). The per-arm inputs they would use (agreement, calibration sign, subset split) are
written as descriptive values.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest, chi2

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jwe_pinned_inputs as jpi  # noqa: E402

N40 = 40
HEADLINE_ROLES = ("original_base", "new_base", "s3_gate", "currency_tier")  # as in 29_ (15 base arms)
RUNS_CSV_REF = "f00b3f8f81d96767980ad3a76cc826b0de3361da"  # feat/jwe-adjudication-ui-20261001 on 2026-10-13
RUNS_CSV = "experiments/outputs/jwe_consensus/2026-10-12_binary_runs_vs_reference/runs.csv"
FROZEN_ICWE = "experiments/outputs/_frozen_icwe_cameraready/significance_mcnemar__n40__parsable_only.meta.json"
KEY = ["QuestionID", "cv_fold", "user_id", "answer_text_lf"]
# Values recorded in ANALYSIS_PLAN.md (D-log) for the S1 check; base minus guided, b = base right/guided wrong.
S1_RECORDED = {
    "Qwen/Qwen3.6-27B": {"b_c": (25, 8), "p_holm": ".0091"},
    "Qwen/Qwen3.8-27B": {"b_c": (27, 4), "p_holm": ".0001"},
    "microsoft/phi-4:16k": {"b_c": (70, 22), "p_holm": "<.0001"},
    "mistralai/Mistral-Small-3.2-24B-Instruct-2506": {"b_c": (41, 35), "p_holm": ".567"},
}


def n40_slice(df: pd.DataFrame) -> pd.DataFrame:
    sl = df[df["n_examples"] == N40].copy()
    if len(sl) != 450:
        raise ValueError(f"n=40 slice has {len(sl)} rows, expected 450")
    sl["overruled"] = (sl["source_score"] != sl["human_answer_correct"]).astype(int)
    sl["correct"] = (sl["re_eval_score"] == sl["human_answer_correct"]).astype(int)
    return sl


def arm_row(src: dict, meta: dict, sl: pd.DataFrame) -> dict:
    pars = sl[sl["parsable"] == 1]
    k, n = int(pars["correct"].sum()), int(len(pars))
    lo, hi = jpi.wilson(k, n)
    fp = int(((pars["re_eval_score"] == 1) & (pars["human_answer_correct"] == 0)).sum())
    fn = int(((pars["re_eval_score"] == 0) & (pars["human_answer_correct"] == 1)).sum())
    conf = pd.to_numeric(pars["confidence"], errors="coerce")
    mean_conf = float(conf.mean())
    agree = k / n
    ov, cf = pars[pars["overruled"] == 1], pars[pars["overruled"] == 0]
    ko, no_, kc, nc = int(ov["correct"].sum()), int(len(ov)), int(cf["correct"].sum()), int(len(cf))
    olo, ohi = jpi.wilson(ko, no_)
    clo, chi_ = jpi.wilson(kc, nc)
    dec = src["decoding"]
    return {
        "model": src["model"], "role": src["role"], "condition_id": src["condition_id"],
        "backend": jpi.backend_of(meta), "temperature_requested": dec.get("temperature"),
        "max_output_tokens": dec.get("max_output_tokens"), "use_response_format": dec.get("use_response_format"),
        "reasoning": json.dumps(dec.get("reasoning"), sort_keys=True) if dec.get("reasoning") is not None else "",
        "system_prompt_sha256": src.get("system_prompt_sha256") or meta.get("system_prompt_sha256") or "",
        "rows_n40": int(len(sl)), "parsable_n40": n, "parse_rate_n40": n / len(sl),
        "agree_k": k, "agreement": agree, "wilson95_low": lo, "wilson95_high": hi,
        "agree_k_all_rows_fallback": int(sl["correct"].sum()), "agreement_all_rows_fallback": float(sl["correct"].mean()),
        "false_pass_rate": fp / n, "false_fail_rate": fn / n, "false_pass": fp, "false_fail": fn,
        "mean_confidence": mean_conf, "calibration_gap_conf_minus_agreement": mean_conf - agree,
        "s4_sign_overconfident": int(mean_conf - agree > 0),
        # Confidence by predicted class. The base prompt asks for a 'confidence' number 0..1 without defining
        # what it refers to; a class-dependent mean (low on predicted-incorrect rows) suggests a different
        # semantics for that arm and leaves its S4 sign unresolved. Descriptive only.
        "mean_confidence_pred0": float(conf[pars["re_eval_score"] == 0].mean()),
        "mean_confidence_pred1": float(conf[pars["re_eval_score"] == 1].mean()),
        "overruled_k": ko, "overruled_n": no_, "agreement_overruled": ko / no_ if no_ else float("nan"),
        "overruled_wilson95_low": olo, "overruled_wilson95_high": ohi,
        "confirmed_k": kc, "confirmed_n": nc, "agreement_confirmed": kc / nc if nc else float("nan"),
        "confirmed_wilson95_low": clo, "confirmed_wilson95_high": chi_,
        "run_id": src["run_id"], "source_id": src["source_id"],
        "predictions_path": src["files"]["predictions"]["path"],
        "predictions_sha256_lf": src["files"]["predictions"]["sha256_lf"],
    }


def mcnemar(a: np.ndarray, b: np.ndarray) -> dict:
    n10 = int(((a == 1) & (b == 0)).sum())
    n01 = int(((a == 0) & (b == 1)).sum())
    d = n10 + n01
    exact = float(binomtest(min(n10, n01), d, 0.5).pvalue) if d else 1.0
    cc = float(1 - chi2.cdf((abs(n10 - n01) - 1) ** 2 / d, df=1)) if d else 1.0
    return {"a_right_b_wrong": n10, "a_wrong_b_right": n01, "discordant": d,
            "mcnemar_exact_p": exact, "mcnemar_cc_p": cc}


def boot_rows(a: np.ndarray, b: np.ndarray, n_boot: int, seed: int, alpha: float) -> list[float]:
    """Identical to 13_significance_testing.bootstrap_accuracy_difference (rows resampled)."""
    rng = np.random.default_rng(seed)
    n = len(a)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        diffs[i] = a[idx].mean() - b[idx].mean()
    return [float(np.percentile(diffs, 100 * alpha / 2)), float(np.percentile(diffs, 100 * (1 - alpha / 2)))]


def boot_clusters(a: np.ndarray, b: np.ndarray, cl: np.ndarray, n_boot: int, seed: int, alpha: float) -> list[float]:
    ids = np.unique(cl)
    sa = np.array([a[cl == c].sum() for c in ids], dtype=float)
    sb = np.array([b[cl == c].sum() for c in ids], dtype=float)
    sz = np.array([(cl == c).sum() for c in ids], dtype=float)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(ids), size=(n_boot, len(ids)))
    diffs = (sa[draws].sum(1) - sb[draws].sum(1)) / sz[draws].sum(1)
    return [float(np.percentile(diffs, 100 * alpha / 2)), float(np.percentile(diffs, 100 * (1 - alpha / 2)))]


def paired(sl_a: pd.DataFrame, sl_b: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    pa, pb = sl_a[sl_a["parsable"] == 1], sl_b[sl_b["parsable"] == 1]
    info = {"rows_a": len(pa), "rows_b": len(pb),
            "dup_rows_on_QuestionID_cv_fold_user_id": int(pa.duplicated(["QuestionID", "cv_fold", "user_id"], keep=False).sum()),
            "surplus_rows_on_QuestionID_cv_fold_user_id": int(pa.duplicated(["QuestionID", "cv_fold", "user_id"]).sum()),
            "dup_rows_on_full_key": int(pa.duplicated(KEY, keep=False).sum())}
    if info["dup_rows_on_full_key"] or pb.duplicated(KEY).any():
        raise ValueError("pairing key not unique")
    m = pa.set_index(KEY)[["correct", "re_eval_score"]].join(
        pb.set_index(KEY)[["correct", "re_eval_score"]], how="inner", lsuffix="_a", rsuffix="_b")
    info["paired_rows"] = len(m)
    info["score_discordant"] = int((m["re_eval_score_a"] != m["re_eval_score_b"]).sum())
    cl = np.array([f"{q}|{f}" for q, f in zip(m.index.get_level_values(0), m.index.get_level_values(1))])
    return m["correct_a"].to_numpy(), m["correct_b"].to_numpy(), cl, info


def p1_block(label: str, src_a: dict, src_b: dict, slices: dict) -> dict:
    a, b, cl, info = paired(slices[src_a["source_id"]], slices[src_b["source_id"]])
    out = {"label": label, "arm_a_onprem": src_a["run_id"], "arm_b_api": src_b["run_id"],
           "temperature": src_a["decoding"]["temperature"], **info,
           "agreement_a": float(a.mean()), "agreement_b": float(b.mean()), "diff_a_minus_b": float(a.mean() - b.mean()),
           **mcnemar(a, b), "n_clusters": int(len(np.unique(cl)))}
    out["boot90_rows_13_convention"] = boot_rows(a, b, 10000, 42, 0.10)
    out["boot90_clusters_sensitivity"] = boot_clusters(a, b, cl, 10000, 42, 0.10)
    out["boot95_rows_13_convention"] = boot_rows(a, b, 10000, 42, 0.05)
    out["margin"] = 0.030
    out["equivalent_rows_ci"] = bool(-0.030 <= out["boot90_rows_13_convention"][0] and out["boot90_rows_13_convention"][1] <= 0.030)
    out["equivalent_cluster_ci"] = bool(-0.030 <= out["boot90_clusters_sensitivity"][0] and out["boot90_clusters_sensitivity"][1] <= 0.030)
    return out


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj, running = [0.0] * m, 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * ps[i]))
        adj[i] = running
    return adj


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args(argv)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    sources = [s for s in jpi.selection_sources() if s["role"] != "diagnostic"]
    rows, slices, by_role = [], {}, {}
    for src in sources:
        meta = jpi.run_meta(src)
        sl = n40_slice(jpi.load_source_predictions(src))
        slices[src["source_id"]] = sl
        by_role.setdefault(src["role"], []).append(src)
        rows.append(arm_row(src, meta, sl))
    arms = pd.DataFrame(rows)
    arms["headline_base_arm"] = arms["role"].isin(HEADLINE_ROLES)

    # Cross-check against 29_'s runs.csv (agreement with the teacher label on its row set).
    runs = pd.read_csv(io.BytesIO(jpi.git_blob(RUNS_CSV_REF, RUNS_CSV)))
    runs = runs.set_index("run_id")
    def xcheck(r):
        key = r["run_id"]
        hits = runs.loc[[key]] if key in runs.index else pd.DataFrame()
        if hits.empty:
            return pd.Series({"runs_csv_acc_teacher": np.nan, "runs_csv_parse_failures": np.nan})
        hit = hits[hits["model"] == r["model"]]
        hit = hit.iloc[0] if not hit.empty else hits.iloc[0]
        return pd.Series({"runs_csv_acc_teacher": hit["acc_teacher"], "runs_csv_parse_failures": hit["parse_failures"]})
    arms = pd.concat([arms, arms.apply(xcheck, axis=1)], axis=1)
    arms["runs_csv_matches_all_rows_fallback_4dp"] = (arms["agreement_all_rows_fallback"].round(4) == arms["runs_csv_acc_teacher"].round(4))
    arms = arms.sort_values(["headline_base_arm", "agreement"], ascending=[False, False])
    arms.to_csv(out / "arms_n40.csv", index=False)

    # Reference lines (identical across arms: same 450 rows, checked here).
    ref_sl = slices[by_role["original_base"][0]["source_id"]]
    sig = ref_sl[["QuestionID", "cv_fold", "user_id", "answer_text_lf", "human_answer_correct", "source_score"]].astype(str)
    sig = sorted(map(tuple, sig.values.tolist()))
    same_rows = all(sorted(map(tuple, s[["QuestionID", "cv_fold", "user_id", "answer_text_lf", "human_answer_correct",
                                         "source_score"]].astype(str).values.tolist())) == sig for s in slices.values())
    pool_src = by_role["original_base"][0]
    pool = pd.read_csv(io.BytesIO(jpi.git_blob(jpi.SELECTION_REF, pool_src["files"]["pool"]["path"])), keep_default_na=False, dtype=str)
    ov = ref_sl[ref_sl["overruled"] == 1]
    ref = {
        "rows": int(len(ref_sl)), "unique_question_answer_texts": int(ref_sl[["QuestionID", "answer_text_lf"]].drop_duplicates().shape[0]),
        "teacher_label_positive": int((ref_sl["human_answer_correct"] == 1).sum()),
        "majority_class_line": float((ref_sl["human_answer_correct"] == 1).mean()),
        "incumbent_agreement_reference_k": int((ref_sl["overruled"] == 0).sum()),
        "incumbent_agreement_reference": float((ref_sl["overruled"] == 0).mean()),
        "overruled_rows": int(len(ov)),
        "pool_validation_lecturer_0_rows": int((pd.to_numeric(pool["validation_lecturer"], errors="coerce") == 0).sum()),
        "deployed_grader_positive": int((ref_sl["source_score"] == 1).sum()),
        "always_negative_on_overruled": float((ov["human_answer_correct"] == 0).mean()),
        "teacher_positive_share_confirmed": float(ref_sl.loc[ref_sl["overruled"] == 0, "human_answer_correct"].mean()),
        "teacher_positive_share_overruled": float(ov["human_answer_correct"].mean()),
        "all_selected_arms_share_identical_n40_rows_and_labels": bool(same_rows),
        "prompt_clusters_n40": int(ref_sl[["QuestionID", "cv_fold"]].drop_duplicates().shape[0]),
    }

    # S3 gate: frozen ICWE n=40 against the harmonised rerun.
    frozen = json.loads(jpi.git_blob(jpi.ICWE_REF, FROZEN_ICWE))["model_accuracies_at_n"]
    s3 = []
    for model_safe, (label, model_id) in jpi.ICWE_MODELS.items():
        gate = arms[(arms["role"] == "s3_gate") & (arms["model"] == model_id)].iloc[0]
        f = float(frozen[model_safe])
        s3.append({"model": model_id, "model_label": label, "frozen_icwe_n40": f, "s3_rerun_n40": gate["agreement"],
                   "delta_pp": 100 * (gate["agreement"] - f), "within_3pp": abs(gate["agreement"] - f) <= 0.030 + 1e-12,
                   "s3_parse_rate": gate["parse_rate_n40"], "s3_run_id": gate["run_id"]})
    rep = arms[arms["role"] == "s3_repeat"].iloc[0]
    g_gate = [s for s in by_role["s3_gate"] if s["model"] == rep["model"]][0]
    g_rep = by_role["s3_repeat"][0]
    _, _, _, ginfo = paired(slices[g_gate["source_id"]], slices[g_rep["source_id"]])
    s3_df = pd.DataFrame(s3)
    s3_df.to_csv(out / "s3_gate.csv", index=False)
    s3_repeat = {"model": rep["model"], "repeat_agreement_n40": rep["agreement"],
                 "delta_pp_vs_frozen": 100 * (rep["agreement"] - float(frozen["google_gemini-2.5-flash-lite"])),
                 "score_discordant_gate_vs_repeat": ginfo["score_discordant"], "run_id": rep["run_id"]}

    # P1, both runs.
    p1_t0 = p1_block("P1 rerun at temperature 0 (after D10)", by_role["p1_onprem_t0"][0], by_role["p1_api_t0"][0], slices)
    onprem_t02 = [s for s in by_role["original_base"] if s["model"].startswith("mistralai/")][0]
    p1_t02 = p1_block("P1 first run at temperature 0.2 (superseded by D10)", onprem_t02, by_role["superseded_p1_t02"][0], slices)

    # S1 check (base vs guided at n=40, original base arms).
    s1 = []
    for model, rec in S1_RECORDED.items():
        base = [s for s in by_role["original_base"] if s["model"] == model][0]
        guided = [s for s in by_role["guided"] if s["model"] == model][0]
        a, b, cl, info = paired(slices[base["source_id"]], slices[guided["source_id"]])
        mc = mcnemar(a, b)
        s1.append({"model": model, "agreement_base": float(a.mean()), "agreement_guided": float(b.mean()),
                   "diff_pp_guided_minus_base": 100 * float(b.mean() - a.mean()),
                   "base_right_guided_wrong": mc["a_right_b_wrong"], "base_wrong_guided_right": mc["a_wrong_b_right"],
                   "recorded_b_c": f"{rec['b_c'][0]}/{rec['b_c'][1]}", "recorded_p_holm": rec["p_holm"],
                   "mcnemar_exact_p": mc["mcnemar_exact_p"], "mcnemar_cc_p": mc["mcnemar_cc_p"], "paired_rows": info["paired_rows"]})
    s1_df = pd.DataFrame(s1)
    s1_df["holm_exact"] = holm(s1_df["mcnemar_exact_p"].tolist())
    s1_df["holm_cc"] = holm(s1_df["mcnemar_cc_p"].tolist())
    s1_df["b_c_matches_recorded"] = [f"{r.base_right_guided_wrong}/{r.base_wrong_guided_right}" == r.recorded_b_c for r in s1_df.itertuples()]
    s1_df.to_csv(out / "s1_check.csv", index=False)

    # Repeat discordance (score differences between two runs of the same model ID on the same 450 rows).
    # D14(a): cells at temperature 0 and 0.2 are never averaged, ranked or differenced across the boundary,
    # so the agreement difference is left empty for pairs that cross it; only the item-level discordance
    # count is written for them, as an internal check that is not for manuscript tables.
    def pair_row(label: str, sa: dict, sb: dict) -> dict:
        a, b, _, info = paired(slices[sa["source_id"]], slices[sb["source_id"]])
        ta, tb = sa["decoding"]["temperature"], sb["decoding"]["temperature"]
        crosses = float(ta) != float(tb)
        return {"comparison": label, "model": sa["model"], "run_a": sa["run_id"], "run_b": sb["run_id"],
                "temperature_a": ta, "temperature_b": tb, "crosses_temperature_boundary_d14": crosses,
                "paired_rows": info["paired_rows"], "score_discordant": info["score_discordant"],
                "agreement_a": float(a.mean()), "agreement_b": float(b.mean()),
                "diff_pp_a_minus_b": float("nan") if crosses else 100 * float(a.mean() - b.mean())}
    rep_rows = []
    for orig in by_role["original_base"]:
        ctrl = [s for s in by_role["reproducibility_control"] if s["model"] == orig["model"]][0]
        rep_rows.append(pair_row("D12 rerun under HEAD vs original base (t0.2)", ctrl, orig))
    for t0 in by_role["exploratory_t0"]:
        ctrl = [s for s in by_role["reproducibility_control"] if s["model"] == t0["model"]][0]
        rep_rows.append(pair_row("t0 run vs t0.2 rerun of 2026-08-19 (crosses D14 boundary, discordance only)", t0, ctrl))
    rep_rows.append(pair_row("t0 run vs its t0 repeat (on-premise)", by_role["exploratory_t0"][[s["model"] for s in by_role["exploratory_t0"]].index("Qwen/Qwen3.8-27B")],
                             by_role["exploratory_t0_repeat"][0]))
    rep_rows.append(pair_row("S3 gate vs S3 repeat (API, t0.2)", g_gate, g_rep))
    pd.DataFrame(rep_rows).to_csv(out / "repeat_discordance.csv", index=False)

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "experiments/scripts/31_jwe_n40_agreement.py",
        "inputs": {"selection_ref": jpi.SELECTION_REF, "selection_path": jpi.SELECTION_PATH,
                   "icwe_ref": jpi.ICWE_REF, "frozen_icwe": FROZEN_ICWE,
                   "runs_csv_ref": RUNS_CSV_REF, "runs_csv": RUNS_CSV},
        "reference_lines": ref, "s3_repeat": s3_repeat, "p1": [p1_t02, p1_t0],
        "not_computed": ["S2 (on-premise vs Claude Haiku 4.5, K=6, Holm)", "S4 Fisher test (sign by arm)",
                         "S6 Fisher tests for Qwen3.5-27B and Qwen3-32B (K=2)", "S1 cluster-robust p values (quoted from ANALYSIS_PLAN.md D7)"],
        "status": "descriptive recomputation; P1/S1 recomputed to verify recorded values; cluster bootstrap for P1 is an added sensitivity",
    }
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    head = arms[arms["headline_base_arm"]]
    print(f"{len(arms)} non-diagnostic arms, {len(head)} headline base arms; same n40 rows: {same_rows}")
    for r in head.itertuples():
        print(f"  {r.model:<46} {r.role:<14} {r.backend:<18} t={r.temperature_requested} parse={r.parse_rate_n40:.4f} "
              f"agree={r.agreement:.4f} ({r.agree_k}/{r.parsable_n40}) overruled={r.agreement_overruled:.3f} confirmed={r.agreement_confirmed:.3f} "
              f"runs.csv={r.runs_csv_acc_teacher}")
    print("reference lines:", json.dumps(ref))
    print("S3:", s3_df[["model", "frozen_icwe_n40", "s3_rerun_n40", "delta_pp", "within_3pp"]].to_string(index=False))
    print("S3 repeat:", s3_repeat)
    for p in (p1_t02, p1_t0):
        print("P1:", {k: p[k] for k in ("label", "paired_rows", "agreement_a", "agreement_b", "diff_a_minus_b",
                                         "a_right_b_wrong", "a_wrong_b_right", "mcnemar_exact_p", "mcnemar_cc_p",
                                         "boot90_rows_13_convention", "boot90_clusters_sensitivity",
                                         "dup_rows_on_QuestionID_cv_fold_user_id", "score_discordant")})
    print("S1:", s1_df.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
