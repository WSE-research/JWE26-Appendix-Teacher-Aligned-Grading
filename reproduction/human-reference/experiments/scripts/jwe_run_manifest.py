"""Explicit, checksummed run selection for the JWE partial-credit analysis."""

import hashlib
import json
from pathlib import Path

def portable_text_sha256(path):
    """Hash text with checkout CRLF converted to canonical LF; content is otherwise byte-exact."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


PLAN_SHA256 = portable_text_sha256(Path(__file__).resolve().parents[1] / "ANALYSIS_PLAN.md")
REQUIRED = ("cell_id", "analysis_class", "model", "prompt", "decoding", "status", "predictions_csv",
            "run_id", "predictions_sha256", "run_meta_csv", "run_meta_sha256",
            "source_pool_csv", "source_pool_sha256", "system_prompt_sha256")


def validate(manifest_path, requested_cells, *, root=None, n_examples=40, pool_sha256=None):
    """Return pinned cells only; blocked/missing requested cells fail closed."""
    path = Path(manifest_path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "jwe-run-manifest-v1" or doc.get("analysis_plan_sha256") != PLAN_SHA256:
        raise ValueError("Manifest schema or binding analysis plan checksum mismatch")
    if doc.get("n_examples") != n_examples or (pool_sha256 and doc.get("pool_sha256") != pool_sha256):
        raise ValueError("Manifest operating point or pool identity mismatch")
    cells = doc.get("cells")
    if not isinstance(cells, list) or not cells:
        raise ValueError("Manifest requires explicit planned cells")
    planned = doc.get("planned_cells")
    if not isinstance(planned, list) or len(set(planned)) != len(planned) or not planned:
        raise ValueError("Manifest requires a distinct planned-cell inventory")
    by_id = {}
    seen_runs, seen_paths = set(), set()
    for cell in cells:
        if not isinstance(cell, dict) or any(k not in cell for k in REQUIRED):
            raise ValueError("Incomplete manifest cell")
        ident = cell["cell_id"]
        if not isinstance(ident, str) or not ident or ident in by_id:
            raise ValueError(f"Duplicate or invalid cell ID: {ident!r}")
        by_id[ident] = cell
        if cell.get("analysis_class") not in ("exploratory", "confirmatory", "replication"):
            raise ValueError(f"Analysis classification missing for {ident}")
        if cell["prompt"] == "partial_credit" and cell["analysis_class"] != "exploratory":
            raise ValueError(f"Partial-credit cells are exploratory under ANALYSIS_PLAN.md section 6: {ident}")
        if not isinstance(cell["decoding"], dict) or not cell["model"] or not cell["prompt"]:
            raise ValueError(f"Missing model, prompt or decoding for {ident}")
        if cell["status"] == "ready" and cell["analysis_class"] == "exploratory" and cell["prompt"] == "partial_credit":
            if cell["decoding"] != {"temperature": 0.2, "max_output_tokens": 512,
                                    "use_response_format": False}:
                raise ValueError(f"Partial-credit decoding plan mismatch for {ident}")
        if cell["status"] not in ("ready", "missing", "blocked"):
            raise ValueError(f"Unknown status for {ident}")
        if cell["status"] != "ready":
            if (not cell.get("reason") or any(cell[k] for k in ("predictions_csv", "run_id",
                "predictions_sha256", "run_meta_csv", "run_meta_sha256", "source_pool_csv",
                "source_pool_sha256", "system_prompt_sha256"))):
                raise ValueError(f"Blocked/missing cell {ident} needs a reason and no run")
            continue
        if not all(isinstance(cell[k], str) and cell[k] for k in ("predictions_csv", "run_id", "predictions_sha256",
                 "run_meta_csv", "run_meta_sha256", "source_pool_csv", "source_pool_sha256", "system_prompt_sha256")):
            raise ValueError(f"Incomplete ready run for {ident}")
        if cell["run_id"] in seen_runs or cell["predictions_csv"] in seen_paths:
            raise ValueError(f"Duplicate run ID or prediction path for {ident}")
        seen_runs.add(cell["run_id"]); seen_paths.add(cell["predictions_csv"])
    if len(set(requested_cells)) != len(requested_cells) or not requested_cells:
        raise ValueError("Requested cells must be distinct and nonempty")
    if set(planned) != set(by_id):
        raise ValueError("Planned-cell inventory mismatch")
    if set(requested_cells) - set(by_id):
        raise ValueError(f"Unplanned requested cells: {sorted(set(requested_cells) - set(by_id))}")
    selected = {}
    base = Path(root) if root else path.resolve().parents[2]
    for ident in requested_cells:
        cell = by_id[ident]
        if cell["status"] != "ready":
            raise ValueError(f"Requested cell {ident} is {cell['status']}: {cell['reason']}")
        target = (base / cell["predictions_csv"]).resolve()
        if not target.is_relative_to(base.resolve()) or not target.is_file():
            raise ValueError(f"Missing/unsafe prediction path for {ident}")
        if target.parents[2].name != cell["run_id"]:
            raise ValueError(f"Run ID/path mismatch for {ident}")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != cell["predictions_sha256"]:
            raise ValueError(f"Prediction checksum mismatch for {ident}")
        meta_path = (base / cell["run_meta_csv"]).resolve()
        pool_path = (base / cell["source_pool_csv"]).resolve()
        for candidate, expected in ((meta_path, cell["run_meta_sha256"]),
                                    (pool_path, cell["source_pool_sha256"])):
            if not candidate.is_relative_to(base.resolve()) or not candidate.is_file():
                raise ValueError(f"Missing/unsafe run provenance path for {ident}")
            actual = portable_text_sha256(candidate) if candidate == meta_path else hashlib.sha256(candidate.read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError(f"Run provenance checksum mismatch for {ident}")
        if meta_path.parents[1].name != cell["run_id"] or pool_path.parents[1].name != cell["run_id"]:
            raise ValueError(f"Run provenance path/ID mismatch for {ident}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        runs = meta.get("model_runs", [])
        if (meta.get("models") != [cell["model"]] or meta.get("manual_csv_sha256") != doc.get("manual_csv_sha256")
                or meta.get("system_prompt_sha256") != cell["system_prompt_sha256"]
                or len(runs) != 1 or runs[0].get("condition_id") != cell["prompt"]
                or runs[0].get("model") != cell["model"]
                or any(runs[0].get("effective_request_settings", {}).get(k) != v
                       for k, v in cell["decoding"].items())):
            raise ValueError(f"Run metadata disagrees with planned model/prompt/decoding for {ident}")
        cell = dict(cell)
        cell["_source_pool_path"] = pool_path
        selected[ident] = (cell, target)
    return doc, selected
