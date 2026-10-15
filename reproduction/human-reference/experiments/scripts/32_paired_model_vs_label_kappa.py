#!/usr/bin/env python3
"""Exploratory, post hoc: paired comparison of each binary JWE run with the historical teacher label (RQ3).

    python experiments/scripts/32_paired_model_vs_label_kappa.py \
        --reference experiments/outputs/jwe_consensus/2026-10-12_e5_adjacent_residual/partial_credit_reference_adjacent_residual.csv \
        --baseline experiments/outputs/jwe_consensus/2026-10-12_binary_runs_vs_reference/report.json \
        --out-dir experiments/outputs/jwe_consensus/2026-10-14_paired_model_vs_label

29_ reports, separately, kappa(run, reference) for every binary run and kappa(teacher label, reference) for the
historical binary label (`human_answer_correct`), each with its own interval. This script asks whether a run's
agreement with the binarised independent human reference differs from the label's agreement with the same
reference on the same 450 rows:

    Delta_m = kappa(run m, reference) - kappa(teacher label, reference)

Both kappas are computed exactly as in 29_ (functions imported from it, unchanged): binary reference per item,
residual adjacent disagreements that straddle the threshold enter with weight 1/2 for each class, weighted
2x2 matrices, Cohen's kappa. Threshold 3 (correct from raw level 3) is primary, threshold 4 the sensitivity.

Paired percentile bootstrap: the unit is the unique (QuestionID, answer_text_sha256) text; all rows of a text
move together, and one resample is applied to the run and to the label at once (one draw matrix shared by
all arms and both thresholds), 10,000 resamples, seed 42, 95 % percentile interval of Delta. Reported per arm:
kappa_run, kappa_label, Delta, its interval, whether the interval excludes 0, the share of resamples with
Delta > 0. Supplementary and labelled as such: two-sided bootstrap p-values
p = min(1, 2 * min((#{Delta* <= 0} + 1) / (B + 1), (#{Delta* >= 0} + 1) / (B + 1))) with Holm adjustment
within each family (15 base arms per threshold; 51 arms per threshold). No equivalence margin; an interval
that includes 0 is not evidence of equivalence.

Reproduction gate (runs first; nothing is written if it fails, exit code 2): every point kappa of the 51
non-diagnostic runs at thresholds 3 and 4, every interval that 29_ stored for them, and the teacher label
against the reference (0.685 [0.619, 0.744] at threshold 3) are recomputed and compared with the 29_
report; the paired machinery (per-text matrices + shared draws) must return 29_'s intervals at 2,000
resamples, seed 42.

Sensitivity (also supplementary): three runs store rows that failed (request error, unparsable output) with a
fallback score 0, which 29_ counts as predictions (`parse_failures` 0). For those runs Delta is recomputed on
the rows without a stored failure, for the run and the label alike.

Claude advisory notes from the adjudication are not used (author decision 2026-10-12): no --protocol input.
Exploratory under ANALYSIS_PLAN.md section 6; no confirmatory claim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("binref29", HERE / "29_binary_runs_vs_human_reference.py")
m29 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m29)
from jwe_run_manifest import portable_text_sha256  # noqa: E402

THRESHOLDS = (3, 4)
PRIMARY_THRESHOLD = 3
N_ITEMS = 439
N_ROWS = 450
BOOT = {"resamples": 10000, "seed": 42, "unit": "unique (QuestionID, answer_text_sha256); rows of a text move together",
        "pairing": "one draw matrix shared by every run, the teacher label and both thresholds", "interval": "percentile 95%"}
BASELINE_BOOT = (2000, 42)   # 29_'s bootstrap, used only by the reproduction gate
PUBLISHED_LABEL_T3 = (0.685, 0.619, 0.744)   # results-ledger, 2026-10-12, rounded to three decimals
TOL = 1e-12


# --------------------------------------------------------------------------------------------- statistics
def item_matrices(keys: list, pred: list[int], ref: dict, items: list) -> np.ndarray:
    """(n_items, 2, 2) weighted reference-by-prediction counts per text, rows of a text summed (as in 29_.block)."""
    pos = {k: i for i, k in enumerate(items)}
    M = np.zeros((len(items), 2, 2))
    for k, p in zip(keys, pred):
        for h, w in ref[k]:
            M[pos[k], h, p] += w
    return M


def resample_counts(n_items: int, n_boot: int, seed: int) -> np.ndarray:
    """(n_boot, n_items) multiplicities; identical draws to 29_.block for the same n_items, n_boot and seed."""
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, n_items, size=(n_boot, n_items))
    return np.stack([np.bincount(d, minlength=n_items) for d in draws]).astype(float)


def boot_kappas(M: np.ndarray, counts: np.ndarray) -> np.ndarray:
    return m29.kappa_from_matrix(np.tensordot(counts, M, axes=(1, 0)))


def two_sided_p(d: np.ndarray) -> float:
    B = len(d)
    return float(min(1.0, 2 * min((int((d <= 0).sum()) + 1) / (B + 1), (int((d >= 0).sum()) + 1) / (B + 1))))


def paired_delta(M_run: np.ndarray, M_label: np.ndarray, counts: np.ndarray) -> dict:
    """Delta = kappa(run) - kappa(label) with a paired percentile bootstrap over the rows of `counts`."""
    k_run = float(m29.kappa_from_matrix(M_run.sum(axis=0)))
    k_lab = float(m29.kappa_from_matrix(M_label.sum(axis=0)))
    br, bl = boot_kappas(M_run, counts), boot_kappas(M_label, counts)
    ok = ~(np.isnan(br) | np.isnan(bl))
    d = br[ok] - bl[ok]
    lo, hi = float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))
    const = br[ok].std() == 0 or bl[ok].std() == 0
    corr = None if const else float(np.corrcoef(br[ok], bl[ok])[0, 1])
    return {"kappa_run": k_run, "kappa_label": k_lab, "delta": k_run - k_lab, "delta_ci": [lo, hi],
            "ci_excludes_zero": bool(lo > 0 or hi < 0), "share_delta_gt_0": float((d > 0).mean()),
            "p_boot_two_sided": two_sided_p(d), "valid_resamples": int(ok.sum()),
            "corr_run_label_resamples": corr}


def holm(p: list[float]) -> list[float]:
    p = np.asarray(p, dtype=float)
    m, out, running = len(p), np.empty(len(p)), 0.0
    for rank, i in enumerate(np.argsort(p, kind="stable")):
        running = max(running, min(1.0, (m - rank) * p[i]))
        out[i] = running
    return out.tolist()


# --------------------------------------------------------------------------------------------- inputs
def load_runs(ref: dict) -> tuple[list, dict, list]:
    """Every non-diagnostic run of the pinned selection at n=40, joined as in 29_; teacher label checked."""
    selection = json.loads(m29.SELECTION.read_text(encoding="utf-8"))
    sources = [s for s in selection["sources"] if s["role"] != "diagnostic"]
    lf = m29.lf_index(m29.POOL)
    pool_keys = set(ref)
    runs, teacher_by_key, keys0 = [], None, None
    for s in sources:
        sl = m29.load_slice(s, pool_keys, lf)
        teach = {k: int(v) for k, v in zip(sl["key"], sl["teacher"]) if not pd.isna(v)}
        if len(teach) != N_ITEMS:
            raise SystemExit(f"{s['source_id']}: teacher label missing for some items")
        if teacher_by_key is None:
            teacher_by_key, keys0 = teach, list(sl["key"])
        elif teach != teacher_by_key:
            raise SystemExit(f"{s['source_id']}: teacher labels differ from the first run")
        if list(sl["key"]) != keys0:
            raise SystemExit(f"{s['source_id']}: row order differs from the first run")
        # 29_ keeps one label per text; duplicated texts must not carry different labels
        if any(int(v) != teacher_by_key[k] for k, v in zip(sl["key"], sl["teacher"])):
            raise SystemExit(f"{s['source_id']}: duplicated texts carry different teacher labels")
        ok = sl.dropna(subset=["pred"])
        fail = (ok["failure_reason"] != "").tolist() if "failure_reason" in ok.columns else [False] * len(ok)
        runs.append({"source": s, "keys": list(ok["key"]), "pred": [int(x) for x in ok["pred"]],
                     "parse_failures": int(sl["pred"].isna().sum()), "stored_failure": fail,
                     "failure_reasons": sorted(set(ok.loc[ok["failure_reason"] != "", "failure_reason"]))
                     if "failure_reason" in ok.columns else []})
    return runs, teacher_by_key, keys0


# --------------------------------------------------------------------------------------------- gate
def reproduction_gate(runs, teacher_by_key, keys0, refs, baseline, reference_path) -> dict:
    """Recompute 29_'s stored values; returns a record with `passed`."""
    fails, max_point, max_ci, n_point, n_ci = [], 0.0, 0.0, 0, 0
    if baseline["reference_sha256"] != hashlib.sha256(reference_path.read_bytes()).hexdigest():
        fails.append("reference CSV differs from the one 29_ read")
    if baseline["selection_sha256_lf"] != portable_text_sha256(m29.SELECTION):
        fails.append("run selection differs from the one 29_ read")
    base_runs = {e["source_id"]: e for e in baseline["runs"]}
    if set(base_runs) != {r["source"]["source_id"] for r in runs}:
        fails.append("set of runs differs from the 29_ report")
    for r in runs:
        b = base_runs.get(r["source"]["source_id"])
        if b is None:
            continue
        s = r["source"]
        if (b["run_id"], b["model"], b["role"]) != (s["run_id"], s["model"], s["role"]):
            fails.append(f"{s['source_id']}: run identity differs")
        if b["parse_failures"] != r["parse_failures"]:
            fails.append(f"{s['source_id']}: parse failures {r['parse_failures']} vs {b['parse_failures']}")
        for T in THRESHOLDS:
            stored = b[f"reference_t{T}"]
            nb = BASELINE_BOOT[0] if stored["kappa_ci"] is not None else 0
            got = m29.block(r["keys"], r["pred"], refs[T], nb, BASELINE_BOOT[1])
            dk = abs(got["kappa"] - stored["kappa"]); max_point = max(max_point, dk); n_point += 1
            if dk > TOL:
                fails.append(f"{s['model']} {s['role']} T{T}: kappa {got['kappa']:.6f} vs {stored['kappa']:.6f}")
            if nb:
                dc = max(abs(a - c) for a, c in zip(got["kappa_ci"], stored["kappa_ci"])); max_ci = max(max_ci, dc); n_ci += 1
                if dc > TOL:
                    fails.append(f"{s['model']} {s['role']} T{T}: kappa CI differs by {dc:.2e}")
    label = {}
    teacher_rows = [teacher_by_key[k] for k in keys0]
    items = sorted(set(keys0))
    counts_2000 = resample_counts(len(items), *BASELINE_BOOT)
    for T in THRESHOLDS:
        stored = baseline["humans"][f"t{T}"]["teacher_vs_reference"]
        got = m29.block(keys0, teacher_rows, refs[T], *BASELINE_BOOT)
        dk = abs(got["kappa"] - stored["kappa"]); dc = max(abs(a - c) for a, c in zip(got["kappa_ci"], stored["kappa_ci"]))
        if dk > TOL or dc > TOL:
            fails.append(f"teacher label T{T}: {got['kappa']:.6f} {got['kappa_ci']} vs {stored['kappa']:.6f} {stored['kappa_ci']}")
        # paired machinery: per-text matrices + shared draws must give 29_'s marginal interval
        M = item_matrices(keys0, teacher_rows, refs[T], items)
        k = boot_kappas(M, counts_2000); k = k[~np.isnan(k)]
        mach = [float(np.percentile(k, 2.5)), float(np.percentile(k, 97.5))]
        dm = max(abs(a - c) for a, c in zip(mach, stored["kappa_ci"]))
        if dm > TOL or abs(float(m29.kappa_from_matrix(M.sum(axis=0))) - stored["kappa"]) > TOL:
            fails.append(f"paired machinery T{T}: marginal CI {mach} vs {stored['kappa_ci']}")
        label[f"t{T}"] = {"kappa": got["kappa"], "kappa_ci_2000": got["kappa_ci"], "stored_kappa": stored["kappa"],
                          "stored_kappa_ci": stored["kappa_ci"], "machinery_ci_2000": mach}
    lt3 = label["t3"]
    rounded = (round(lt3["kappa"], 3), round(lt3["kappa_ci_2000"][0], 3), round(lt3["kappa_ci_2000"][1], 3))
    if rounded != PUBLISHED_LABEL_T3:
        fails.append(f"teacher label T3 rounds to {rounded}, published {PUBLISHED_LABEL_T3}")
    return {"passed": not fails, "failures": fails, "tolerance": TOL,
            "run_point_kappas_checked": n_point, "run_kappa_cis_checked": n_ci,
            "max_abs_diff_point": max_point, "max_abs_diff_ci": max_ci,
            "teacher_label": label, "teacher_label_t3_rounded": list(rounded), "published_teacher_label_t3": list(PUBLISHED_LABEL_T3)}


