#!/usr/bin/env python3
"""Blind five-level (0/1/2/3/4) re-grading of the JWE evaluation answers.

    python experiments/scripts/21_label_partial_credit.py --rater jonas
    python experiments/scripts/21_label_partial_credit.py --rater jonas --sync
    python experiments/scripts/21_label_partial_credit.py --agreement

Two raters work on their own machines and exchange results through git. Each writes only
`labels/partial_credit__<rater>.csv`, so the two never touch the same file and cannot conflict.

Design decisions, and why they are not negotiable:

**Blind.** The rater sees the question and the student answer, nothing else. The deployed grader's
score, the earlier lecturer verdict and the LLM feedback are not merely hidden, they are absent
from `labelling_pool.csv` entirely. Blinding by absence beats blinding by user interface: a later
edit to the display cannot leak what the file does not contain. This matters because the existing
gold label is the deployed grader's score confirmed or overruled by a lecturer, and on this pool the
lecturer confirmed it 407 times out of 450. A trivial oracle repeating the deployed grader scores
90.44 percent. Labels produced while looking at the old ones would inherit that anchoring.

**One rating per distinct answer text.** Several students wrote identical answers to one item.
Rating that string ten times wastes effort and invites the same rater to grade the same text
differently. The label is broadcast back to every pool row sharing the text at join time.

**Question-major, random within question, identical for both raters.** One rubric is held in mind
at a time. The order is derived from the data alone, never from the rater, and is stable regardless
of input row order, so both raters see the same sequence and inter-rater agreement is not confounded
by different fatigue trajectories. Because the order is random within question, stopping early still
leaves an unbiased subsample of each question.

**Strictly append-only.** Every rating is one appended line, flushed immediately. `u` (undo) appends
a retraction rather than rewriting, so no code path ever truncates the file. Verified to survive
SIGKILL mid-session.

**Independent, then adjudicated.** Rate without discussing. Agreement is computed on the raw,
pre-adjudication labels; disagreements are resolved afterwards in a separate pass. A kappa computed
after adjudication measures only whether you eventually agreed.
"""

from __future__ import annotations

import argparse
import label_safety
import csv
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
POOL = REPO_ROOT / "experiments" / "data" / "manual_eval" / "labelling_pool.csv"
LABEL_DIR = REPO_ROOT / "experiments" / "data" / "manual_eval" / "labels"

# Pinned so both raters provably grade the same items. Regenerating the pool must be a deliberate
# act that updates this constant, not something that silently happens on one machine.
POOL_SHA256 = "6082e25812778e4057f6d3bbb16088b68b123f76f32a6589274c0ba08e652cbd"
POOL_ITEMS = 439
POOL_QUESTIONS = 9

FIELDS = ["QuestionID", "answer_text_sha256", "level", "note", "rated_at_utc", "seconds", "pool_sha256", "label_scale"]
LABEL_SCALE = "human_0_4_v1"
BACKUP_DIR = None
SYNC_RATER = None
VALID = {"0", "1", "2", "3", "4"}
THREE_WAY = {0: 0, 1: 1, 2: 1, 3: 1, 4: 2}
RETRACT = "__RETRACTED__"
NOTE_ONLY = "__NOTE__"

RUBRIC = """\
  0  wrong or empty        nothing correct about the question asked
  1  correct fragments     relevant pieces, but does not yet answer the question
  2  partly answered       about half answered, or a correct core plus a factual error
  3  correct, incomplete   a required part is missing or vague; no factual errors
  4  fully correct         everything requested is present and factually correct"""

KEYS = """\
  0 / 1 / 2 / 3 / 4   rate                    ?   show the question again
  s           skip for now            u   retract the previous rating (this session)
  n           add a note              q   save and quit"""


def wrap(text: str, width: int = 92, indent: str = "    ") -> str:
    out = []
    for para in (text or "").splitlines() or [""]:
        out.append(textwrap.fill(para, width=width, initial_indent=indent,
                                 subsequent_indent=indent) if para.strip() else "")
    return "\n".join(out)


