# Vendored from alphaXiv openresearch-cli, agent-skills/orx-figures/assets/orx_figstyle.py
# (MIT License, snapshot 2026-08-29, commit "OR-216 Add an orx-figures skill for
# publication-quality figures (#260)"). Kept under its upstream name so the
# reference documents apply verbatim.
#
# Local modifications for the PhD Central `paper-figures` skill 1.1.0
# (2026-10-07). They are not upstream changes, and no upstream sync is implied:
#   - audit: declared `expected_width` with a tolerance replaces the width
#     whitelist; vertical and horizontal colorbar labels are checked; new
#     machine-readable `audit_report()` and `AUDIT_SCOPE`; a font fallback is
#     reported as a note instead of a defect; unsourced venue claims removed
#   - save(): keyword-only `expected_width`, `width_tolerance`, `strict`
#     (writes `<stem>.audit.json` and raises `FigureAuditError` after the
#     figure files are written); timestamp-free PDF/SVG metadata. Positional
#     use and the list-of-paths return are unchanged.
#   - use_style(): fixed `svg.hashsalt` for repeatable SVG ids
#   - input validation (1-D shape, matching length, empty, non-finite) in
#     mean_ci, diff_ci, band, label_ends, pareto_front, annotate_matrix
#   - new helpers: paired_diff_ci, pair_by_id, normalize_confusion,
#     texpt_to_inches, FigureAuditError
#   - palette comment narrowed: the palette alone does not guarantee greyscale
#     separation
#
# The upstream license follows. Keep it with every copy of this file, and copy
# LICENSE-openresearch-cli.txt alongside when vendoring.
#
# MIT License
#
# Copyright (c) 2026 alphaXiv
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Publication figure style for matplotlib.

Vendor this file (and LICENSE-openresearch-cli.txt) next to the figure scripts
that import it, so a figure stays reproducible after the session that made it
ends.

    from orx_figstyle import COLUMN, PALETTE, figure, save, use_style

    use_style()
    fig, ax = figure(width=COLUMN)
    ax.plot(x, y, color=PALETTE["blue"])
    save(fig, "figs/loss_curve", expected_width=COLUMN)