# --------------------------------------------------------------------------------------------- outputs
CSV_COLS = ["threshold", "model", "role", "condition_id", "temperature", "headline", "kappa_run", "kappa_label", "delta",
            "delta_ci_low", "delta_ci_high", "ci_excludes_zero", "share_delta_gt_0", "p_boot_two_sided", "p_holm",
            "holm_family_size", "stored_failure_rows", "n_rows", "n_items", "source_id", "run_id"]


def csv_row(e: dict, T: int, family: str) -> list:
    d = e[f"t{T}"]
    return [T, e["model"], e["role"], e["condition_id"], e["temperature"], e["headline"], f"{d['kappa_run']:.4f}",
            f"{d['kappa_label']:.4f}", f"{d['delta']:+.4f}", f"{d['delta_ci'][0]:+.4f}", f"{d['delta_ci'][1]:+.4f}",
            d["ci_excludes_zero"], f"{d['share_delta_gt_0']:.4f}", f"{d['p_boot_two_sided']:.4f}",
            f"{d[f'p_holm_{family}']:.4f}", d[f"holm_family_size_{family}"], e["stored_failure_rows"], e["n_rows"], e["n_items"],
            e["source_id"], e["run_id"]]


def write_csv(path: Path, entries: list, family: str) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLS)
        for T in THRESHOLDS:
            for e in sorted(entries, key=lambda e: (not e["headline"], -e[f"t{T}"]["delta"])):
                w.writerow(csv_row(e, T, family))