def load_pool() -> list[dict]:
    if not POOL.exists():
        sys.exit(f"Missing {POOL.relative_to(REPO_ROOT)}. Run `git pull` first.")
    digest = hashlib.sha256(POOL.read_bytes()).hexdigest()
    csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
    with POOL.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    problems = []
    if digest != POOL_SHA256:
        problems.append(f"sha256 is {digest[:16]}..., expected {POOL_SHA256}...")
    if len(rows) != POOL_ITEMS:
        problems.append(f"{len(rows)} rows, expected {POOL_ITEMS}")
    nq = len({r["QuestionID"] for r in rows})
    if nq != POOL_QUESTIONS:
        problems.append(f"{nq} questions, expected {POOL_QUESTIONS}")
    if problems:
        sys.exit("Refusing to run: the item pool is not the pinned one.\n  "
                 + "\n  ".join(problems)
                 + "\nBoth raters must grade an identical item set, so this is fatal.")
    keys = [(r["QuestionID"], r["answer_text_sha256"]) for r in rows]
    if len(set(keys)) != len(keys):
        sys.exit("Refusing to run: duplicate (QuestionID, answer_text_sha256) in the pool.")
    return rows


def ordered(items: list[dict]) -> list[dict]:
    out = []
    for qid in sorted({i["QuestionID"] for i in items}, key=lambda q: (len(q), q)):
        group = [i for i in items if i["QuestionID"] == qid]
        # Canonicalise before shuffling: random.shuffle permutes the list it is handed, so a
        # different input row order would otherwise yield a different sequence despite the same
        # seed, and the two raters would diverge. The sha is unique per question, so this total
        # order has no ties and needs no tie-breaker.
        group.sort(key=lambda i: i["answer_text_sha256"])
        random.Random(int(hashlib.sha256(qid.encode()).hexdigest()[:8], 16)).shuffle(group)
        out.extend(group)
    return out


def label_path(rater: str) -> Path:
    safe = rater.strip().lower()
    if not re.fullmatch(r"[a-z0-9_-]+", safe):
        sys.exit("--rater must use only a-z, 0-9, underscore or hyphen")
    return LABEL_DIR / f"partial_credit__{safe}.csv"


def aggregate_three_way(level: int) -> int:
    """Analysis only. Never overwrite or infer five-level human labels."""
    if isinstance(level, bool) or not isinstance(level, int) or level not in THREE_WAY:
        raise ValueError(f"Not a five-level human label: {level!r}")
    return THREE_WAY[level]


def read_label_rows(path: Path) -> list[dict]:
    """Reject legacy/mixed schemas rather than silently reinterpret their 0/1/2."""
    if not path.exists() or path.stat().st_size == 0:
        return []
    csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
    if not path.read_bytes().endswith((b"\n", b"\r")):
        raise ValueError(f"{path}: interrupted final record; preserve and restore the log.")
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, strict=True)
        if reader.fieldnames not in (FIELDS, FIELDS + ["adjudicator", "rater_levels"]):
            raise ValueError(f"{path}: missing five-level schema. Preserve legacy files separately; "
                             "three-level labels cannot be converted losslessly. Re-rate independently.")
        try:
            rows = list(reader)
        except csv.Error as exc:
            raise ValueError(f"{path}: malformed CSV; file left unchanged") from exc
    for line, row in enumerate(rows, 2):
        if (None in row or any(row.get(f) is None for f in reader.fieldnames)
                or not row.get("QuestionID") or not row.get("answer_text_sha256")
                or row.get("level") not in VALID | {RETRACT, NOTE_ONLY}
                or row.get("label_scale") != LABEL_SCALE
                or row.get("pool_sha256") != POOL_SHA256):
            raise ValueError(f"{path}:{line}: malformed row, wrong pool or incompatible label scale. "
                             "File left unchanged; inspect/restore this log before continuing.")
    return rows


def load_labels(path: Path, warn: bool = True) -> dict[tuple[str, str], str]:
    """Replay five-level raw labels without aggregation; last write wins, undo removes."""
    out: dict[tuple[str, str], str] = {}
    for row in read_label_rows(path):
        key = row["QuestionID"], row["answer_text_sha256"]
        if row["level"] == NOTE_ONLY:
            continue
        if row["level"] == RETRACT:
            out.pop(key, None)
        else:
            out[key] = row["level"]
    return out


