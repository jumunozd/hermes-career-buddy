"""Encrypted daily backup of the private zone and Baserow (database + uploaded files). No LLM.

One archive per run: `hcb-backup-<YYYYmmdd-HHMM>.tar.enc` (AES-256, key in ~/.hermes/career-buddy/secrets/
backup.key, never in the project or in git). Inside: private.tar.gz, baserow-db.dump (pg_dump -Fc) and
baserow-media.tar. Each run is verified (decrypt + list + pg_restore -l) before old archives are pruned.
Keeps the newest 7 plus one per week for 4 weeks. Optional extra copies (an external drive, iCloud Drive)
from config `backup.extra_destinations`; the archive is already encrypted before it leaves this folder.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from . import state
from .util import ROOT, config

HOME = Path.home() / ".hermes" / "career-buddy"
KEY = HOME / "secrets" / "backup.key"


def _cfg() -> dict:
    return config().get("backup") or {}


def _dest() -> Path:
    d = Path(os.path.expanduser(_cfg().get("destination", str(HOME / "backups" / "daily"))))
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    return d


def _docker() -> str:
    c = os.path.expanduser(_cfg().get("docker") or "")
    return c if c and Path(c).exists() else (shutil.which("docker") or "/usr/bin/docker")   # Mac Docker Desktop or Linux


def ensure_key() -> Path:
    if not KEY.exists():
        KEY.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(KEY.parent, 0o700)
        KEY.write_text(secrets.token_urlsafe(48))
        os.chmod(KEY, 0o600)
    return KEY


def _run(cmd: list[str], out_path: Path | None = None, **kw) -> None:
    if out_path:
        with out_path.open("wb") as fh:
            p = subprocess.run(cmd, stdout=fh, stderr=subprocess.PIPE, timeout=1800, **kw)
    else:
        p = subprocess.run(cmd, capture_output=True, timeout=1800, **kw)
    if p.returncode != 0:
        raise RuntimeError(f"{Path(cmd[0]).name} failed (exit {p.returncode}): {p.stderr.decode(errors='ignore')[-300:]}")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(now: datetime | None = None, include_baserow: bool = True) -> dict:
    now = now or datetime.now()
    key = ensure_key()
    dest = _dest()
    name = f"hcb-backup-{now:%Y%m%d-%H%M}"
    with tempfile.TemporaryDirectory(prefix="hcb-backup-") as tmp:
        tmp = Path(tmp)
        with tarfile.open(tmp / "private.tar.gz", "w:gz") as tf:
            tf.add(ROOT / "private", arcname="private",
                   filter=lambda ti: None if ti.name.endswith((".DS_Store", "__pycache__")) else ti)
        parts = ["private.tar.gz"]
        if include_baserow:
            _run([_docker(), "exec", "baserow", "sh", "-c", 'cd /tmp && su postgres -c "pg_dump -Fc baserow"'],
                 tmp / "baserow-db.dump")
            _run([_docker(), "exec", "baserow", "tar", "-C", "/baserow/data", "-cf", "-", "media"],
                 tmp / "baserow-media.tar")
            parts += ["baserow-db.dump", "baserow-media.tar"]
        with tarfile.open(tmp / f"{name}.tar", "w") as tf:
            for p in parts:
                tf.add(tmp / p, arcname=p)
        out = dest / f"{name}.tar.enc"
        _run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-in", str(tmp / f"{name}.tar"),
              "-out", str(out), "-pass", f"file:{key}"])
        os.chmod(out, 0o600)
    check = verify(out, include_baserow)
    copies = []
    for extra in _cfg().get("extra_destinations") or []:
        d = Path(os.path.expanduser(extra))
        if d.exists():
            target = d / "hermes-career-buddy-backups"
            target.mkdir(exist_ok=True)
            shutil.copy2(out, target / out.name)
            copies.append(str(target / out.name))
            prune(target)
    removed = prune(dest)
    res = {"archive": str(out), "bytes": out.stat().st_size, "sha256": _sha(out), "parts": parts,
           "verified": check, "copies": copies, "pruned": removed}
    state.event("backup", archive=out.name, bytes=res["bytes"], verified=check["ok"], copies=len(copies))
    if not check["ok"]:
        raise RuntimeError(f"backup verification failed: {check}")
    return res


def verify(archive: Path, include_baserow: bool = True) -> dict:
    """Decrypt to a temp dir, list the parts, check the private tar and the DB dump table of contents."""
    key = ensure_key()
    with tempfile.TemporaryDirectory(prefix="hcb-verify-") as tmp:
        tmp = Path(tmp)
        plain = tmp / "b.tar"
        _run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-in", str(archive), "-out", str(plain),
              "-pass", f"file:{key}"])
        with tarfile.open(plain) as tf:
            names = tf.getnames()
            tf.extractall(tmp, filter="data")
        with tarfile.open(tmp / "private.tar.gz") as tf:
            n_private = len(tf.getnames())
        out = {"parts": names, "private_files": n_private}
        if include_baserow:
            p = subprocess.run([_docker(), "exec", "-i", "baserow", "sh", "-c",
                                'cat > /tmp/v.dump && su postgres -c "pg_restore -l /tmp/v.dump" | grep -c "TABLE DATA"; rm -f /tmp/v.dump'],
                               stdin=(tmp / "baserow-db.dump").open("rb"), capture_output=True, timeout=600)
            out["db_table_data_entries"] = int((p.stdout or b"0").strip() or 0)
            with tarfile.open(tmp / "baserow-media.tar") as tf:
                out["media_files"] = sum(1 for m in tf.getmembers() if m.isfile())
        out["ok"] = n_private > 0 and (not include_baserow or (out["db_table_data_entries"] > 0 and out["media_files"] > 0))
        return out


def prune(folder: Path, keep_daily: int = 7, keep_weekly: int = 4) -> list[str]:
    files = sorted(folder.glob("hcb-backup-*.tar.enc"), reverse=True)
    keep = set(files[:keep_daily])
    weeks = {}
    for f in files:
        try:
            dt = datetime.strptime(f.name[11:24], "%Y%m%d-%H%M")
        except ValueError:
            continue
        weeks.setdefault(dt.isocalendar()[:2], f)
    keep |= set(list(weeks.values())[:keep_weekly])
    removed = []
    for f in files:
        if f not in keep:
            f.unlink()
            removed.append(f.name)
    return removed
