"""Render the three existing appendix figures from published aggregate inputs only.
Derived from make_figures.py (PhD Central, 2026-10-12_jwe-human-agreement),
accessed 2026-10-15. Plotting functions and values retained; other figures and
private report loading removed. No metric estimation, bootstrap or raw data.
335.7426 TeX pt is the previously measured river-journal text width.
"""
from pathlib import Path
import csv,json
import matplotlib as mpl
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from orx_figstyle import BASELINE,MUTED,PALETTE,SEQUENTIAL,figure,save,texpt_to_inches,use_style
HERE=Path(__file__).resolve().parent
DATA=HERE/'data'
WIDTH=texpt_to_inches(335.7426)
def _save(fig,stem,**kwargs):
    save(fig,stem,strict=True,**kwargs)
    # Keep the distributed audit portable across checkouts.
    audit=Path(str(stem)+'.audit.json')
    doc=json.loads(audit.read_text())
    doc['stem']=Path(doc['stem']).name
    doc['files']=[Path(name).name for name in doc['files']]
    audit.write_text(json.dumps(doc,indent=2)+'\n')


CODERS = {"jonas": "JG", "andreas": "AB"}

MODELS = {  # fixed order everywhere
    "partial_credit_qwen36_20260818": "Qwen3.6-27B",
    "partial_credit_qwen38_20260818": "Qwen3.8-27B",
    "partial_credit_phi4_20260818": "Phi-4",
    "partial_credit_mistral_20260818": "Mistral Small 3.2",
}

