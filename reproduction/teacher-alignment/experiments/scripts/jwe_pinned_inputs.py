"""Read JWE and ICWE prediction artifacts from pinned git commits, never from the working tree.

The JWE study selection (`experiments/docs/jwe_study_run_selection_20260916.json`) and the two new
on-premise base arms (Qwen3.5-27B, Qwen3-32B) live on commit 46fb4e6 of
`codex/jwe-study-selection-20260916`; the frozen ICWE consolidated predictions live on every branch
(identical blobs on 6d30d74 and 46fb4e6). Reading blobs at pinned commits makes every number in the
evidence outputs traceable to an immutable object, independent of what is checked out.

Every selected prediction file is checked against the selection's LF-canonical SHA-256
(CRLF converted to LF before hashing, the convention of `jwe_run_manifest.portable_text_sha256`).
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import subprocess
from functools import lru_cache
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]

# Pinned inputs (full SHAs, so a later branch move cannot change what is read).
SELECTION_REF = "46fb4e6b4d9f667e458107f642aba54b50c51d92"  # codex/jwe-study-selection-20260916
ICWE_REF = "6d30d7476dafcaa40a500416b19a82498bb52b8b"       # jwe_extension_work HEAD on 2026-10-13
SELECTION_PATH = "experiments/docs/jwe_study_run_selection_20260916.json"
ICWE_RUN = ("experiments/outputs/incremental_in_context_eval_consolidated/runs/"
            "20260218_consolidated__full__min50__all_models__n0-40_fullrows")
ICWE_MODELS = {
    # model_safe -> (ICWE label, OpenRouter id)
    "anthropic_claude-haiku-4.5": ("Claude Haiku 4.5", "anthropic/claude-haiku-4.5"),
    "deepseek_deepseek-v3.2": ("DeepSeek V3.2", "deepseek/deepseek-v3.2"),
    "qwen_qwen3.5-397b-a17b": ("Qwen 3.5 397B A17B", "qwen/qwen3.5-397b-a17b"),
    "google_gemini-2.5-flash-lite": ("Gemini 2.5 Flash Lite", "google/gemini-2.5-flash-lite"),
    "z-ai_glm-4.7-flash": ("GLM 4.7 Flash", "z-ai/glm-4.7-flash"),
}
FULL_GRID = (0, 1, 3, 5, 10, 15, 20, 25, 30, 35, 40)


def git_blob(ref: str, path: str) -> bytes:
    res = subprocess.run(["git", "-C", str(REPO_ROOT), "show", f"{ref}:{path}"], capture_output=True)
    if res.returncode != 0:
        raise FileNotFoundError(f"{ref}:{path}: {res.stderr.decode(errors='replace').strip()}")
    return res.stdout


def git_blob_id(ref: str, path: str) -> str:
    res = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", f"{ref}:{path}"],
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise FileNotFoundError(f"{ref}:{path}")
    return res.stdout.strip()


def lf_sha256(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


@lru_cache(maxsize=1)
def load_selection() -> dict:
    return json.loads(git_blob(SELECTION_REF, SELECTION_PATH))


def selection_sources(roles: tuple[str, ...] | None = None) -> list[dict]:
    sources = load_selection()["sources"]
    if roles is not None:
        sources = [s for s in sources if s["role"] in roles]
    return sources


def run_meta(source: dict) -> dict:
    meta_file = source["files"]["metadata"]
    data = git_blob(SELECTION_REF, meta_file["path"])
    if lf_sha256(data) != meta_file["sha256_lf"]:
        raise ValueError(f"{source['source_id']}: run_meta hash differs from the pinned selection")
    return json.loads(data)


def backend_of(meta: dict) -> str:
    url = (meta.get("llm_settings") or {}).get("api_url", "")
    if "openrouter.ai" in url:
        return "OpenRouter API"
    if "host.docker.internal:8081" in url:
        return "local vLLM (h200)"
    return f"unknown ({url})"


def _numeric(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("n_examples", "parsable", "re_eval_score", "human_answer_correct", "source_score",
                "confidence", "cv_fold"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["answer_text_lf"] = df["answer_text"].astype(str).str.replace("\r\n", "\n", regex=False)
    return df


def load_source_predictions(source: dict) -> pd.DataFrame:
    """Predictions of one selected source, hash-checked, filtered to its model if the file is shared."""
    pred_file = source["files"]["predictions"]
    data = git_blob(SELECTION_REF, pred_file["path"])
    if lf_sha256(data) != pred_file["sha256_lf"]:
        raise ValueError(f"{source['source_id']}: predictions hash differs from the pinned selection")
    df = pd.read_csv(io.BytesIO(data), keep_default_na=False, dtype=str)
    if "model" in df.columns:
        df = df[df["model"] == source["model"]].copy()
    return _numeric(df)


def load_icwe_predictions(model_safe: str) -> pd.DataFrame:
    data = git_blob(ICWE_REF, f"{ICWE_RUN}/02_predictions/{model_safe}/in_context_predictions.csv")
    df = pd.read_csv(io.BytesIO(data), keep_default_na=False, dtype=str)
    return _numeric(df)


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (center - half, center + half)


def per_n_agreement(df: pd.DataFrame) -> pd.DataFrame:
    """ICWE convention (08_plot_accuracy_overlay_full_runs.py --parsable-only): per n, the share of
    parsable rows whose binary prediction equals `human_answer_correct`. The all-rows variant counts
    an unparsable row with its stored fallback score, as 29_binary_runs_vs_human_reference.py does."""
    rows = []
    for n_value, grp in df.groupby("n_examples", sort=True):
        pars = grp[grp["parsable"] == 1]
        k = int((pars["re_eval_score"] == pars["human_answer_correct"]).sum())
        n_pars = int(len(pars))
        k_all = int((grp["re_eval_score"] == grp["human_answer_correct"]).sum())
        lo, hi = wilson(k, n_pars)
        rows.append({
            "n_examples": int(n_value),
            "n_rows": int(len(grp)),
            "n_parsable": n_pars,
            "parse_rate": n_pars / len(grp),
            "agree_k": k,
            "agreement": k / n_pars if n_pars else float("nan"),
            "wilson95_low": lo,
            "wilson95_high": hi,
            "agree_k_all_rows_fallback": k_all,
            "agreement_all_rows_fallback": k_all / len(grp),
        })
    return pd.DataFrame(rows)


def first_n_reaching(curve: pd.DataFrame, target: float) -> int | None:
    """ICWE Table 3 rule (12_generate_paper_metrics_snapshot.compute_table3_thresholds): smallest grid
    value n whose agreement is >= target; None if no grid value reaches it."""
    hit = curve.sort_values("n_examples")
    hit = hit[hit["agreement"] >= target]
    return None if hit.empty else int(hit.iloc[0]["n_examples"])


def first_n_staying(curve: pd.DataFrame, target: float) -> int | None:
    """Added descriptive column (not an ICWE quantity): smallest grid value n from which every larger
    grid value also stays >= target. Differs from first_n_reaching when attainment is transient."""
    c = curve.sort_values("n_examples").reset_index(drop=True)
    ok = (c["agreement"] >= target).tolist()
    for i in range(len(ok)):
        if all(ok[i:]):
            return int(c.loc[i, "n_examples"])
    return None
