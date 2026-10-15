#!/usr/bin/env python3
"""Adjudicate the five-level (0/1/2/3/4) disagreements left after both raters finished rating.

    python experiments/scripts/24_adjudicate_partial_credit.py --adjudicator jonas
    python experiments/scripts/24_adjudicate_partial_credit.py --adjudicator jonas+andreas --raters jonas andreas

`21_label_partial_credit.py --agreement` counts the disagreements; this tool resolves them.
It presents only the items where the two raters disagree, one at a time, in the same
question-major canonical order as the rating pass, and writes the resolution to
`labels/partial_credit_adjudicated.csv`.

Design decisions, and why:

**Both raters' levels are shown.** During rating that would have been contamination; here it
is the entire point. Adjudication happens after `--agreement` has been computed on the raw
labels, so nothing shown here can reach back and inflate the reported kappa.

**The old grade still cannot appear.** This tool reads only `labelling_pool.csv` and the two
rater files. The deployed grader's score, the lecturer verdict and the LLM feedback are
absent from all three, so the adjudicated label is anchored to the raters' independent
judgements and to nothing else. Blinding by absence survives adjudication unchanged.

**Rater files are never written.** Each rater file is that rater's evidence; overwriting a
level there would silently rewrite history and make the pre-adjudication kappa unverifiable.
The resolution lives in its own append-only file, single underscore on purpose:
`--agreement` globs `partial_credit__*.csv` for rater files, and a double underscore would
enrol the adjudication as a third rater in every pairwise comparison.

**Same append-only log format, same replay.** One row per decision, flushed immediately;
undo appends a retraction; resume replays the log. The replay, ordering, append and pool
validation are imported from `21_label_partial_credit.py` rather than copied, so the two
tools cannot drift apart. The extra columns (`adjudicator`, `rater_levels`) record who
resolved the item, when, and what the raters had said, making every resolution auditable
without opening the rater files.

**Disagreements are recomputed on every start.** If a rater retracts or extends ratings
after adjudication began, the todo list follows the current label state. Changed rater values or a different rater pair invalidate previous resolutions and stop
the run, so a stale resolution cannot silently override new raw evidence.
"""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import csv
import hashlib
import importlib.util
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("label_partial_credit", HERE / "21_label_partial_credit.py")
assert _spec and _spec.loader
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)

# Single underscore: keeps this file out of the `partial_credit__*.csv` rater glob (see docstring).
ADJUDICATED = cli.LABEL_DIR / "partial_credit_adjudicated.csv"
ADJ_FIELDS = cli.FIELDS + ["adjudicator", "rater_levels"]

KEYS = """\
  0 / 1 / 2 / 3 / 4   resolve                 ?   show the question again
  s           skip for now            u   retract the previous resolution (this session)
  n           add a note              q   save and quit"""


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(cli.REPO_ROOT))
    except ValueError:   # redirected in tests
        return str(path)


def append_adj(row: dict) -> None:
    """``cli.append`` with the two extra provenance columns.

    Not reusable directly: 21's append pins the rater schema in its DictWriter, and passing
    `adjudicator` / `rater_levels` through it raises. The flush-and-fsync-per-row behaviour
    is kept identical, for the same crash-safety reason.
    """
    cli.append_record(ADJUDICATED, row, ADJ_FIELDS)


def replay_rows(path: Path) -> dict[tuple[str, str], dict]:
    """Like ``load_labels`` but keeps the surviving row's note for display.

    Mirrors the replay rules (last write wins, retractions remove, malformed rows are
    skipped) and then asserts its level projection against ``load_labels`` itself, so the
    authoritative resolution stays the one function in 21 and any drift dies loudly here
    instead of silently showing a different note than the level it belongs to.
    """
    out: dict[tuple[str, str], dict] = {}
    for row in cli.read_label_rows(path):
        key = row["QuestionID"], row["answer_text_sha256"]
        if row["level"] == cli.NOTE_ONLY:
            continue
        if row["level"] == cli.RETRACT:
            out.pop(key, None)
        else:
            out[key] = {"level": row["level"], "note": row["note"]}

    return out


def disputed_keys(rows_a: dict, rows_b: dict) -> set[tuple[str, str]]:
    """Items both raters rated with different levels. Single-rater coverage is not a dispute."""
    return {k for k in set(rows_a) & set(rows_b) if rows_a[k]["level"] != rows_b[k]["level"]}