def rows(name):
    with open(DATA / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

def fig_teacher_relation():
    ct = {(r["rater"], int(r["teacher_label"]), int(r["level"])): int(r["count"]) for r in rows("teacher_label_crosstab.csv")}
    cmap = mpl.colormaps[SEQUENTIAL]
    colors = [cmap(x) for x in np.linspace(0.05, 0.92, 5)]
    fig, ax = figure(width=WIDTH, ratio=0.36)
    ypos, ylabels, pos = [], [], 0.0
    for rater in ("jonas", "andreas"):
        for teacher, tname in ((0, "teacher: incorrect"), (1, "teacher: correct")):
            vec = np.array([ct[(rater, teacher, l)] for l in range(5)], float)
            left = 0.0
            for l in range(5):
                share = vec[l] / vec.sum() * 100
                ax.barh(pos, share, left=left, color=colors[l], height=0.8, edgecolor="white", linewidth=0.5)
                left += share
            ylabels.append(f"{CODERS[rater]}, {tname} (n={int(vec.sum())})")
            ypos.append(pos)
            pos -= 1.0
        pos -= 0.5
    ax.set_yticks(ypos, ylabels)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of rows per coder level (%)")
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    fig.legend(handles=[Patch(color=colors[l], label=f"Level {l}") for l in range(5)],
              loc="outside upper center", ncols=5, handlelength=1.0)
    _save(fig, HERE / "fig08_teacher_label_relation", expected_width=WIDTH)

def fig_model_vs_reference():
    doc = json.loads((DATA / "consensus_model_vs_reference.json").read_text(encoding="utf-8"))
    hl = doc["human_labels"]
    if hl.get("primary_reference") != "soft" or hl.get("adjacent_residual_boundary") is None:
        raise ValueError("fig10 needs the E5 adjacent-residual report with the soft primary reference")
    fig, ax = figure(width=WIDTH, ratio=0.42)
    y = np.arange(len(MODELS))[::-1]
    for yi, cell in zip(y, MODELS):
        pol = doc["models"][cell]["reference_policies"]
        lo_s, hi_l = pol["strict"]["qwk"], pol["lenient"]["qwk"]
        ax.plot([min(lo_s, hi_l), max(lo_s, hi_l)], [yi - 0.16, yi - 0.16], color=BASELINE, lw=2.2, alpha=0.35, solid_capstyle="butt", zorder=1)
        ax.plot(lo_s, yi - 0.16, marker="<", ls="", color=PALETTE["orange"], ms=4.2, mec="white", mew=0.4, zorder=3)
        ax.plot(hi_l, yi - 0.16, marker=">", ls="", color=PALETTE["green"], ms=4.2, mec="white", mew=0.4, zorder=3)
        v = pol["soft"]["qwk"]; lo, hi = pol["soft"]["qwk_ci"]
        ax.errorbar(v, yi + 0.12, xerr=[[v - lo], [hi - v]], fmt="o", color=PALETTE["blue"], ms=4.0,
                    elinewidth=0.9, capsize=0, mec="white", mew=0.4, zorder=4)
    ax.set_yticks(y, list(MODELS.values()))
    ax.set_xlim(0.35, 0.7)
    ax.set_xlabel("QWK, model vs. human reference (3 levels)")
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    handles = [Line2D([], [], marker="o", ls="-", lw=0.9, color=PALETTE["blue"], label="primary: boundary cases half per coder (95% CI)"),
               Line2D([], [], marker="<", ls="", color=PALETTE["orange"], label="boundary cases to the lower class"),
               Line2D([], [], marker=">", ls="", color=PALETTE["green"], label="boundary cases to the higher class")]
    fig.legend(handles=handles, loc="outside upper center", ncols=1)
    _save(fig, HERE / "fig10_model_vs_reference", expected_width=WIDTH)

NICE = {"qwen/qwen3.5-397b-a17b": "Qwen3.5-397B (API)", "anthropic/claude-haiku-4.5": "Claude Haiku 4.5",
        "Qwen/Qwen3.5-27B": "Qwen3.5-27B", "google/gemini-3.5-flash-lite": "Gemini 3.5 Flash-Lite",
        "Qwen/Qwen3.6-27B": "Qwen3.6-27B", "deepseek/deepseek-v3.2": "DeepSeek V3.2", "microsoft/phi-4:16k": "Phi-4",
        "Qwen/Qwen3-32B": "Qwen3-32B", "Qwen/Qwen3.8-27B": "Qwen3.8-27B", "openai/gpt-5.6-luna": "GPT-5.6 Luna",
        "mistralai/Mistral-Small-3.2-24B-Instruct-2506": "Mistral Small 3.2", "qwen/qwen3.8-flash": "Qwen3.8 Flash",
        "deepseek/deepseek-v4-flash": "DeepSeek V4 Flash", "z-ai/glm-4.7-flash": "GLM-4.7 Flash",
        "google/gemini-2.5-flash-lite": "Gemini 2.5 Flash-Lite"}

def fig_binary_runs():
    doc = json.loads((DATA / "binary_runs_vs_reference.json").read_text(encoding="utf-8"))
    runs = sorted((r for r in doc["runs"] if r["headline"]), key=lambda r: r["reference_t3"]["kappa"])
    if len(runs) != 15 or doc["primary_threshold"] != 3:
        raise ValueError("fig11 expects the 15 headline arms with threshold 3")
    tv = doc["humans"]["t3"]["teacher_vs_reference"]
    fig, ax = figure(width=WIDTH, ratio=0.62)
    y = np.arange(len(runs))
    ax.axvspan(tv["kappa_ci"][0], tv["kappa_ci"][1], color=MUTED, alpha=0.6, lw=0)
    ax.axvline(tv["kappa"], color=BASELINE, lw=0.8, ls="--")
    for yi, r in zip(y, runs):
        ref, te = r["reference_t3"], r["teacher"]
        ax.plot([ref["kappa"], te["kappa"]], [yi, yi], color=BASELINE, lw=0.6, zorder=1)
        ax.errorbar(ref["kappa"], yi, xerr=[[ref["kappa"] - ref["kappa_ci"][0]], [ref["kappa_ci"][1] - ref["kappa"]]],
                    fmt="o", color=PALETTE["blue"], ms=3.4, elinewidth=0.9, capsize=0, mec="white", mew=0.4, zorder=3)
        ax.plot(te["kappa"], yi, marker="s", ls="", color=PALETTE["orange"], ms=3.2, mec="white", mew=0.4, zorder=3)
    ax.set_yticks(y, [NICE[r["model"]] for r in runs])
    ax.set_xlim(0.45, 0.9)
    ax.set_xlabel("Cohen's kappa, binary (correct from level 3)")
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    handles = [Line2D([], [], marker="o", ls="-", lw=0.9, color=PALETTE["blue"], label="vs. human reference (95% CI)"),
               Line2D([], [], marker="s", ls="", color=PALETTE["orange"], label="vs. historical teacher label"),
               Patch(color=MUTED, label="teacher label vs. human reference (95% CI)")]
    fig.legend(handles=handles, loc="outside upper center", ncols=2)
    _save(fig, HERE / "fig11_binary_runs_vs_reference", expected_width=WIDTH)

if __name__ == '__main__':
    use_style()
    fig_teacher_relation()
    fig_model_vs_reference()
    fig_binary_runs()
    # PNG is a browser preview; the PDF and SVG remain vector source assets.
    import pymupdf
    for name in ['fig08_teacher_label_relation','fig10_model_vs_reference','fig11_binary_runs_vs_reference']:
        doc=pymupdf.open(HERE/(name+'.pdf'))
        doc[0].get_pixmap(matrix=pymupdf.Matrix(2,2)).save(HERE/(name+'.png'))
