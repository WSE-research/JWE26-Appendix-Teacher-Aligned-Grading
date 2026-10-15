"""Durable snapshots and single-writer guards for human annotation logs (stdlib only)."""
from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone
import uuid


@contextmanager
def session_lock(path: Path):
    """OS lock released even after process termination; never delete the lock inode."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    with lock.open("a+b") as fh:
        fh.seek(0, 2)
        if fh.tell() == 0:
            fh.write(b"0")
            fh.flush()
        fh.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(f"Another session owns {path.name}. Close it before continuing.") from exc
        try:
            yield
        finally:
            fh.seek(0)
            if os.name == "nt":
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fh, fcntl.LOCK_UN)


def tool_digest() -> str:
    root = Path(__file__).resolve().parent
    names = ("21_label_partial_credit.py", "24_adjudicate_partial_credit.py", "label_safety.py")
    return hashlib.sha256(b"".join((root / name).read_bytes() for name in names)).hexdigest()


def validate_bundle(bundle: Path, filename: str, pool_hash: str, scale: str) -> tuple[dict, bytes]:
    obj = json.loads(bundle.read_text(encoding="utf-8"))
    if (obj.get("format") != "jwe-label-backup-v1" or obj.get("filename") != filename
            or obj.get("pool_sha256") != pool_hash or obj.get("label_scale") != scale):
        raise ValueError("Backup identity, pool or schema does not match the requested log.")
    data = base64.b64decode(obj["csv_base64"], validate=True)
    if hashlib.sha256(data).hexdigest() != obj.get("csv_sha256"):
        raise ValueError("Backup checksum mismatch; do not restore this file.")
    if not isinstance(obj.get("tool_sha256"), str) or len(obj["tool_sha256"]) != 64:
        raise ValueError("Backup tool provenance missing.")
    return obj, data


def snapshot(path: Path, directory: Path, pool_hash: str, scale: str) -> Path | None:
    if not path.exists() or not path.stat().st_size:
        return None
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    # Never replace an earlier snapshot, including an earlier version of the same item.
    target = directory / (path.stem + "__" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                          + "__" + uuid.uuid4().hex + ".json")
    obj = dict(format="jwe-label-backup-v1", filename=path.name, csv_sha256=digest,
               pool_sha256=pool_hash, label_scale=scale, tool_sha256=tool_digest(),
               created_at_utc=datetime.now(timezone.utc).isoformat(),
               csv_base64=base64.b64encode(data).decode("ascii"))
    with target.open("x", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    _, saved = validate_bundle(target, path.name, pool_hash, scale)
    if saved != data:
        raise OSError("Backup read-back differs from the source log.")
    return target


def restore(bundle: Path, target: Path, pool_hash: str, scale: str, validator) -> None:
    """Validate before writing, and never replace even an empty existing destination."""
    _, data = validate_bundle(bundle, target.name, pool_hash, scale)
    with tempfile.TemporaryDirectory() as td:
        candidate = Path(td) / target.name
        candidate.write_bytes(data)
        validator(candidate)
    target.parent.mkdir(parents=True, exist_ok=True)
    with session_lock(target):
        with target.open("xb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        if target.read_bytes() != data:
            raise OSError("Restore read-back mismatch; preserve source backup.")


def prepare_backup(directory: Path) -> Path:
    """Check local recovery-copy storage before showing an item."""
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    probe = directory / (".write-probe-" + uuid.uuid4().hex)
    try:
        with probe.open("xb") as fh:
            fh.write(b"jwe-backup-probe")
            fh.flush()
            os.fsync(fh.fileno())
        if probe.read_bytes() != b"jwe-backup-probe":
            raise OSError("Backup destination read-back failed.")
    finally:
        if probe.exists():
            probe.unlink()
    return directory


def atomic_write(path: Path, text: str) -> None:
    """Publish one derived artifact without truncating the previous version on interruption."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as fh:
            temp = Path(fh.name)
            fh.write(text.encode("utf-8"))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()