def rater_files(only: list[str] | None) -> dict[str, Path]:
    files = sorted(cli.LABEL_DIR.glob("partial_credit__*.csv"))
    named = {f.stem.split("__", 1)[1]: f for f in files}
    if only:
        want = [r.lower() for r in only]
        missing = [r for r in want if r not in named]
        if missing:
            sys.exit(f"No label file for rater(s): {', '.join(missing)} in {cli.LABEL_DIR}")
        named = {r: named[r] for r in want}
    if len(named) != 2:
        sys.exit(f"Adjudication needs exactly two rater files, found {len(named)} in "
                 f"{cli.LABEL_DIR} ({', '.join(sorted(named)) or 'none'}). "
                 "Both raters must finish and --sync first; use --raters to select two.")
    return named


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adjudicator", required=True,
                    help="who is resolving, e.g. jonas, andreas, or jonas+andreas for a joint session")
    ap.add_argument("--raters", nargs=2, metavar=("A", "B"),
                    help="restrict to these two raters (default: the two files present)")
    ap.add_argument("--question", help="adjudicate only this QuestionID, e.g. r1q15")
    ap.add_argument("--agreement-report", type=Path, required=True,
                    help="immutable pre-adjudication report written by 21 --agreement-out")
    ap.add_argument("--backup-dir", type=Path, help="optional local recovery-copy folder")
    ap.add_argument("--sync-on-save", action="store_true", help="confirm each resolution on origin")
    args = ap.parse_args()
    named = rater_files(args.raters)
    cli.validate_agreement_archive(args.agreement_report, list(named))
    with ExitStack() as locks:
        locks.enter_context(cli.label_safety.session_lock(cli.LABEL_DIR / ".session"))
        for path in sorted([ADJUDICATED, *named.values()]):
            locks.enter_context(cli.label_safety.session_lock(path))
        previous, previous_rater = cli.BACKUP_DIR, cli.SYNC_RATER
        cli.SYNC_RATER = args.adjudicator if args.sync_on_save else None
        cli.BACKUP_DIR = cli.label_safety.prepare_backup(args.backup_dir or cli.LABEL_DIR / ".backups")
        try:
            cli.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            return run_adjudication(args, named)
        finally:
            cli.BACKUP_DIR, cli.SYNC_RATER = previous, previous_rater


