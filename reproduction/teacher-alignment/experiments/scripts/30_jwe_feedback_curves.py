#!/usr/bin/env python3
"""RQ2 (teacher feedback volume): per-n agreement with the teacher label and threshold attainment.

    python experiments/scripts/30_jwe_feedback_curves.py \
        --out-dir experiments/outputs/jwe_rq1_rq2_evidence/2026-10-13/rq2

What it computes, in this order (the order is the guard):

1. **ICWE reproduction gate.** For the five ICWE models, from the frozen consolidated predictions of
   2026-02-18 (commit ICWE_REF), the per-n agreement on parsable rows and the smallest n in
   {0,1,3,5,10,15,20,25,30,35,40} whose agreement is >= 85 %, 88 % and 90 %. This is exactly the
   ICWE computation (08_plot_accuracy_overlay_full_runs.py --parsable-only, then
   12_generate_paper_metrics_snapshot.compute_table3_thresholds). The values must equal the
   published ICWE Table 3 and the n=0 / n=40 columns of ICWE Table 1; otherwise the script stops
   with exit code 2 and writes nothing about new models.
2. **Pool identity.** The JWE runs must use the same 450 pool rows, teacher labels and n=40 fold
   assignment as the ICWE run, otherwise their curves are not comparable. Checked for the 15 curve
   arms below (`pool_and_fold_identity.csv`) and, separately, for every non-diagnostic source of the
   pinned selection (`pool_and_fold_identity_all_selected.csv`, 51 arms).
3. **JWE full-grid base runs.** Every source of the pinned study selection (commit SELECTION_REF)
   whose example counts are the full eleven-point grid and whose prompt is the base prompt:
   the four original on-premise base arms (S1 basis), their four reproducibility controls (D12),
   the on-premise and API arms of P1 at temperature 0 and the superseded API arm at 0.2 (D10).
   Same per-n agreement and attainment rule, plus an added descriptive column "first n from which
   all larger n stay >= target" to expose transient attainment (ICWE Table 3, footnote on GLM).
4. **Partial-grid runs** (currency tier, n in {0,5,20,40}): per-n agreement only, with the crossing
   on the four-point grid in a separate file; not comparable with the eleven-point attainment.

Status: exploratory (ANALYSIS_PLAN.md section 6 lists all 11 n values and the learning curves as
exploratory). Operating points are never pooled: temperature is a column of every table (D14).
Agreement is with the operational teacher label (`human_answer_correct`, ANALYSIS_PLAN.md section 2).
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jwe_pinned_inputs as jpi  # noqa: E402

TARGETS = (0.85, 0.88, 0.90)
# Published ICWE values (camera-ready, Table 3 and Table 1); None = "-" (not reached by n=40).
ICWE_TABLE3 = {
    "anthropic_claude-haiku-4.5": (0, 3, 10),
    "deepseek_deepseek-v3.2": (10, 15, 30),
    "qwen_qwen3.5-397b-a17b": (5, 10, None),
    "google_gemini-2.5-flash-lite": (25, None, None),
    "z-ai_glm-4.7-flash": (10, None, None),
}
ICWE_TABLE1_N0_N40_PCT = {
    "anthropic_claude-haiku-4.5": (87.11, 90.67),
    "deepseek_deepseek-v3.2": (72.89, 90.00),
    "qwen_qwen3.5-397b-a17b": (81.11, 89.33),
    "google_gemini-2.5-flash-lite": (67.56, 86.00),
    "z-ai_glm-4.7-flash": (80.22, 81.78),
}
SNAPSHOT = ("experiments/outputs/incremental_in_context_eval_consolidated/analysis/paper_repro_snapshot/"
            "paper_table3_feedback_thresholds.csv")
FULL_GRID_ROLES = ("original_base", "reproducibility_control", "p1_onprem_t0", "p1_api_t0", "superseded_p1_t02")
PARTIAL_GRID_ROLES = ("currency_tier",)
ROLE_NOTE = {
    "original_base": "S1 basis, original on-premise base arm (D12: prompt hash not recorded)",
    "reproducibility_control": "D12 rerun of the original base arm under HEAD, a check, not a replacement",
    "p1_onprem_t0": "P1 on-premise arm, temperature 0 (D10)",
    "p1_api_t0": "P1 API arm, temperature 0 (D10)",
    "superseded_p1_t02": "first P1 API arm at temperature 0.2, P1 claim superseded (D10); S4 API arm",
    "currency_tier": "currency tier, four n values (D19/D19b)",
}


def thresholds_row(curve: pd.DataFrame) -> dict:
    out = {}
    for t in TARGETS:
        pct = int(round(t * 100))
        out[f"n_first_ge_{pct}"] = jpi.first_n_reaching(curve, t)
        out[f"n_stays_ge_{pct}"] = jpi.first_n_staying(curve, t)
    return out


def fmt_n(v) -> str:
    return "-" if v is None or (isinstance(v, float) and pd.isna(v)) else str(int(v))


def icwe_gate(out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    per_n, thr, problems = [], [], []
    snap = pd.read_csv(io.BytesIO(jpi.git_blob(jpi.ICWE_REF, SNAPSHOT)))
    for model_safe, (label, model_id) in jpi.ICWE_MODELS.items():
        df = jpi.load_icwe_predictions(model_safe)
        curve = jpi.per_n_agreement(df)
        if tuple(curve["n_examples"]) != jpi.FULL_GRID:
            problems.append(f"{model_safe}: grid {tuple(curve['n_examples'])}")
        curve.insert(0, "model", model_id)
        curve.insert(1, "model_label", label)
        per_n.append(curve)
        row = {"model": model_id, "model_label": label, **thresholds_row(curve)}
        pub = ICWE_TABLE3[model_safe]
        row.update({"published_n_ge_85": pub[0], "published_n_ge_88": pub[1], "published_n_ge_90": pub[2]})
        got = (row["n_first_ge_85"], row["n_first_ge_88"], row["n_first_ge_90"])
        row["matches_published_table3"] = got == pub
        if got != pub:
            problems.append(f"{model_safe}: thresholds {got} != published {pub}")
        s = snap[snap["model_safe"] == model_safe].iloc[0]
        snap_vals = tuple(None if pd.isna(s[c]) else int(s[c]) for c in ("n_for_ge_85", "n_for_ge_88", "n_for_ge_90"))
        row["matches_repro_snapshot"] = got == snap_vals
        if got != snap_vals:
            problems.append(f"{model_safe}: thresholds {got} != repro snapshot {snap_vals}")
        a0 = round(100 * float(curve.loc[curve["n_examples"] == 0, "agreement"].iloc[0]), 2)
        a40 = round(100 * float(curve.loc[curve["n_examples"] == 40, "agreement"].iloc[0]), 2)
        row.update({"agreement_n0_pct": a0, "agreement_n40_pct": a40,
                    "published_n0_pct": ICWE_TABLE1_N0_N40_PCT[model_safe][0],
                    "published_n40_pct": ICWE_TABLE1_N0_N40_PCT[model_safe][1]})
        row["matches_published_table1_n0_n40"] = (a0, a40) == ICWE_TABLE1_N0_N40_PCT[model_safe]
        if not row["matches_published_table1_n0_n40"]:
            problems.append(f"{model_safe}: n0/n40 {a0}/{a40} != published {ICWE_TABLE1_N0_N40_PCT[model_safe]}")
        thr.append(row)
    return pd.concat(per_n, ignore_index=True), pd.DataFrame(thr), problems


def pool_signature(pool_bytes: bytes) -> set:
    pool = pd.read_csv(io.BytesIO(pool_bytes), keep_default_na=False, dtype=str)
    pool["answer_text_lf"] = pool["answer_text"].str.replace("\r\n", "\n", regex=False)
    cols = ["QuestionID", "user_id", "answer_text_lf", "human_answer_correct", "score", "validation_lecturer"]
    sig = pool[cols].apply(tuple, axis=1).value_counts()
    return set(sig.items())


def fold_signature(df: pd.DataFrame) -> set:
    n40 = df[df["n_examples"] == 40]
    cols = ["QuestionID", "cv_fold", "user_id", "answer_text_lf", "human_answer_correct"]
    sig = n40[cols].astype(str).apply(tuple, axis=1).value_counts()
    return set(sig.items())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args(argv)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    icwe_per_n, icwe_thr, problems = icwe_gate(out)
    icwe_per_n.to_csv(out / "icwe_per_n.csv", index=False)
    icwe_thr.to_csv(out / "icwe_thresholds_vs_published.csv", index=False)
    if problems:
        (out / "STOPPED_icwe_not_reproduced.txt").write_text("\n".join(problems) + "\n", encoding="utf-8")
        print("ICWE reproduction FAILED; no new-model numbers written:\n  " + "\n  ".join(problems))
        return 2
    print("ICWE Table 3 and Table 1 n=0/n=40 reproduced exactly for all five models.")

    icwe_pool = pool_signature(jpi.git_blob(jpi.ICWE_REF, f"{jpi.ICWE_RUN}/01_inputs/in_context_pool.csv"))
    icwe_folds = fold_signature(jpi.load_icwe_predictions("anthropic_claude-haiku-4.5"))

    per_n_rows, thr_rows, identity = [], [], []
    partial_rows, partial_thr = [], []
    for src in jpi.selection_sources(FULL_GRID_ROLES + PARTIAL_GRID_ROLES):
        meta = jpi.run_meta(src)
        df = jpi.load_source_predictions(src)
        curve = jpi.per_n_agreement(df)
        grid = tuple(curve["n_examples"])
        pool_same = pool_signature(jpi.git_blob(jpi.SELECTION_REF, src["files"]["pool"]["path"])) == icwe_pool
        folds_same = fold_signature(df) == icwe_folds
        identity.append({"run_id": src["run_id"], "model": src["model"], "role": src["role"],
                         "pool_identical_to_icwe": pool_same, "n40_fold_assignment_identical_to_icwe": folds_same})
        dec = src["decoding"]
        info = {
            "model": src["model"], "role": src["role"], "role_note": ROLE_NOTE[src["role"]],
            "backend": jpi.backend_of(meta), "temperature_requested": dec.get("temperature"),
            "max_output_tokens": dec.get("max_output_tokens"), "use_response_format": dec.get("use_response_format"),
            "system_prompt_sha256": src.get("system_prompt_sha256") or meta.get("system_prompt_sha256"),
            "run_id": src["run_id"], "predictions_path": src["files"]["predictions"]["path"],
            "predictions_sha256_lf": src["files"]["predictions"]["sha256_lf"],
        }
        if src["role"] in FULL_GRID_ROLES:
            if grid != jpi.FULL_GRID:
                raise ValueError(f"{src['source_id']}: expected the full grid, found {grid}")
            per_n_rows.append(curve.assign(**{k: info[k] for k in ("model", "role", "backend", "temperature_requested", "run_id")}))
            thr_rows.append({**info, **thresholds_row(curve),
                             "agreement_n0": float(curve.loc[curve["n_examples"] == 0, "agreement"].iloc[0]),
                             "agreement_n40": float(curve.loc[curve["n_examples"] == 40, "agreement"].iloc[0]),
                             "min_parse_rate": float(curve["parse_rate"].min())})
        else:
            partial_rows.append(curve.assign(**{k: info[k] for k in ("model", "role", "backend", "temperature_requested", "run_id")}))
            partial_thr.append({**{k: info[k] for k in ("model", "role", "backend", "temperature_requested", "run_id")},
                                "grid": "0,5,20,40",
                                **{f"n_first_ge_{int(round(t*100))}_on_4pt_grid": jpi.first_n_reaching(curve, t) for t in TARGETS},
                                "min_parse_rate": float(curve["parse_rate"].min())})

    lead = ["model", "role", "backend", "temperature_requested", "run_id"]
    per_n = pd.concat(per_n_rows, ignore_index=True)
    per_n = per_n[lead + [c for c in per_n.columns if c not in lead]]
    per_n.to_csv(out / "jwe_full_grid_per_n.csv", index=False)
    thr = pd.DataFrame(thr_rows)
    thr.to_csv(out / "jwe_full_grid_thresholds.csv", index=False)
    part = pd.concat(partial_rows, ignore_index=True)
    part = part[lead + [c for c in part.columns if c not in lead]]
    part.to_csv(out / "jwe_partial_grid_per_n.csv", index=False)
    pd.DataFrame(partial_thr).to_csv(out / "jwe_partial_grid_4pt_crossings.csv", index=False)
    pd.DataFrame(identity).to_csv(out / "pool_and_fold_identity.csv", index=False)

    # Same identity check for every non-diagnostic source of the pinned selection (not only the curve arms).
    identity_all = []
    for src in jpi.selection_sources():
        if src["role"] == "diagnostic":
            continue
        df = jpi.load_source_predictions(src)
        identity_all.append({
            "source_id": src["source_id"], "run_id": src["run_id"], "model": src["model"], "role": src["role"],
            "pool_identical_to_icwe": pool_signature(jpi.git_blob(jpi.SELECTION_REF, src["files"]["pool"]["path"])) == icwe_pool,
            "n40_fold_assignment_identical_to_icwe": fold_signature(df) == icwe_folds,
        })
    pd.DataFrame(identity_all).to_csv(out / "pool_and_fold_identity_all_selected.csv", index=False)

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "experiments/scripts/30_jwe_feedback_curves.py",
        "inputs": {"icwe_ref": jpi.ICWE_REF, "icwe_run": jpi.ICWE_RUN, "selection_ref": jpi.SELECTION_REF,
                   "selection_path": jpi.SELECTION_PATH,
                   "selection_blob": jpi.git_blob_id(jpi.SELECTION_REF, jpi.SELECTION_PATH)},
        "rule": "agreement = share of parsable rows with re_eval_score == human_answer_correct per n; "
                "n_first_ge_X = smallest grid n with agreement >= X (ICWE Table 3 rule); "
                "n_stays_ge_X = smallest grid n from which all larger grid n stay >= X (added, descriptive)",
        "icwe_gate": "PASS: Table 3 (85/88/90) and Table 1 n=0/n=40 reproduced exactly for all five models",
        "status": "exploratory (ANALYSIS_PLAN.md section 6); temperature strata never pooled (D14)",
        "full_grid_runs": len(thr_rows), "partial_grid_runs": len(partial_thr),
        "all_pools_identical_to_icwe": all(r["pool_identical_to_icwe"] for r in identity),
        "all_n40_folds_identical_to_icwe": all(r["n40_fold_assignment_identical_to_icwe"] for r in identity),
        "identity_scope": "pool_and_fold_identity.csv: the 15 curve arms (full grid + currency tier); "
                          "pool_and_fold_identity_all_selected.csv: every non-diagnostic selected source",
        "all_selected_sources_checked": len(identity_all),
        "all_selected_pools_identical_to_icwe": all(r["pool_identical_to_icwe"] for r in identity_all),
        "all_selected_n40_folds_identical_to_icwe": all(r["n40_fold_assignment_identical_to_icwe"] for r in identity_all),
    }
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("\nFull-grid base runs (agreement with the teacher label, parsable rows):")
    for r in thr_rows:
        print(f"  {r['model']:<46} {r['role']:<24} t={r['temperature_requested']:<4} "
              f"85%:{fmt_n(r['n_first_ge_85']):>3} 88%:{fmt_n(r['n_first_ge_88']):>3} 90%:{fmt_n(r['n_first_ge_90']):>3}  "
              f"stays85:{fmt_n(r['n_stays_ge_85']):>3} stays90:{fmt_n(r['n_stays_ge_90']):>3}  "
              f"n0 {r['agreement_n0']:.4f} n40 {r['agreement_n40']:.4f}")
    print(f"\npool identical to ICWE: {report['all_pools_identical_to_icwe']}; "
          f"n40 folds identical: {report['all_n40_folds_identical_to_icwe']}")
    print(f"all {report['all_selected_sources_checked']} selected sources: pool identical "
          f"{report['all_selected_pools_identical_to_icwe']}; n40 folds identical "
          f"{report['all_selected_n40_folds_identical_to_icwe']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