"""

from __future__ import annotations

import json
import math
import os
import sys
import warnings

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

# Default printed widths in inches, taken from common ML venue templates
# (ICML, CVPR, IEEE two-column; NeurIPS/article single column). They are
# defaults, not measurements of your document: measure `\the\columnwidth` /
# `\the\textwidth` and pass the result to `save(..., expected_width=...)`.
COLUMN = 3.25  # one column of a two-column paper
TEXT = 5.5  # \textwidth of a single-column paper
WIDE = 6.75  # both columns of a two-column paper (figure*)

# How far the built width may differ from the declared target, in inches.
WIDTH_TOLERANCE = 0.02

# TeX points per inch. `\the\columnwidth` reports TeX pt (1/72.27 in); PDF
# tools such as pdfinfo report PostScript/big points (1/72 in).
TEX_POINTS_PER_INCH = 72.27

# Okabe-Ito: chosen to stay distinguishable under common forms of color-vision
# deficiency. It does not separate every pair in greyscale (orange and sky
# blue are close in lightness), so add a redundant channel (marker, linestyle,
# hatch, direct label) whenever series are told apart by color alone. Use in
# this order so the first two series stay the furthest apart.
PALETTE = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "red": "#D55E00",
    "purple": "#CC79A7",
    "cyan": "#56B4E9",
    "yellow": "#F0E442",
    "black": "#000000",
}
CYCLE = [PALETTE[k] for k in ("blue", "orange", "green", "red", "purple", "cyan")]

# Reference elements (baselines, chance level, targets) are grey, never a
# palette color: the colors belong to the things being compared. BASELINE is
# the line weight of grey; MUTED is the fill weight, light enough that a dark
# edge still reads as the outline.
BASELINE = "#7F7F7F"
MUTED = "#CFCFCF"

SEQUENTIAL = "viridis"
DIVERGING = "RdBu_r"

# Two-sided 95% t critical values by degrees of freedom. Seed counts are small
# enough that the normal approximation understates the interval.
_T95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
    8: 2.306, 9: 2.262, 10: 2.228, 12: 2.179, 15: 2.131, 20: 2.086, 30: 2.042,
    40: 2.021, 60: 2.000, 120: 1.980,
}


# Figure text is sans by default: it holds its strokes at the 5-8pt sizes tick
# labels print at, and the house register for figures and diagrams is a
# Helvetica-compatible sans. The faces below share Helvetica's metrics but are
# distinct designs. Each stack runs from preferred to always-present, ending
# in matplotlib's bundled fonts so a script still renders on a bare box. Font
# requirements differ by venue; check the author guidelines, not this list.
SANS = [
    "Helvetica Neue", "Helvetica", "Arial",
    "TeX Gyre Heros", "Nimbus Sans", "Liberation Sans",
    "DejaVu Sans",
]
# STIXGeneral ships with Matplotlib, reducing variation from installed fonts.
# Its design differs from Times New Roman; rendering depends on the environment.
SERIF = ["STIXGeneral", "TeX Gyre Termes", "Nimbus Roman", "Times New Roman", "DejaVu Serif"]

_resolved_font: str | None = None

# What `audit_report()` looks at, and what it does not. `clean` means only that
# none of the checked items failed.
AUDIT_SCOPE = {
    "checked": [
        "figure width against the declared expected_width (or the default widths when none is declared)",
        "PDF export font-type rcParam (42), not inspection of the exported fonts",
        "axes titles",
        "missing x/y labels on quantitative axes (tick-text heuristic)",
        "colorbar labels, vertical and horizontal",
        "text below the 5 pt house floor at the built size",
        "text overlapping other text",
        "text running off the canvas",
    ],
    "not_checked": [
        "text, legends or annotations covering data marks (bars, lines, points)",
        "color or greyscale distinguishability of series",
        "correctness of data, statistics, intervals or captions",
        "accessibility, such as alternative text or contrast",
        "axis-label completeness with custom/mathtext formatters",
        "actual PDF/PS font embedding (inspect exports separately)",
        "printed size after LaTeX inclusion if the declared target is wrong",
        "overall visual quality: open the PDF at 100 %",
    ],
}


class FigureAuditError(RuntimeError):
    """Raised by `save(..., strict=True)` after the files are written.

    `report` is the `audit_report()` dict, `paths` the written figure files,
    `report_path` the JSON copy of the report. Nothing is deleted.
    """

    def __init__(self, stem: str, report: dict, paths: list[str], report_path: str | None):
        self.stem = stem
        self.report = report
        self.paths = list(paths)
        self.report_path = report_path
        codes = ", ".join(problem["code"] for problem in report["problems"])
        super().__init__(
            f"figure audit {stem}: {len(report['problems'])} problem(s) ({codes}); "
            f"files kept: {', '.join(self.paths + ([report_path] if report_path else []))}"
        )


def texpt_to_inches(points) -> float:
    """Convert a TeX length in pt (`252.0pt` or `252.0`) to inches."""
    if isinstance(points, str):
        points = points.strip().removesuffix("pt")
    return float(points) / TEX_POINTS_PER_INCH


def _available_font(stack) -> str | None:
    """The first font in `stack` this machine actually has."""
    import matplotlib.font_manager as fm

    installed = {f.name for f in fm.fontManager.ttflist}
    return next((name for name in stack if name in installed), None)


def use_style(family: str = "sans") -> None:
    """Apply the house rcParams. Call once, before creating any figure.

    Sans is the default. Pass `family="serif"` to match a serif-set document
    when the figure carries heavy math and you want it to read as part of the
    body text; for a plain `article` in Computer Modern, set
    `mathtext.fontset` to `"cm"` afterwards.
    """
    # Figure scripts only ever write files, and often run where no display
    # exists; picking Agg up front avoids a backend failure at import.
    mpl.use("Agg")
    global _resolved_font
    _resolved_font = _available_font(SERIF if family == "serif" else SANS)
    mpl.rcParams.update({
        "font.family": "serif" if family == "serif" else "sans-serif",
        "font.serif": SERIF,
        "font.sans-serif": SANS,
        # stixsans pairs with a Helvetica-metric text face and is bundled, so
        # math in a figure does not fall back to a different-looking family.
        "mathtext.fontset": "stix" if family == "serif" else "stixsans",
        # Type 42 embeds TrueType outlines. Some submission checkers flag
        # Type 3 fonts; the venue's own requirements decide.
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        # Fixed salt: SVG element ids repeat across runs.
        "svg.hashsalt": "orx-figstyle",
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "legend.fontsize": 7,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "figure.dpi": 200,
        "savefig.dpi": 600,
        "savefig.transparent": False,
        "axes.prop_cycle": mpl.cycler(color=CYCLE),
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.6,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "grid.color": "#D9D9D9",
        "grid.linewidth": 0.4,
        "lines.linewidth": 1.2,
        "lines.markersize": 3.5,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "legend.frameon": False,
        "legend.handlelength": 1.4,
        "legend.columnspacing": 1.0,
        "legend.borderaxespad": 0.3,
    })


def figure(width: float = COLUMN, ratio: float = 0.68, **kwargs):
    """One axes at a final printed size. `ratio` is height/width."""
    fig, ax = plt.subplots(figsize=(width, width * ratio), layout="constrained", **kwargs)
    return fig, ax


def figure_grid(nrows: int = 1, ncols: int = 2, width: float = TEXT, ratio: float = 0.4, **kwargs):
    """A panel grid at a final printed size, sharing one constrained layout."""
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(width, width * ratio), layout="constrained", **kwargs
    )
    return fig, axes


def panel_labels(axes, labels=None, weight: str = "bold", pad: float = 2.0):
    """Label panels (a), (b), ... above each axes' top-left corner.

    Panel letters are how prose names a part of a figure ("as Fig. 2b shows").
    Without them a multi-panel figure can only be referred to by position,
    which breaks the moment a panel moves.
    """
    flat = np.ravel(np.asarray(axes, dtype=object)).tolist()
    labels = labels or [f"({chr(ord('a') + i)})" for i in range(len(flat))]
    for ax, text in zip(flat, labels):
        ax.annotate(
            text,
            xy=(0, 1), xycoords="axes fraction",
            xytext=(0, pad), textcoords="offset points",
            ha="left", va="bottom", fontweight=weight,
            fontsize=mpl.rcParams["axes.labelsize"],
        )


def _looks_numeric(label: str) -> bool:
    try:
        float(label.replace("−", "-").replace("%", "").rstrip("kMBT"))
        return True
    except ValueError:
        return False


def _colorbar_of(ax):
    """`(orientation, label)` if `ax` is a colorbar axes, else None.

    Two signals because the first is a private attribute: a rename would
    otherwise fail every heatmap. A colorbar carries its label on its long
    axis: y for vertical, x for horizontal.
    """
    cbar = getattr(ax, "_colorbar", None)
    if cbar is None and ax.get_label() != "<colorbar>":
        return None
    orientation = getattr(cbar, "orientation", None)
    if orientation not in ("vertical", "horizontal"):
        box = ax.get_position()
        orientation = "vertical" if box.height >= box.width else "horizontal"
    axis = ax.yaxis if orientation == "vertical" else ax.xaxis
    return orientation, axis.get_label().get_text()


def audit_report(fig, *, expected_width=None, width_tolerance: float = WIDTH_TOLERANCE) -> dict:
    """Check a figure against the layout and typography rules; return a dict.

    Keys: `clean` (no problems), `problems` and `notes` (lists of
    `{"code", "message"}`), `width_in`, `height_in`, `expected_width_in`,
    `width_tolerance_in`, `font`, `pdf_fonttype`, and `scope` (a copy of
    `AUDIT_SCOPE`). The dict is JSON-serializable. `clean` is a narrow
    statement: see `scope["not_checked"]`.

    `expected_width` is the measured printed width of the target (inches).
    Without it, a width matching none of COLUMN/TEXT/WIDE is reported as
    undeclared; that alone does not show the figure will be rescaled.
    """
    problems, notes = [], []

    def problem(code: str, message: str) -> None:
        problems.append({"code": code, "message": message})

    def note(code: str, message: str) -> None:
        notes.append({"code": code, "message": message})

    tolerance = float(width_tolerance)
    if not (math.isfinite(tolerance) and tolerance >= 0):
        raise ValueError(f"width_tolerance must be a finite value >= 0, got {width_tolerance!r}")
    expected = None
    if expected_width is not None:
        expected = float(expected_width)
        if not (math.isfinite(expected) and expected > 0):
            raise ValueError(f"expected_width must be a positive finite width in inches, got {expected_width!r}")

    fonttype = mpl.rcParams["pdf.fonttype"]
    if fonttype != 42:
        problem(
            "font-type",
            f"pdf.fonttype is {fonttype}, not 42: call use_style() first; "
            "some submission checkers reject Type 3 fonts",
        )
    if _resolved_font is None:
        note("font-unresolved", "use_style() has not resolved a font; text uses matplotlib's defaults")
    elif _resolved_font.startswith("DejaVu"):
        note(
            "font-fallback",
            f"figure text resolves to {_resolved_font!r}, outside the house Helvetica-compatible "
            "register, so it may not match other figures or diagrams; check the venue's font "
            "requirements, and ask before installing fonts",
        )

    width, height = (float(v) for v in fig.get_size_inches())
    if expected is not None:
        if abs(width - expected) > tolerance:
            problem(
                "width-mismatch",
                f"figure is {width:.2f}in wide but the declared target is {expected:.2f}in "
                f"(tolerance {tolerance:.2f}in); included at width=\\linewidth it would be "
                f"scaled by {expected / width:.2f}, text included",
            )
    elif any(abs(width - known) <= tolerance for known in (COLUMN, TEXT, WIDE)):
        note(
            "width-default",
            f"width {width:.2f}in is a skill default, not a measurement; confirm it against "
            "the document and pass expected_width",
        )
    else:
        problem(
            "width-undeclared",
            f"figure is {width:.2f}in wide, matching none of the defaults "
            f"({COLUMN}/{TEXT}/{WIDE}in), and no expected_width was declared; measure the "
            "target (\\the\\columnwidth in TeX pt / 72.27) and pass expected_width",
        )

    for ax in fig.axes:
        if not ax.axison:
            continue
        for loc in ("center", "left", "right"):
            title = ax.get_title(loc=loc)
            if title:
                problem("axes-title", f"axes title {title!r} duplicates the caption: delete it")
        colorbar = _colorbar_of(ax)
        if colorbar is not None:
            orientation, label = colorbar
            if not label.strip():
                problem(
                    "colorbar-unlabelled",
                    f"a {orientation} colorbar has no label: name the quantity and its unit",
                )
            continue
        for axis, name, shared in (
            (ax.xaxis, "x", ax.get_shared_x_axes()),
            (ax.yaxis, "y", ax.get_shared_y_axes()),
        ):
            if axis.get_label().get_text() or not ax.get_visible():
                continue
            # A shared axis is labelled once, on whichever panel shows the ticks.
            if any(
                getattr(sib, f"get_{name}label")() for sib in shared.get_siblings(ax) if sib is not ax
            ):
                continue
            # Categorical ticks (benchmark or variant names) label themselves;
            # an axis title over them just repeats the tick text. Only a linear
            # axis can be categorical: a log axis is quantitative by
            # construction, and its formatter emits mathtext that no numeric
            # test would accept.
            ticks = [t.get_text() for t in axis.get_ticklabels() if t.get_text().strip()]
            if (
                axis.get_scale() == "linear"
                and ticks
                and not all(_looks_numeric(t) for t in ticks)
            ):
                continue
            problem("axis-unlabelled", f"an axes has no {name} label")

    # House floor: below 5pt is hard to read in print. Bar value labels sit at
    # 5. The size is checked at the built width, which equals the printed size
    # only when the figure is included unscaled.
    tiny = {
        round(t.get_fontsize(), 1)
        for t in fig.findobj(mpl.text.Text)
        if t.get_text().strip() and t.get_fontsize() < 5
    }
    if tiny:
        problem("text-too-small", f"text below the 5pt floor: sizes {sorted(tiny)}")

    for code, message in _text_findings(fig):
        problem(code, message)

    return {
        "clean": not problems,
        "problems": problems,
        "notes": notes,
        "width_in": round(width, 4),
        "height_in": round(height, 4),
        "expected_width_in": expected,
        "width_tolerance_in": tolerance,
        "font": _resolved_font,
        "pdf_fonttype": fonttype,
        "scope": {key: list(items) for key, items in AUDIT_SCOPE.items()},
    }


def _audit(fig) -> list[str]:
    """Legacy entry point: the problem messages of `audit_report(fig)`."""
    return [problem["message"] for problem in audit_report(fig)["problems"]]


def _text_findings(fig) -> list[tuple[str, str]]:
    """Text that overlaps other text or runs off the canvas, as (code, message).

    A label sitting on the axis or through a tick label is a common way a
    figure that satisfies every other rule is still unusable, and it is
    invisible until the figure is drawn. Text over data marks is not checked.
    """
    fig.canvas.draw()
    try:
        renderer = fig.canvas.get_renderer()
    except AttributeError:
        return [("text-uninspectable", "text could not be inspected: no Agg-family canvas; call use_style() first")]

    # A locator can emit ticks just past the view limits; their label artists
    # exist and carry a position but are never drawn. Exclude them by tick
    # location rather than by geometry, which cannot tell them apart.
    offscreen = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            lo, hi = sorted(axis.get_view_interval())
            span = hi - lo
            for tick in list(axis.get_major_ticks()) + list(axis.get_minor_ticks()):
                if not lo - span * 1e-6 <= tick.get_loc() <= hi + span * 1e-6:
                    offscreen.update({id(tick.label1), id(tick.label2)})

    boxes = []
    hidden = set()
    for ax in fig.axes:
        if ax.axison:
            continue
        # Its axis artists still carry positions but are never drawn; the
        # axes' own text is the figure and must stay in the comparison.
        for part in (ax.xaxis, ax.yaxis):
            hidden.update(id(t) for t in part.findobj(mpl.text.Text))
    for text in fig.findobj(mpl.text.Text):
        if id(text) in offscreen or id(text) in hidden:
            continue
        if not text.get_visible() or not text.get_text().strip():
            continue
        try:
            box = text.get_window_extent(renderer)
        except (RuntimeError, ValueError):
            continue
        if box.width > 0 and box.height > 0:
            boxes.append((text, box))

    findings, tolerance = [], 1.5
    clipped = [
        text.get_text()
        for text, box in boxes
        if box.x0 < fig.bbox.x0 - tolerance
        or box.x1 > fig.bbox.x1 + tolerance
        or box.y0 < fig.bbox.y0 - tolerance
        or box.y1 > fig.bbox.y1 + tolerance
    ]
    if clipped:
        findings.append((
            "text-clipped",
            f"text runs off the canvas and will be clipped: {sorted(set(clipped))[:3]}",
        ))

    hits = []
    for i, (text_a, box_a) in enumerate(boxes):
        for text_b, box_b in boxes[i + 1 :]:
            overlap = mpl.transforms.Bbox.intersection(box_a, box_b)
            if overlap is None:
                continue
            if overlap.width > tolerance and overlap.height > tolerance:
                hits.append(f"{text_a.get_text()[:22]!r} over {text_b.get_text()[:22]!r}")
    if hits:
        shown = "; ".join(hits[:3]) + (f" (+{len(hits) - 3} more)" if len(hits) > 3 else "")
        findings.append(("text-overlap", f"overlapping text: {shown}"))
    return findings


def _text_collisions(fig) -> list[str]:
    """Legacy entry point: messages of the text-overlap and off-canvas checks."""
    return [message for _, message in _text_findings(fig)]


# Timestamps make every rerun a different file; None drops them.
_SAVE_METADATA = {"pdf": {"CreationDate": None}, "svg": {"Date": None}}


def save(
    fig,
    stem,
    formats=("pdf", "svg"),
    close: bool = True,
    *,
    expected_width=None,
    width_tolerance: float = WIDTH_TOLERANCE,
    strict: bool = False,
) -> list[str]:
    """Write `stem.pdf` (for \\includegraphics) and `stem.svg` (for preview).

    Returns the written figure paths, as before. The audit is printed to
    stderr. With `strict=True`, `<stem>.audit.json` is written as well and a
    failed audit raises `FigureAuditError` after every file exists, so the
    diagnostic artifacts survive the failure.

    No `bbox_inches="tight"`: trimming to content changes the physical width
    and defeats building at the final size.
    """
    stem = os.fspath(stem)
    # Write first: the audit inspects a live canvas and must never be the
    # reason a finished figure is lost.
    parent = os.path.dirname(stem)
    if parent:
        os.makedirs(parent, exist_ok=True)
    paths = []
    for ext in formats:
        path = f"{stem}.{ext}"
        fig.savefig(path, format=ext, metadata=_SAVE_METADATA.get(ext))
        paths.append(path)
    try:
        report = audit_report(fig, expected_width=expected_width, width_tolerance=width_tolerance)
    finally:
        if close:
            plt.close(fig)
    report["stem"] = stem
    report["files"] = list(paths)

    report_path = None
    if strict:
        report_path = f"{stem}.audit.json"
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    # Printed by default, not raised: a hard failure mid-analysis loses the
    # figure, but a silent pass is how an unpublishable figure reaches the paper.
    if report["problems"]:
        print(f"FIGURE AUDIT {stem}: {len(report['problems'])} problem(s), fix before using", file=sys.stderr)
        for item in report["problems"]:
            print(f"  - {item['message']}", file=sys.stderr)
    else:
        print(
            f"figure audit {stem}: clean (layout and typography checks only; see AUDIT_SCOPE)",
            file=sys.stderr,
        )
    for item in report["notes"]:
        print(f"  note: {item['message']}", file=sys.stderr)

    if strict and report["problems"]:
        raise FigureAuditError(stem, report, paths, report_path)
    return paths


def _require_finite(name: str, values) -> None:
    bad = ~np.isfinite(values)
    if bad.any():
        where = np.argwhere(bad)[:5].tolist()
        raise ValueError(
            f"{name} has {int(bad.sum())} non-finite value(s) (NaN/inf) at {where}; "
            "drop or report failed runs explicitly before summarizing"
        )


def _real_array(name: str, values) -> np.ndarray:
    """Convert numeric values without silently discarding imaginary parts."""
    raw = np.asarray(values)
    if np.iscomplexobj(raw):
        raise ValueError(f"{name} must be real-valued, got dtype {raw.dtype}")
    return np.asarray(values, dtype=float)


def _finite_vector(name: str, values) -> np.ndarray:
    """A non-empty, finite, 1-D float array of samples; a scalar is one sample."""
    array = _real_array(name, values)
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim != 1:
        raise ValueError(f"{name} must be a 1-D array of samples, got shape {array.shape}")
    if array.size == 0:
        raise ValueError(f"{name} is empty: there is no sample to summarize")
    _require_finite(name, array)
    return array


def mean_ci(runs, confidence: float = 0.95):
    """Mean and 95% t-interval across independent replicates (seeds).

    `runs` is either `(n_replicates,)`, one scalar per replicate, which returns
    scalars, or `(n_replicates, n_points)`, one curve per replicate, which
    returns arrays. A single curve is shape `(1, n_points)`; a 1-D vector is
    always read as replicates, never as one curve.

    Returns `(mean, lo, hi)`. Report the interval, not the standard deviation:
    a band of +/- 1 SD says how spread the seeds are, not how well the mean is
    resolved. The t-interval assumes independent replicates. Folds of one
    cross-validation share training data, so do not present this interval over
    folds as if they were independent runs; an interval over items (bootstrap)
    is a separate analysis.
    """
    if confidence != 0.95:
        raise ValueError("only the 95% interval is tabulated; use scipy for others")
    runs = _real_array("runs", runs)
    if runs.ndim not in (1, 2):
        raise ValueError(
            f"runs must be (n_replicates,) or (n_replicates, n_points), got shape {runs.shape}"
        )
    if runs.size == 0:
        raise ValueError(f"runs is empty (shape {runs.shape}): there is no replicate to summarize")
    _require_finite("runs", runs)
    n = runs.shape[0]
    mean = runs.mean(axis=0)
    if n < 2:
        warnings.warn(
            "one replicate: the band is a line, not an interval; say 'single run' in the caption",
            stacklevel=2,
        )
        return mean, mean, mean
    sem = runs.std(axis=0, ddof=1) / math.sqrt(n)
    crit = _t95(n - 1)
    return mean, mean - crit * sem, mean + crit * sem


def family(name: str, n: int, lightest: float = 0.55) -> list[str]:
    """`n` shades of one palette color, lightest first.

    Hue names the method family, shade names the variant within it, so a
    reader separates "prior work" from "ours" before reading the legend.
    """
    base = np.array(mpl.colors.to_rgb(PALETTE[name]))
    if n == 1:
        return [mpl.colors.to_hex(base)]
    steps = np.linspace(lightest, 0.0, n)
    return [mpl.colors.to_hex(base + (1.0 - base) * step) for step in steps]


def pareto_front(x, y, minimize_x: bool = True, maximize_y: bool = True):
    """Indices of the non-dominated points, ordered along the frontier.

    A point is dominated when another point is at least as good on both axes
    and strictly better on one. Points with identical coordinates do not
    dominate each other; the frontier keeps one representative, the first in
    input order, so the line has no zero-length segments. The index list is
    therefore not a census of runs: scatter every run separately.

    `x` and `y` must be finite 1-D arrays of equal length. Empty input returns
    an empty index array. Non-finite values raise: a diverged run is a result
    to report, not a frontier point, so drop it explicitly and say so.
    """
    x = _real_array("x", x)
    y = _real_array("y", y)
    if x.ndim != 1 or y.ndim != 1:
        raise ValueError(f"x and y must be 1-D, got shapes {x.shape} and {y.shape}")
    if x.shape != y.shape:
        raise ValueError(f"x and y must have the same length, got {x.size} and {y.size}")
    if x.size == 0:
        return np.array([], dtype=int)
    _require_finite("x", x)
    _require_finite("y", y)
    cost_x = x if minimize_x else -x
    cost_y = -y if maximize_y else y
    best = np.inf
    front = []
    # Input position is the last key, so ties keep the first point in input order.
    for i in np.lexsort((np.arange(x.size), cost_y, cost_x)):
        if cost_y[i] < best:
            front.append(i)
            best = cost_y[i]
    return np.array(front, dtype=int)


def _t95(df: int) -> float:
    # Round the degrees of freedom down, never to the nearest key: a smaller df
    # gives a larger t, so the interval errs wide rather than overstating how
    # well a handful of seeds resolves the mean.
    covered = [k for k in _T95 if k <= df]
    return _T95[max(covered)] if covered else _T95[1]


def diff_ci(treatment, baseline):
    """Mean difference (treatment - baseline) and its 95% Welch interval.

    For independent arms: each variant was run on its own samples, with no
    pairing between a treatment run and a baseline run. If the design pairs
    runs (same seed and data order, same folds, same item set), align them with
    `pair_by_id` and use `paired_diff_ci`; matching seed names alone do not
    establish pairing.

    An ablation claims a difference, so the figure has to show the interval of
    the difference. Two overlapping per-variant intervals do not mean the
    difference is indistinguishable from zero.
    """
    treatment = _finite_vector("treatment", treatment)
    baseline = _finite_vector("baseline", baseline)
    delta = treatment.mean() - baseline.mean()
    n_t, n_b = treatment.size, baseline.size
    if n_t < 2 or n_b < 2:
        warnings.warn(
            "one sample in an arm: the difference has no interval; say so in the caption",
            stacklevel=2,
        )
        return delta, delta, delta
    var_t = treatment.var(ddof=1) / n_t
    var_b = baseline.var(ddof=1) / n_b
    sem = math.sqrt(var_t + var_b)
    if sem == 0:
        return delta, delta, delta  # every seed identical: the interval is a point
    df = (var_t + var_b) ** 2 / (var_t**2 / (n_t - 1) + var_b**2 / (n_b - 1))
    half = _t95(int(df)) * sem
    return delta, delta - half, delta + half


def paired_diff_ci(treatment, baseline, confidence: float = 0.95):
    """Mean paired difference (treatment - baseline) and its 95% t-interval.

    Use when the design pairs every treatment sample with exactly one baseline
    sample and both arrays are aligned by that pairing (`pair_by_id`). The
    interval is the t-interval of the per-pair differences, df = n - 1.
    """
    if confidence != 0.95:
        raise ValueError("only the 95% interval is tabulated; use scipy for others")
    treatment = _finite_vector("treatment", treatment)
    baseline = _finite_vector("baseline", baseline)
    if treatment.size != baseline.size:
        raise ValueError(
            f"paired samples need one baseline per treatment sample, got {treatment.size} and {baseline.size}"
        )
    differences = treatment - baseline
    n = differences.size
    delta = float(differences.mean())
    if n < 2:
        warnings.warn(
            "one pair: the difference has no interval; say so in the caption",
            stacklevel=2,
        )
        return delta, delta, delta
    spread = float(differences.std(ddof=1))
    if spread == 0:
        return delta, delta, delta  # every pair moved by the same amount
    half = _t95(n - 1) * spread / math.sqrt(n)
    return delta, delta - half, delta + half


def pair_by_id(treatment, baseline):
    """Align two arms by pair id for `paired_diff_ci`.

    `treatment` and `baseline` are iterables of `(pair_id, value)`. Returns
    `(ids, treatment_values, baseline_values)` in a stable id order. Raises when
    an id repeats within an arm or appears in only one arm: an interval over a
    silently reduced set is not the interval the design promised.
    """

    def index(name, records):
        values, repeated = {}, set()
        for key, value in records:
            if key in values:
                repeated.add(key)
            values[key] = value
        if repeated:
            raise ValueError(f"{name}: duplicate pair id(s) {sorted(map(str, repeated))[:5]}")
        return values

    treated = index("treatment", treatment)
    based = index("baseline", baseline)
    only_treatment = sorted(map(str, treated.keys() - based.keys()))
    only_baseline = sorted(map(str, based.keys() - treated.keys()))
    if only_treatment or only_baseline:
        raise ValueError(
            f"unmatched pair id(s): treatment only {only_treatment[:5]}, "
            f"baseline only {only_baseline[:5]}"
        )
    if not treated:
        raise ValueError("no pairs: both arms are empty")
    ids = sorted(treated, key=str)
    return (
        ids,
        _finite_vector("paired treatment", [treated[key] for key in ids]),
        _finite_vector("paired baseline", [based[key] for key in ids]),
    )


def band(ax, x, runs, label=None, color=None, **kwargs):
    """Plot the replicate mean as a line with its 95% interval as a matching band.

    `runs` is `(n_replicates, n_points)`; wrap a single curve as `[curve]`.
    A 1-D replicate vector remains supported when `x` contains one point.
    """
    runs = _real_array("runs", runs)
    x = np.asarray(x)
    if x.ndim != 1 or x.size == 0:
        raise ValueError(f"x must be a non-empty 1-D array, got shape {x.shape}")
    # Keep Matplotlib date/category units; validate their numerical coordinates.
    ax.xaxis.update_units(x)
    _finite_vector("x coordinates", ax.convert_xunits(x))
    # Preserve 1.0.0: scalar replicates can describe a single plotted point.
    if runs.ndim == 1 and x.size == 1:
        runs = runs.reshape(-1, 1)
    if runs.ndim != 2:
        raise ValueError(f"band() needs runs of shape (n_replicates, n_points), got {runs.shape}")
    if x.size != runs.shape[1]:
        raise ValueError(f"x has shape {x.shape} but runs have {runs.shape[1]} points per replicate")
    mean, lo, hi = mean_ci(runs)
    (line,) = ax.plot(x, mean, label=label, color=color, **kwargs)
    ax.fill_between(x, lo, hi, color=line.get_color(), alpha=0.18, linewidth=0)
    return line


def label_ends(ax, lines, labels, pad: float = 3.0, min_gap: float = 7.0, **kwargs):
    """Label each line at its last finite point, in the line's own color.

    Direct labels spare the reader matching a color to a key, and they double
    as the redundant channel when color alone separates the series. Labels
    whose lines converge are nudged apart by `min_gap` points so they stay
    readable, and the right x-limit is extended by exactly the width the
    labels need.
    """
    lines = list(lines)
    labels = list(labels)
    if len(lines) != len(labels):
        raise ValueError(f"{len(lines)} lines but {len(labels)} labels")
    if not labels:
        return
    ends_data = []
    for line, text in zip(lines, labels):
        xs = np.asarray(line.get_xdata(), dtype=float)
        ys = np.asarray(line.get_ydata(), dtype=float)
        finite = np.flatnonzero(np.isfinite(xs) & np.isfinite(ys))
        if finite.size == 0:
            raise ValueError(f"line for label {text!r} has no finite point")
        ends_data.append((xs[finite[-1]], ys[finite[-1]]))

    ax.figure.canvas.draw()  # constrained layout settles the transform at draw
    renderer = ax.figure.canvas.get_renderer()
    pad_px = pad * ax.figure.dpi / 72

    size = kwargs.pop("fontsize", mpl.rcParams["legend.fontsize"])
    widths, heights = [], []
    for text in labels:
        probe = ax.text(0, 0, text, fontsize=size)
        extent = probe.get_window_extent(renderer)
        widths.append(extent.width)
        heights.append(extent.height)
        probe.remove()
    # Separate by the labels' own height, not a fixed point value: the right
    # gap depends on the font, and a constant tuned for one is wrong for another.
    gap_px = max(min_gap * ax.figure.dpi / 72, max(heights) * 1.15)
    # Setting xlim changes the data-to-pixel scale, so the room cannot be
    # measured in the old scale: solve for the limit at which the original span
    # occupies (axes width - label width) pixels.
    x_lo, x_hi = ax.get_xlim()
    need = max(widths) + 2 * pad_px
    axes_px = ax.bbox.width
    if need < axes_px:
        scale = ax.xaxis.get_transform()
        s_lo, s_hi = scale.transform([x_lo, x_hi])
        room = scale.inverted().transform(
            [s_lo + (s_hi - s_lo) * axes_px / (axes_px - need)]
        )[0]
        ax.set_xlim(x_lo, room)

    ends = []
    for line, text, xy in zip(lines, labels, ends_data):
        ends.append([ax.transData.transform(xy)[1], xy, line, text])
    ends.sort(key=lambda end: end[0])
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + gap_px)
    for y_px, xy, line, text in ends:
        offset = (y_px - ax.transData.transform(xy)[1]) * 72 / ax.figure.dpi
        ax.annotate(
            text,
            xy=xy,
            xytext=(pad, offset),
            textcoords="offset points",
            color=line.get_color(),
            va="center",
            fontsize=size,
            clip_on=False,
            **kwargs,
        )


def si_ticks(ax, which: str = "x") -> None:
    """Format ticks as 1.2k / 340M / 7B instead of 1.2e3 / 3.4e8.

    Call it after the limits are final. On a log axis spanning less than a
    decade the minor ticks carry the labels, so they get the same format —
    otherwise matplotlib prints them as `1.85 x 10^0`.
    """

    def fmt(value, _pos):
        for scale, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "k")):
            if abs(value) >= scale:
                trimmed = f"{value / scale:.1f}".rstrip("0").rstrip(".")
                return f"{trimmed}{suffix}"
        return f"{value:g}"

    axis = ax.xaxis if which == "x" else ax.yaxis
    axis.set_major_formatter(mpl.ticker.FuncFormatter(fmt))
    scale = ax.get_xscale() if which == "x" else ax.get_yscale()
    lo, hi = sorted(ax.get_xlim() if which == "x" else ax.get_ylim())
    if scale == "log" and lo > 0 and hi / lo < 10:
        axis.set_minor_formatter(mpl.ticker.FuncFormatter(fmt))


def normalize_confusion(counts, normalize: str = "true"):
    """Fractions and support from a square confusion matrix of counts.

    `counts[i, j]` counts items of true class i predicted as class j.
    `normalize="true"` divides each row by its support (recall per true
    class); `"pred"` divides each column (precision per predicted class).
    Returns `(fractions, support)`.

    Counts must be finite, non-negative whole numbers. Fractional values are
    rejected rather than truncated (they usually mean the matrix is already
    normalized), and the division is done in floating point. A class with zero
    support has no defined rate and stays NaN, never 0.
    """
    raw = np.asarray(counts)
    if raw.dtype == bool or np.iscomplexobj(raw) or not np.issubdtype(raw.dtype, np.number):
        raise ValueError(f"counts must be numeric, got dtype {raw.dtype}")
    counts = raw.astype(float)
    if counts.ndim != 2 or counts.shape[0] != counts.shape[1] or counts.shape[0] == 0:
        raise ValueError(f"counts must be a non-empty square matrix, got shape {counts.shape}")
    _require_finite("counts", counts)
    if (counts < 0).any():
        raise ValueError("counts must be non-negative")
    if not np.array_equal(counts, np.round(counts)):
        raise ValueError("counts must be whole numbers; fractional values suggest an already normalized matrix")
    if normalize == "true":
        axis = 1
    elif normalize == "pred":
        axis = 0
    else:
        raise ValueError(f"normalize must be 'true' or 'pred', got {normalize!r}")
    support = counts.sum(axis=axis, keepdims=True)
    fractions = np.divide(counts, support, out=np.full(counts.shape, np.nan), where=support > 0)
    return fractions, support.ravel()


def annotate_matrix(ax, values, fmt: str = "{:.2f}", image=None, threshold: float = 0.6) -> None:
    """Write each cell's value on a heatmap, in whichever of black or white
    stays legible against that cell. Non-finite cells are left blank; label
    them explicitly (failed, missing) in the calling script."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 2:
        raise ValueError(f"values must be 2-D, got shape {values.shape}")
    if image is None:
        if not ax.images:
            raise ValueError("annotate_matrix needs an image: call imshow first or pass image=")
        image = ax.images[-1]
    shown = tuple(np.shape(image.get_array())[:2])
    if values.shape != shown:
        raise ValueError(f"values have shape {values.shape} but the image shows {shown}")
    norm, cmap = image.norm, image.cmap
    for (row, col), value in np.ndenumerate(values):
        if not np.isfinite(value):
            continue
        rgba = cmap(norm(value))
        luminance = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
        ax.text(
            col, row, fmt.format(value),
            ha="center", va="center", fontsize=6,
            color="black" if luminance > threshold else "white",
        )