def readme(payload: dict, cmd: str) -> str:
    g = payload["reproduction"]
    base = [e for e in payload["arms"] if e["headline"]]
    lines = ["# Paired comparison: binary runs vs the historical teacher label at the human reference (2026-10-14)", "",
             "Exploratory, post hoc (ANALYSIS_PLAN.md section 6). For each binary run at n=40 (450 rows, 439 unique texts):",
             "`Delta = kappa(run, reference) - kappa(teacher label, reference)`, the reference being the E5 human reference",
             "binarised at threshold 3 (correct from raw level 3, primary) or 4 (sensitivity). Kappas exactly as in",
             "`29_binary_runs_vs_human_reference.py` (functions imported from it). Paired percentile bootstrap over unique",
             "texts (all rows of a text move together), one draw matrix shared by every run and the label, 10,000",
             "resamples, seed 42. No equivalence margin: an interval containing 0 means the data cannot tell the two",
             "apart, not that they are equivalent. Claude advisory notes are not used.", "",
             "## Command", "", "```bash", cmd, "python experiments/scripts/test_paired_model_vs_label_kappa.py", "```", "",
             "## Reproduction gate (passed before any Delta was computed)", "",
             f"* {g['run_point_kappas_checked']} point kappas (51 runs x thresholds 3 and 4) and {g['run_kappa_cis_checked']} stored",
             f"  intervals recomputed against the 29_ report; max abs difference {g['max_abs_diff_point']:.1e} (points),",
             f"  {g['max_abs_diff_ci']:.1e} (intervals).",
             f"* Teacher label vs reference, threshold 3: {g['teacher_label']['t3']['kappa']:.4f} "
             f"[{g['teacher_label']['t3']['kappa_ci_2000'][0]:.4f}, {g['teacher_label']['t3']['kappa_ci_2000'][1]:.4f}]"
             f" (2,000 resamples, seed 42), rounds to {tuple(g['teacher_label_t3_rounded'])}, published {tuple(g['published_teacher_label_t3'])};",
             f"  threshold 4: {g['teacher_label']['t4']['kappa']:.4f} [{g['teacher_label']['t4']['kappa_ci_2000'][0]:.4f},"
             f" {g['teacher_label']['t4']['kappa_ci_2000'][1]:.4f}].",
             "* The paired machinery (per-text matrices, shared draws) returns 29_'s marginal label intervals at 2,000 / 42.", ""]
    for T in THRESHOLDS:
        n_ex = sum(e[f"t{T}"]["ci_excludes_zero"] for e in base)
        n_lo = sum(e[f"t{T}"]["delta_ci"][1] < 0 for e in base); n_hi = sum(e[f"t{T}"]["delta_ci"][0] > 0 for e in base)
        lines += [f"## 15 base arms, threshold {T}" + (" (primary)" if T == PRIMARY_THRESHOLD else " (sensitivity)"), "",
                  f"Teacher label vs reference: kappa {base[0][f't{T}']['kappa_label']:.3f}. Intervals excluding 0: {n_ex} of 15"
                  f" ({n_lo} below 0, {n_hi} above 0).", "",
                  "| Model | Role | kappa run | Delta | 95% CI | excl. 0 | share Delta>0 | p (boot) | p Holm (15) |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for e in sorted(base, key=lambda e: -e[f"t{T}"]["delta"]):
            d = e[f"t{T}"]
            lines.append(f"| {e['model']} | {e['role']} | {d['kappa_run']:.3f} | {d['delta']:+.3f} | [{d['delta_ci'][0]:+.3f}, "
                         f"{d['delta_ci'][1]:+.3f}] | {'yes' if d['ci_excludes_zero'] else 'no'} | {d['share_delta_gt_0']:.3f} | "
                         f"{d['p_boot_two_sided']:.4f} | {d['p_holm_base']:.4f} |")
        lines.append("")
    lines += ["## Files", "",
              "* `paired_base_arms.csv`: the 15 base arms (roles original_base, new_base, s3_gate, currency_tier), both thresholds;",
              "  `p_holm` within the 15 arms of a threshold.",
              "* `paired_all_arms.csv`: all 51 non-diagnostic arms (supplementary); `p_holm` within the 51 arms of a threshold.",
              "* `report.json`: everything above plus the reproduction record, input hashes, the correlation of the run and",
              "  label kappas across resamples, and the stored-failure sensitivity.", "",
              "p-values and Holm adjustment are supplementary: two-sided bootstrap p",
              "`min(1, 2 min((#{Delta*<=0}+1)/(B+1), (#{Delta*>=0}+1)/(B+1)))`. Exploratory; no confirmatory claim.", "",
              "## Sensitivity: rows with a stored failure", "",
              "29_ counts rows whose request failed or whose output was unparsable with their stored fallback score 0",
              "(`parse_failures` 0). The main tables keep that (exact 29_ values). `report.json` -> `sensitivity_stored_failures_excluded`",
              "recomputes Delta without those rows, for the run and the label alike:", ""]
    for sv in payload["sensitivity_stored_failures_excluded"]:
        for T in THRESHOLDS:
            d = sv[f"t{T}"]
            lines.append(f"* {sv['model']} ({sv['role']}, {sv['stored_failure_rows']} row{'s' if sv['stored_failure_rows'] != 1 else ''}, {', '.join(sv['failure_reasons'])}),"
                         f" threshold {T}: Delta {d['delta']:+.3f} [{d['delta_ci'][0]:+.3f}, {d['delta_ci'][1]:+.3f}] on {sv['n_rows']} rows"
                         f" (main table {sv[f'main_delta_t{T}']:+.3f}).")
    lines += ["", f"Generated {payload['generated_at_utc']}, code SHA-256 `{payload['code_sha256']}`, base commit `{payload['git_head']}`.", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", type=Path, required=True, help="25_ export partial_credit_reference_adjacent_residual.csv")
    ap.add_argument("--baseline", type=Path, required=True, help="29_ report.json (2026-10-12) for the reproduction gate")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--boot", type=int, default=BOOT["resamples"])
    ap.add_argument("--seed", type=int, default=BOOT["seed"])
    args = ap.parse_args(argv)

    ref = m29.load_reference(args.reference)
    if len(ref) != N_ITEMS:
        raise SystemExit(f"reference has {len(ref)} items, expected {N_ITEMS}")
    refs = {T: m29.binary_reference(ref, T) for T in THRESHOLDS}
    runs, teacher_by_key, keys0 = load_runs(ref)
    if len(keys0) != N_ROWS:
        raise SystemExit(f"{len(keys0)} rows, expected {N_ROWS}")
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))

    gate = reproduction_gate(runs, teacher_by_key, keys0, refs, baseline, args.reference)
    if not gate["passed"]:
        print("REPRODUCTION FAILED, no output written:", file=sys.stderr)
        for f in gate["failures"]:
            print("  " + f, file=sys.stderr)
        return 2
    print(f"reproduction gate passed: {gate['run_point_kappas_checked']} point kappas, {gate['run_kappa_cis_checked']} intervals, "
          f"teacher label T3 {gate['teacher_label']['t3']['kappa']:.4f} {gate['teacher_label']['t3']['kappa_ci_2000']}")

    # ---- paired bootstrap, one draw matrix for everything
    items = sorted(set(keys0))
    counts = resample_counts(len(items), args.boot, args.seed)
    teacher_rows = [teacher_by_key[k] for k in keys0]
    M_label = {T: item_matrices(keys0, teacher_rows, refs[T], items) for T in THRESHOLDS}
    base_runs = {e["source_id"]: e for e in baseline["runs"]}
    arms, sens = [], []
    for r in runs:
        s = r["source"]
        e = {"source_id": s["source_id"], "run_id": s["run_id"], "model": s["model"], "role": s["role"],
             "condition_id": s["condition_id"], "temperature": s["decoding"].get("temperature"),
             "headline": s["role"] in m29.HEADLINE_ROLES, "n_rows": len(r["keys"]), "n_items": len(set(r["keys"])),
             "parse_failures": r["parse_failures"], "stored_failure_rows": int(sum(r["stored_failure"]))}
        for T in THRESHOLDS:
            d = paired_delta(item_matrices(r["keys"], r["pred"], refs[T], items), M_label[T], counts)
            # point estimates must be the 29_ values (gate already checked them; guard against drift here)
            if abs(d["kappa_run"] - base_runs[s["source_id"]][f"reference_t{T}"]["kappa"]) > TOL or \
               abs(d["kappa_label"] - baseline["humans"][f"t{T}"]["teacher_vs_reference"]["kappa"]) > TOL:
                raise SystemExit(f"{s['source_id']} T{T}: paired point estimate differs from 29_")
            e[f"t{T}"] = d
        arms.append(e)
        if e["stored_failure_rows"]:
            keep = [i for i, f in enumerate(r["stored_failure"]) if not f]
            kk = [r["keys"][i] for i in keep]; pp = [r["pred"][i] for i in keep]; tt = [teacher_by_key[k] for k in kk]
            it = sorted(set(kk)); cnt = resample_counts(len(it), args.boot, args.seed)
            sv = {"source_id": s["source_id"], "model": s["model"], "role": s["role"], "condition_id": s["condition_id"],
                  "headline": e["headline"], "stored_failure_rows": e["stored_failure_rows"], "failure_reasons": r["failure_reasons"],
                  "n_rows": len(kk), "n_items": len(it)}
            for T in THRESHOLDS:
                sv[f"t{T}"] = paired_delta(item_matrices(kk, pp, refs[T], it), item_matrices(kk, tt, refs[T], it), cnt)
                sv[f"main_delta_t{T}"] = e[f"t{T}"]["delta"]
            sens.append(sv)

    families = {"base": [e for e in arms if e["headline"]], "all": arms}
    if len(families["base"]) != 15 or len(arms) != 51:
        raise SystemExit(f"expected 15 base arms of 51, got {len(families['base'])} of {len(arms)}")
    for fam, members in families.items():
        for T in THRESHOLDS:
            adj = holm([e[f"t{T}"]["p_boot_two_sided"] for e in members])
            for e, a in zip(members, adj):
                e[f"t{T}"][f"p_holm_{fam}"] = a
                e[f"t{T}"][f"holm_family_size_{fam}"] = len(members)

    try:
        head = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        head = None
    cmd = ("python experiments/scripts/32_paired_model_vs_label_kappa.py \\\n"
           f"    --reference {args.reference} \\\n    --baseline {args.baseline} \\\n    --out-dir {args.out_dir}")
    payload = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "status": "exploratory_post_hoc_paired_run_vs_teacher_label_at_reference",
               "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "code_29_sha256": hashlib.sha256((HERE / "29_binary_runs_vs_human_reference.py").read_bytes()).hexdigest(),
               "git_head": head, "selection_sha256_lf": portable_text_sha256(m29.SELECTION),
               "reference_csv": str(args.reference), "reference_sha256": hashlib.sha256(args.reference.read_bytes()).hexdigest(),
               "baseline_report": str(args.baseline), "baseline_report_sha256": hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
               "n_examples": int(m29.N_EXAMPLES), "n_rows": N_ROWS, "n_items": N_ITEMS, "thresholds": list(THRESHOLDS),
               "primary_threshold": PRIMARY_THRESHOLD, "headline_roles": list(m29.HEADLINE_ROLES),
               "bootstrap": {**BOOT, "resamples": args.boot, "seed": args.seed},
               "statistic": "delta = kappa(run, binarised reference) - kappa(teacher label, binarised reference); Cohen's kappa as in 29_",
               "p_values": "supplementary; two-sided bootstrap p = min(1, 2*min((#{d<=0}+1)/(B+1), (#{d>=0}+1)/(B+1))); "
                           "Holm within family: base = 15 base arms per threshold, all = 51 arms per threshold",
               "equivalence_margin": None, "advisory_notes_used": False,
               "reproduction": gate, "arms": arms, "sensitivity_stored_failures_excluded": sens}

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(args.out_dir / "paired_base_arms.csv", families["base"], "base")
    write_csv(args.out_dir / "paired_all_arms.csv", arms, "all")
    (args.out_dir / "README.md").write_text(readme(payload, cmd), encoding="utf-8")

    print(f"{len(arms)} arms, 15 base arms -> {args.out_dir}")
    for T in THRESHOLDS:
        print(f"  threshold {T}: teacher label kappa {families['base'][0][f't{T}']['kappa_label']:.3f}")
        for e in sorted(families["base"], key=lambda e: -e[f"t{T}"]["delta"]):
            d = e[f"t{T}"]
            print(f"    {e['model']:<46} kappa {d['kappa_run']:.3f}  Delta {d['delta']:+.3f} [{d['delta_ci'][0]:+.3f}; "
                  f"{d['delta_ci'][1]:+.3f}]  P(D>0) {d['share_delta_gt_0']:.3f}  p {d['p_boot_two_sided']:.4f} Holm {d['p_holm_base']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