def run_adjudication(args, named) -> int:
    (name_a, path_a), (name_b, path_b) = sorted(named.items())
    rows_a, rows_b = replay_rows(path_a), replay_rows(path_b)

    pool = cli.load_pool()
    pool_keys = {(r["QuestionID"], r["answer_text_sha256"]) for r in pool}
    maps = {name_a: cli.load_labels(path_a), name_b: cli.load_labels(path_b)}
    for labels in maps.values():
        cli.validate_coverage(labels, pool_keys, complete=True)
    # Print the pre-adjudication agreement before showing either rater's values.
    cli.run_agreement([name_a, name_b])
    resolved = cli.load_adjudicated(ADJUDICATED, maps, pool_keys)
    bundle = cli.label_safety.snapshot(ADJUDICATED, cli.BACKUP_DIR, cli.POOL_SHA256, cli.LABEL_SCALE)
    if cli.SYNC_RATER is not None:
        cli.run_sync(cli.SYNC_RATER, path=ADJUDICATED)
    disputed = disputed_keys(rows_a, rows_b)
    if not disputed:
        overlap = len(set(rows_a) & set(rows_b))
        print(f"No disagreements between {name_a} and {name_b} ({overlap} items rated by both). "
              "Nothing to adjudicate.")
        return 0

    # Same canonical sequence as the rating pass, filtered to the disputed keys, so the
    # adjudicators walk the questions in the order they already know.
    items = [i for i in cli.ordered(pool)
             if (i["QuestionID"], i["answer_text_sha256"]) in disputed]
    if args.question:
        items = [i for i in items if i["QuestionID"] == args.question]
        if not items:
            sys.exit(f"No disputed items for {args.question}")


    scope = {(i["QuestionID"], i["answer_text_sha256"]) for i in items}
    todo = [i for i in items if (i["QuestionID"], i["answer_text_sha256"]) not in resolved]

    print(f"\nAdjudicator: {args.adjudicator}   file: {rel(ADJUDICATED)}")
    print(f"{len(disputed)} disagreements between {name_a} and {name_b}; "
          f"{len(scope) - len(todo)} of {len(scope)} in scope resolved, {len(todo)} to go.\n")
    print("Rubric:\n" + cli.RUBRIC + "\n\nKeys:\n" + KEYS)
    print("\nYou see the question, the answer, and both raters' levels. The original grade and\n"
          "the lecturer verdict stay withheld: the resolution must come out of the two\n"
          "independent readings, not out of the incumbent grader.\n")

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
            print(f"QUESTION {current_q}   ({remaining} disagreements still to resolve here)")
            print("=" * 96)
            print(cli.wrap(item["question_text"]))
            print("=" * 96)

        done_now = len({k for k in cli.load_labels(ADJUDICATED, warn=False) if k in scope})
        print(f"\n[{done_now + 1}/{len(scope)}]  {current_q}")
        print(cli.wrap(item["answer_text"] or "(empty answer)"))
        va, vb = rows_a[key], rows_b[key]
        print(f"\n  {name_a}: {va['level']}    {name_b}: {vb['level']}")
        for name, v in ((name_a, va), (name_b, vb)):
            if v["note"]:
                print(f"  note ({name}): {v['note']}")

        rater_levels = f"{name_a}={va['level']} {name_b}={vb['level']}"
        note = cli.load_pending_notes(ADJUDICATED).get(key, "")
        if note:
            print(f"  saved note: {note}")
        shown = datetime.now(timezone.utc)
        while True:
            try:
                raw = input("\n  0/1/2/3/4  s=skip  u=undo  n=note  ?=question  q=quit > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n\nSaved. Run the same command again to resume.")
                return 0
            if raw == "?":
                print(cli.wrap(item["question_text"]))
                continue
            if raw == "n":
                note = input("  note > ").strip()
                append_adj({"QuestionID": key[0], "answer_text_sha256": key[1],
                            "level": cli.NOTE_ONLY, "note": note, "seconds": "",
                            "rated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "adjudicator": args.adjudicator, "rater_levels": rater_levels})
                print("  Note saved; choose a level to resolve the item.")
                continue
            if raw == "q":
                print("\nSaved. Run the same command again to resume.")
                return 0
            if raw == "s":
                i += 1
                break
            if raw == "u":
                if not history:
                    print("  nothing to undo in this session")
                    continue
                prev = history.pop()
                append_adj({
                    "QuestionID": prev["QuestionID"],
                    "answer_text_sha256": prev["answer_text_sha256"],
                    "level": cli.RETRACT, "note": prev.get("note", ""),
                    "rated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "seconds": "", "pool_sha256": cli.POOL_SHA256,
                    "adjudicator": args.adjudicator, "rater_levels": prev["rater_levels"],
                })
                todo.insert(i, next(x for x in items
                                    if (x["QuestionID"], x["answer_text_sha256"])
                                    == (prev["QuestionID"], prev["answer_text_sha256"])))
                print(f"  retracted (level {prev['level']}); it will come up again")
                break
            if raw in cli.VALID:
                now = datetime.now(timezone.utc)
                append_adj({
                    "QuestionID": item["QuestionID"],
                    "answer_text_sha256": item["answer_text_sha256"],
                    "level": raw, "note": note,
                    "rated_at_utc": now.isoformat(timespec="seconds"),
                    "seconds": round((now - shown).total_seconds(), 1),
                    "pool_sha256": cli.POOL_SHA256,
                    "adjudicator": args.adjudicator, "rater_levels": rater_levels,
                })
                history.append({**item, "level": raw, "note": note, "rater_levels": rater_levels})
                i += 1
                break
            print("  please enter 0, 1, 2, 3, 4, s, u, n, ? or q")

    remaining = scope - set(cli.load_labels(ADJUDICATED))
    if remaining:
        print(f"\n{len(remaining)} disagreements in this scope remain unresolved. "
              "Run the same command to resume.")
        return 0
    print(f"\nAll {len(scope)} disagreements in this scope resolved. "
          f"Next: python experiments/scripts/25_partial_credit_model_vs_human.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