def load_pending_notes(path: Path) -> dict:
    notes = {}
    for row in read_label_rows(path):
        key = row["QuestionID"], row["answer_text_sha256"]
        if row["level"] in {NOTE_ONLY, RETRACT}:
            notes[key] = row["note"]
        else:
            notes.pop(key, None)
    return notes


def validate_coverage(labels: dict, pool_keys: set, *, complete: bool = False) -> None:
    unknown = set(labels) - pool_keys
    if unknown:
        raise ValueError(f"Label file contains {len(unknown)} keys outside the pinned pool")
    if complete and set(labels) != pool_keys:
        raise ValueError(f"Both raters must finish before agreement/adjudication: "
                         f"{len(pool_keys - set(labels))} labels still missing")


def append_record(path: Path, row: dict, fields: list[str]) -> None:
    """Append a versioned raw row. Refuse schema mixing or an interrupted old write."""
    read_label_rows(path)
    row = {**row, "label_scale": LABEL_SCALE, "pool_sha256": POOL_SHA256}
    if not row.get("QuestionID") or not row.get("answer_text_sha256"):
        raise ValueError("A raw label requires both QuestionID and answer_text_sha256")
    if row.get("level") not in VALID | {RETRACT, NOTE_ONLY}:
        raise ValueError(f"Invalid raw level: {row.get('level')!r}")
    need_header = not path.exists() or path.stat().st_size == 0
    if not need_header:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            if next(csv.reader(fh)) != fields:
                raise ValueError(f"{path}: incompatible log header; refusing to append")
        with path.open("rb") as fh:
            fh.seek(-1, 2)
            if fh.read(1) not in (b"\n", b"\r"):
                raise ValueError(f"{path}: interrupted final line; restore it before appending")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if need_header:
            w.writeheader()
        w.writerow(row)
        fh.flush()
        os.fsync(fh.fileno())
    if BACKUP_DIR is not None:
        try:
            bundle = label_safety.snapshot(path, BACKUP_DIR, POOL_SHA256, LABEL_SCALE)
            if SYNC_RATER is not None:
                run_sync(SYNC_RATER, path=path)
        except (Exception, SystemExit) as exc:
            raise RuntimeError("Label is saved locally, but backup or Git transfer failed. STOP: "
                               "preserve the log and retry --sync before resuming.") from exc


def append(path: Path, row: dict) -> None:
    append_record(path, row, FIELDS)


def load_adjudicated(path: Path, rater_maps: dict, pool_keys: set) -> dict:
    """Reject resolutions made against a different pair or changed raw labels."""
    surviving = {}
    for row in read_label_rows(path):
        key = row["QuestionID"], row["answer_text_sha256"]
        if row["level"] == NOTE_ONLY:
            continue
        if row["level"] == RETRACT:
            surviving.pop(key, None)
        else:
            surviving[key] = row
    validate_coverage(surviving, pool_keys)
    for key, row in surviving.items():
        if len(rater_maps) != 2 or any(key not in m for m in rater_maps.values()):
            raise ValueError("Adjudication needs both original rater labels")
        expected = " ".join(f"{name}={m[key]}" for name, m in sorted(rater_maps.items()))
        if row.get("rater_levels") != expected:
            raise ValueError(f"Stale adjudication for {key}: raw rater labels/pair changed. "
                             "Retract the resolution and adjudicate again.")
    return {key: row["level"] for key, row in surviving.items()}


