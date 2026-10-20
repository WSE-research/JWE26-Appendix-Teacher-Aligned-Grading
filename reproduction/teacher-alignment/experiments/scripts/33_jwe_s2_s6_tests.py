#!/usr/bin/env python3
"""Prespecified secondary tests S2 and S6 that 31_jwe_n40_agreement.py left uncomputed.

    python experiments/scripts/33_jwe_s2_s6_tests.py \
        --out-dir experiments/outputs/jwe_rq1_rq2_evidence/2026-10-20/s2_s6

Definitions follow ANALYSIS_PLAN.md; the arms, K, the API reference and the test definitions were fixed before
any S2/S6 data existed. Applying D7's cluster-robust convention to S2 was written down on 2026-10-20 (D21), after
the descriptive per-arm agreements had been reported on 2026-10-13; exact McNemar is therefore reported alongside:
* S2 (Section 5, D16): each of the six on-premise base arms at n=40 against the S3-gate run of
  anthropic/claude-haiku-4.5, paired on (QuestionID, cv_fold, user_id, LF-normalised answer_text) as in 31_
  (D9: never positional). Holm-Bonferroni at the declared K = 6 (D3: per sub-family).
* Reported p value (D7): cluster sign-flip permutation over the 45 (QuestionID, cv_fold) prompt clusters,
  two-sided on the summed per-cluster difference, Monte Carlo with numpy default_rng(42). Exact McNemar is
  written alongside, as D7 prescribes for S1. The permutation routine is validated first by reproducing the
  D7-recorded Holm-adjusted S1 values (.0090/.0039/.0012/.6249); the script aborts if it does not.
* S6 (Section 5, D17/D18 narrow reading): Fisher exact test of subset (43 overruled / 407 confirmed) x
  correctness for the two models new to the study, Qwen/Qwen3-32B and Qwen/Qwen3.5-27B, Holm at K = 2.
  Parsable rows only. The always-negative line on the overruled subset (D5) is written beside it.
* Not computed: S4 (calibration sign). Its input, the reported confidence, has no defined event in the
  prompt (article Section 6.4), so the plan's sign test would not have an interpretable target.

Inputs are the pinned prediction files of 31_ (jwe_pinned_inputs.py); outputs are CSV/JSON only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jwe_pinned_inputs as jpi  # noqa: E402

_spec = importlib.util.spec_from_file_location("agreement31", HERE / "31_jwe_n40_agreement.py")
a31 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a31)

API_REFERENCE = "anthropic/claude-haiku-4.5"
K_S2, K_S6 = 6, 2
S6_MODELS = ("Qwen/Qwen3-32B", "Qwen/Qwen3.5-27B")
N_PERM = 200_000
D7_S1_HOLM = {  # ANALYSIS_PLAN.md D7, cluster-robust Holm-adjusted, K = 4
    "Qwen/Qwen3.6-27B": 0.0090, "Qwen/Qwen3.8-27B": 0.0039,
    "microsoft/phi-4:16k": 0.0012, "mistralai/Mistral-Small-3.2-24B-Instruct-2506": 0.6249,
}


def cluster_signflip_p(a: np.ndarray, b: np.ndarray, cl: np.ndarray, n_perm: int = N_PERM, seed: int = 42) -> float:
    ids = np.unique(cl)
    d = np.array([(a[cl == c] - b[cl == c]).sum() for c in ids], dtype=float)
    obs = abs(d.sum())
    rng = np.random.default_rng(seed)
    signs = rng.choice((-1.0, 1.0), size=(n_perm, len(ids)))
    null = np.abs(signs @ d)
    return float((1 + (null >= obs - 1e-12).sum()) / (n_perm + 1))


def validate_on_s1(slices: dict, by_role: dict) -> pd.DataFrame:
    rows = []
    for model in D7_S1_HOLM:
        base = [s for s in by_role["original_base"] if s["model"] == model][0]
        guided = [s for s in by_role["guided"] if s["model"] == model][0]
        a, b, cl, _ = a31.paired(slices[base["source_id"]], slices[guided["source_id"]])
        rows.append({"model": model, "cluster_signflip_p": cluster_signflip_p(a, b, cl), "recorded_holm_d7": D7_S1_HOLM[model]})
    df = pd.DataFrame(rows)
    df["holm_cluster"] = a31.holm(df["cluster_signflip_p"].tolist())
    df["abs_dev"] = (df["holm_cluster"] - df["recorded_holm_d7"]).abs()
    return df


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--s1-tolerance", type=float, default=0.002)
    args = ap.parse_args(argv)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    sources = [s for s in jpi.selection_sources() if s["role"] in ("original_base", "new_base", "guided", "s3_gate")]
    slices, by_role = {}, {}
    for src in sources:
        slices[src["source_id"]] = a31.n40_slice(jpi.load_source_predictions(src))
        by_role.setdefault(src["role"], []).append(src)

    s1 = validate_on_s1(slices, by_role)
    s1.to_csv(out / "s1_routine_validation.csv", index=False)
    if (s1["abs_dev"] > args.s1_tolerance).any():
        print(s1.to_string(index=False))
        raise SystemExit("cluster sign-flip routine does not reproduce D7; S2 not computed")

    ref = [s for s in by_role["s3_gate"] if s["model"] == API_REFERENCE][0]
    onprem = by_role["original_base"] + by_role["new_base"]
    if len(onprem) != K_S2:
        raise ValueError(f"expected {K_S2} on-premise base arms, found {len(onprem)}")
    s2 = []
    for src in onprem:
        a, b, cl, info = a31.paired(slices[src["source_id"]], slices[ref["source_id"]])
        mc = a31.mcnemar(a, b)
        s2.append({"model": src["model"], "role": src["role"], "run_onprem": src["run_id"], "run_api_reference": ref["run_id"],
                   "paired_rows": info["paired_rows"], "n_clusters": int(len(np.unique(cl))),
                   "agreement_onprem": float(a.mean()), "agreement_api_reference": float(b.mean()),
                   "diff_pp_onprem_minus_api": 100 * float(a.mean() - b.mean()),
                   "onprem_right_api_wrong": mc["a_right_b_wrong"], "onprem_wrong_api_right": mc["a_wrong_b_right"],
                   "cluster_signflip_p": cluster_signflip_p(a, b, cl), "mcnemar_exact_p": mc["mcnemar_exact_p"],
                   "boot95_clusters": a31.boot_clusters(a, b, cl, 10000, 42, 0.05)})
    s2 = pd.DataFrame(s2)
    s2["holm_cluster_K6"] = a31.holm(s2["cluster_signflip_p"].tolist())
    s2["holm_exact_K6"] = a31.holm(s2["mcnemar_exact_p"].tolist())
    s2["reject_at_0.05_cluster"] = s2["holm_cluster_K6"] < 0.05
    s2.to_csv(out / "s2_onprem_vs_claude_haiku.csv", index=False)

    s6 = []
    for model in S6_MODELS:
        src = [s for s in by_role["new_base"] if s["model"] == model][0]
        sl = slices[src["source_id"]]
        pars = sl[sl["parsable"] == 1]
        ov, cf = pars[pars["overruled"] == 1], pars[pars["overruled"] == 0]
        table = [[int(ov["correct"].sum()), int(len(ov) - ov["correct"].sum())],
                 [int(cf["correct"].sum()), int(len(cf) - cf["correct"].sum())]]
        odds, p = fisher_exact(table)
        lo_o, hi_o = jpi.wilson(table[0][0], len(ov))
        lo_c, hi_c = jpi.wilson(table[1][0], len(cf))
        s6.append({"model": model, "run_id": src["run_id"], "overruled_n": len(ov), "confirmed_n": len(cf),
                   "agreement_overruled": table[0][0] / len(ov), "wilson95_overruled": [lo_o, hi_o],
                   "agreement_confirmed": table[1][0] / len(cf), "wilson95_confirmed": [lo_c, hi_c],
                   "always_negative_line_overruled": float((ov["human_answer_correct"] == 0).mean()),
                   "fisher_table_[[ov_right,ov_wrong],[cf_right,cf_wrong]]": table, "odds_ratio": float(odds), "fisher_p": float(p)})
    s6 = pd.DataFrame(s6)
    s6["holm_K2"] = a31.holm(s6["fisher_p"].tolist())
    s6.to_csv(out / "s6_new_models_fisher.csv", index=False)

    meta = {"script": "experiments/scripts/33_jwe_s2_s6_tests.py", "computed_utc": datetime.now(timezone.utc).isoformat(),
            "selection_ref": jpi.SELECTION_REF, "n_perm": N_PERM, "seed": 42,
            "status": "prespecified secondary tests, computed late on 2026-10-20 after the descriptive per-arm values had been "
                      "reported (2026-10-13); arms, K and test definitions fixed before any S2/S6 data existed; applying the D7 "
                      "cluster-robust convention to S2 recorded on 2026-10-20 (D21), exact McNemar reported alongside",
            "s1_routine_validation_max_abs_dev": float(s1["abs_dev"].max()),
            "not_computed": ["S4 calibration sign: confidence has no defined event in the prompt"]}
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    pd.set_option("display.width", 250)
    print(s1.to_string(index=False)); print(); print(s2.drop(columns=["run_onprem", "run_api_reference"]).to_string(index=False)); print(); print(s6.drop(columns=["run_id"]).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