def quadratic_weighted_kappa(a: list[int], b: list[int], k: int = 3) -> float:
    if len(a) != len(b) or k < 2 or any(x not in range(k) for x in a + b):
        raise ValueError("QWK requires aligned labels within the explicit scale")
    n = len(a)
    if n == 0:
        return float("nan")
    O = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        O[x][y] += 1
    ha, hb = [a.count(i) for i in range(k)], [b.count(i) for i in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = ((i - j) ** 2) / ((k - 1) ** 2)
            num += w * O[i][j]
            den += w * ha[i] * hb[j] / n
    return 1.0 - num / den if den else float("nan")


def run_sync(rater: str, path: Path | None = None) -> int:
    with label_safety.session_lock(LABEL_DIR / ".git-sync"):
        return _run_sync(rater, path)


def _run_sync(rater: str, path: Path | None = None) -> int:
    """Commit only this rater file; safely reconcile disjoint rater updates."""
    path = path or label_path(rater)
    pool_keys = {(r["QuestionID"], r["answer_text_sha256"]) for r in load_pool()}
    labels = load_labels(path)
    validate_coverage(labels, pool_keys)
    rel = path.relative_to(REPO_ROOT).as_posix()

    def git(*args, check=True, binary=False):
        result = subprocess.run(["git", "-C", str(REPO_ROOT), *args], capture_output=True)
        if check and result.returncode:
            sys.exit(f"git {' '.join(args[:2])} failed:\n"
                     + result.stderr.decode("utf-8", errors="replace"))
        if not binary:
            result.stdout = result.stdout.decode("utf-8").strip()
        return result

    if git("diff", "--cached", "--name-only").stdout:
        sys.exit("Staged changes exist. Preserve/resolve them before syncing labels.")
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").stdout
    if not upstream.startswith("origin/"):
        sys.exit("Labels require an origin tracking branch.")
    branch = upstream.removeprefix("origin/")
    expected = path.read_bytes() if path.exists() else None
    if expected is not None:
        git("add", "--", rel)
        if git("diff", "--cached", "--name-only").stdout:
            git("commit", "-m", f"labels: ratings by {rater} ({len(labels)} items)")
    # Retry delivery even when an earlier invocation already committed the file.
    git("fetch", "origin")
    base = git("merge-base", "HEAD", upstream).stdout
    local = git("rev-parse", "HEAD").stdout
    remote = git("rev-parse", upstream).stdout
    if remote != base:
        changed = git("diff", "--name-only", base, upstream).stdout.splitlines()
        if path.name == "partial_credit_adjudicated.csv":
            sys.exit("Remote changed during adjudication. Preserve local resolutions and restart after an explicit update.")
        if rel in changed:
            sys.exit("Remote changed this rater's file. Both versions are preserved; "
                     "stop and reconcile explicitly, never overwrite or force-push.")
        if any(
                not re.fullmatch(r"experiments/data/manual_eval/labels/partial_credit__[a-z0-9_-]+\.csv", f)
                for f in changed):
            sys.exit("Remote contains code or non-rater changes. Local labels are committed; "
                     "update the reviewed checkout explicitly before continuing.")
        git("merge", "--no-edit", upstream)
    if expected is None:
        print("Repository ready; no saved labels yet.")
        return 0
    if git("show", f"HEAD:{rel}", binary=True).stdout != expected:
        sys.exit("Git changed CSV bytes. Local evidence is preserved; check .gitattributes.")
    git("push", "origin", f"HEAD:refs/heads/{branch}")
    git("fetch", "origin")
    if git("show", f"{upstream}:{rel}", binary=True).stdout != expected:
        sys.exit("Remote label checksum differs. Preserve both versions and stop.")
    print(f"Confirmed on origin: {len(labels)} labels by {rater}; "
          f"SHA256 {hashlib.sha256(expected).hexdigest()}")
    return 0


def run_agreement(only: list[str] | None) -> int:
    files = sorted(LABEL_DIR.glob("partial_credit__*.csv"))
    if only:
        want = {r.lower() for r in only}
        files = [f for f in files if f.stem.split("__", 1)[1].lower() in want]
    if len(files) != 2:
        sys.exit(f"Need exactly two rater files in {LABEL_DIR}, found {len(files)}. "
                 f"Use --raters to select explicitly.")
    sets = {f.stem.split("__", 1)[1]: load_labels(f) for f in files}
    pool_keys = {(r["QuestionID"], r["answer_text_sha256"]) for r in load_pool()}
    for labels in sets.values():
        validate_coverage(labels, pool_keys, complete=True)
    names = sorted(sets)
    print(f"raters: {', '.join(names)}\n")
    for f in files:
        print(f"raw log sha256 {f.stem.split('__', 1)[1]}: {hashlib.sha256(f.read_bytes()).hexdigest()}")
    print(f"pool sha256: {POOL_SHA256}; five-level raw pre-adjudication, 439 unique items")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            shared = sorted(set(sets[a]) & set(sets[b]))
            pairs = [(int(sets[a][k]), int(sets[b][k])) for k in shared]
            if not pairs:
                print(f"{a} vs {b}: no overlapping rated items")
                continue
            xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
            exact = sum(1 for x, y in pairs if x == y) / len(pairs)
            adj = sum(1 for x, y in pairs if abs(x - y) <= 1) / len(pairs)
            qwk = quadratic_weighted_kappa(xs, ys, k=5)
            xs3 = [aggregate_three_way(x) for x in xs]
            ys3 = [aggregate_three_way(y) for y in ys]
            qwk3 = quadratic_weighted_kappa(xs3, ys3, k=3)
            print(f"{a} vs {b}")
            print(f"  overlap n={len(pairs)}  ({len(sets[a])} by {a}, {len(sets[b])} by {b})")
            print(f"  QWK5={qwk:.3f}  exact={exact:.1%}  within-1={adj:.1%}")
            print(f"  QWK3={qwk3:.3f} (analysis aggregation 0/1/1/1/2)")
            if qwk != qwk:
                print("  (QWK is undefined when both raters used a single level)")
            dis = [k for k in shared if sets[a][k] != sets[b][k]]
            print(f"  {len(dis)} disagreements to adjudicate")
            for question in ["pool", *sorted({key[0] for key in shared}, key=lambda q: (len(q), q))]:
                scope = shared if question == "pool" else [key for key in shared if key[0] == question]
                levels = [(int(sets[a][key]), int(sets[b][key])) for key in scope]
                print(f"  {question}: n={len(levels)} QWK5={quadratic_weighted_kappa([x for x, _ in levels], [y for _, y in levels], k=5):.3f} "
                      f"QWK3={quadratic_weighted_kappa([aggregate_three_way(x) for x, _ in levels], [aggregate_three_way(y) for _, y in levels], k=3):.3f}")
                for k, mapper in ((5, lambda x: x), (3, aggregate_three_way)):
                    confusion = [[sum(mapper(x) == i and mapper(y) == j for x, y in levels)
                                  for j in range(k)] for i in range(k)]
                    print(f"    scale={k} {a} distribution={[sum(row) for row in confusion]} "
                          f"{b} distribution={[sum(confusion[i][j] for i in range(k)) for j in range(k)]}")
                    print(f"    scale={k} confusion ({a} rows, {b} columns): {confusion}")
    return 0


def agreement_report_bytes(raters: list[str]) -> bytes:
    """Canonical report over the current complete raw logs; no adjudication data."""
    import io
    from contextlib import redirect_stdout
    with redirect_stdout(io.StringIO()) as output:
        run_agreement(raters)
    return output.getvalue().encode("utf-8")


def canonical_report_bytes(blob: bytes) -> bytes:
    """Allow checkout newline conversion while preserving every report character."""
    return blob.replace(b"\r\n", b"\n")


def agreement_archive_path(report_path: Path) -> Path:
    return report_path.with_name(report_path.name + ".archive.json")


def archive_agreement(report_path: Path, raters: list[str], report_bytes: bytes) -> None:
    """Preserve one report and its separate identity record without replacement."""
    names = sorted(r.lower() for r in raters)
    archive = {
        "schema": "jwe-pre-adjudication-archive-v1",
        "report_name": report_path.name,
        "report_sha256": hashlib.sha256(canonical_report_bytes(report_bytes)).hexdigest(),
        "pool_sha256": POOL_SHA256,
        "raw_logs_sha256": {name: hashlib.sha256(label_path(name).read_bytes()).hexdigest()
                            for name in names},
    }
    archive_path = agreement_archive_path(report_path)
    with archive_path.open("x", encoding="utf-8") as fh:
        json.dump(archive, fh, indent=2, sort_keys=True)
        fh.write("\n")
        fh.flush(); os.fsync(fh.fileno())


def validate_agreement_archive(report_path: Path, raters: list[str]) -> dict:
    """Require exact canonical report bytes and archived raw/pool identity."""
    archive_path = agreement_archive_path(report_path)
    if not report_path.is_file() or not archive_path.is_file():
        raise ValueError("Missing pre-adjudication report or archive identity")
    try:
        archive = json.loads(archive_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("Damaged pre-adjudication archive identity") from exc
    names = sorted(r.lower() for r in raters)
    if (archive.get("schema") != "jwe-pre-adjudication-archive-v1"
            or archive.get("pool_sha256") != POOL_SHA256
            or archive.get("report_name") != report_path.name
            or set(archive.get("raw_logs_sha256", {})) != set(names)):
        raise ValueError("Pre-adjudication archive identity mismatch")
    for name in names:
        if hashlib.sha256(label_path(name).read_bytes()).hexdigest() != archive["raw_logs_sha256"][name]:
            raise ValueError("Raw log differs from archived pre-adjudication evidence")
    report_bytes = canonical_report_bytes(report_path.read_bytes())
    if (hashlib.sha256(report_bytes).hexdigest() != archive.get("report_sha256")
            or report_bytes != agreement_report_bytes(names)):
        raise ValueError("Pre-adjudication report differs from canonical complete raw agreement")
    return archive


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rater", help="your name, e.g. jonas or andreas")
    ap.add_argument("--question", help="rate only this QuestionID, e.g. r1q15")
    ap.add_argument("--sync", action="store_true", help="pull, then commit and push your own label file")
    ap.add_argument("--agreement", action="store_true", help="inter-rater agreement, then exit")
    ap.add_argument("--agreement-out", type=Path, help="save agreement to a new file; never overwrite")
    ap.add_argument("--raters", nargs="+", help="restrict --agreement to these raters")
    ap.add_argument("--backup-dir", type=Path, help="optional local recovery-copy folder")
    ap.add_argument("--sync-on-save", action="store_true", help="confirm each save on origin before continuing")
    args = ap.parse_args()

    if args.agreement:
        with label_safety.session_lock(LABEL_DIR / ".session"):
            if args.agreement_out is None:
                return run_agreement(args.raters)
            import io
            from contextlib import redirect_stdout
            with redirect_stdout(io.StringIO()) as output:
                result = run_agreement(args.raters)
            names = sorted(r.lower() for r in args.raters) if args.raters else sorted(
                p.stem.split("__", 1)[1] for p in LABEL_DIR.glob("partial_credit__*.csv"))
            report_bytes = output.getvalue().encode("utf-8")
            if agreement_archive_path(args.agreement_out).exists():
                raise ValueError("Pre-adjudication archive already exists; refusing report creation")
            with args.agreement_out.open("xb") as fh:
                fh.write(report_bytes)
                fh.flush()
                os.fsync(fh.fileno())
            archive_agreement(args.agreement_out, names, report_bytes)
            print(output.getvalue(), end="")
            print(f"Agreement saved: {args.agreement_out}")
            return result
    if not args.rater:
        ap.error("--rater is required (or use --agreement)")
    with label_safety.session_lock(LABEL_DIR / ".session"), label_safety.session_lock(label_path(args.rater)):
        if args.sync:
            return run_sync(args.rater)
        global BACKUP_DIR, SYNC_RATER
        previous, previous_rater = BACKUP_DIR, SYNC_RATER
        BACKUP_DIR = label_safety.prepare_backup(args.backup_dir or LABEL_DIR / ".backups")
        SYNC_RATER = args.rater if args.sync_on_save else None
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            return run_rating(args)
        finally:
            BACKUP_DIR, SYNC_RATER = previous, previous_rater


def run_rating(args) -> int:
    items = ordered(load_pool())
    pool_keys = {(r["QuestionID"], r["answer_text_sha256"]) for r in items}
    if args.question:
        items = [i for i in items if i["QuestionID"] == args.question]
        if not items:
            sys.exit(f"No items for {args.question}")

    path = label_path(args.rater)
    labels = load_labels(path)
    validate_coverage(labels, pool_keys)
    bundle = label_safety.snapshot(path, BACKUP_DIR, POOL_SHA256, LABEL_SCALE)
    if SYNC_RATER is not None:
        run_sync(SYNC_RATER)
    print(f"Local recovery copies: {BACKUP_DIR}")
    scope = {(i["QuestionID"], i["answer_text_sha256"]) for i in items}
    done_here = {k for k in labels if k in scope}          # counts only the current scope
    todo = [i for i in items if (i["QuestionID"], i["answer_text_sha256"]) not in labels]

    print(f"\nRater: {args.rater}   file: {path.relative_to(REPO_ROOT)}")
    print(f"{len(done_here)} of {len(items)} rated, {len(todo)} to go.\n")
    print("Rubric:\n" + RUBRIC + "\n\nKeys:\n" + KEYS)
    print("\nYou see only the question and the answer. The original grade is withheld on purpose:\n"
          "seeing it would anchor these labels to the old ones and defeat the exercise.\n"
          "Rate independently; do not discuss items until both of you are finished.\n")

    current_q = None
    history: list[dict] = []
    i = 0
    while i < len(todo):
        item = todo[i]
        key = (item["QuestionID"], item["answer_text_sha256"])
        if item["QuestionID"] != current_q:
            current_q = item["QuestionID"]
            remaining = sum(1 for x in todo[i:] if x["QuestionID"] == current_q)
            print("\n" + "=" * 96)
            print(f"QUESTION {current_q}   ({remaining} answers still to rate here)")
            print("=" * 96)
            print(wrap(item["question_text"]))
            print("=" * 96)

        rated_now = len({k for k in labels if k in scope})
        print(f"\n[{rated_now + 1}/{len(items)}]  {current_q}")
        print(wrap(item["answer_text"] or "(empty answer)"))

        note = load_pending_notes(path).get(key, "")
        if note:
            print(f"  saved note: {note}")
        shown = datetime.now(timezone.utc)
        while True:
            try:
                raw = input("\n  0/1/2/3/4  s=skip  u=undo  n=note  ?=question  q=quit > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print(f"\n\nSaved {len({k for k in labels if k in scope})} ratings. "
                      "Run the same command again to resume.")
                return 0
            if raw == "?":
                print(wrap(item["question_text"]))
                continue
            if raw == "n":
                note = input("  note > ").strip()
                append(path, {"QuestionID": key[0], "answer_text_sha256": key[1],
                              "level": NOTE_ONLY, "note": note,
                              "rated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                              "seconds": ""})
                print("  Note saved; this item remains unrated until you choose a level.")
                continue
            if raw == "q":
                print(f"\nSaved {len({k for k in labels if k in scope})} ratings. "
                      "Run the same command again to resume.")
                return 0
            if raw == "s":
                i += 1
                break
            if raw == "u":
                if not history:
                    print("  nothing to undo in this session")
                    continue
                prev = history.pop()
                # Append a retraction. Never rewrite: a truncating rewrite interrupted by Ctrl-C
                # loses the whole session, which is exactly what this tool must not do.
                append(path, {"QuestionID": prev["QuestionID"],
                              "answer_text_sha256": prev["answer_text_sha256"],
                              "level": RETRACT, "note": prev.get("note", ""),
                              "rated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                              "seconds": "", "pool_sha256": POOL_SHA256})
                labels.pop((prev["QuestionID"], prev["answer_text_sha256"]), None)
                todo.insert(i, next(x for x in items
                                    if (x["QuestionID"], x["answer_text_sha256"])
                                    == (prev["QuestionID"], prev["answer_text_sha256"])))
                print(f"  retracted (level {prev['level']}); it will come up again")
                break
            if raw in VALID:
                now = datetime.now(timezone.utc)
                append(path, {"QuestionID": item["QuestionID"],
                              "answer_text_sha256": item["answer_text_sha256"],
                              "level": raw, "note": note,
                              "rated_at_utc": now.isoformat(timespec="seconds"),
                              "seconds": round((now - shown).total_seconds(), 1),
                              "pool_sha256": POOL_SHA256})
                labels[key] = raw
                history.append({**item, "level": raw, "note": note})
                i += 1
                break
            print("  please enter 0, 1, 2, 3, 4, s, u, n, ? or q")

    remaining = scope - set(labels)
    if remaining:
        print(f"\n{len(remaining)} items in this scope remain unrated. Run the same command to resume.")
        return 0
    print(f"\nAll {len(items)} items in this scope rated. Thank you.")
    if set(labels) == pool_keys:
        print("Both raters must finish independently before viewing or discussing the other labels.")
        print(f"Sync (also permitted during rating): python {Path(__file__).relative_to(REPO_ROOT)} --rater {args.rater} --sync")
    else:
        print("Continue independently. Intermediate sync is allowed; do not view the other rater file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
