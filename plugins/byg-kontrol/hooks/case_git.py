"""Version control of the cases: byg-sager/ is a local git repo that the hook commits to.

- Created automatically the first time (only in a folder named byg-sager, and never inside a plugin repo).
- Never pushed and has no remote: the cases are user data (ARKITEKTUR.md, "Dataseparation").
- Commits: trade handoff (only the trade's own paths), review verdict and merge (kvalitet/, forslag/ and the
  target files) and at the end of the main thread's turn (everything in byg-sager/). The message starts with the deliverable ID.
- Disabled with the environment variable BYG_GIT=0. Errors never block – review_gate.py logs them.
- Every commit has an overall time budget (BUDGET_SEC), so the hook always answers within its timeout. If a git
  process is killed on timeout, its index.lock is removed so the next commit does not fail.
"""
import os
import pathlib
import shutil
import subprocess
import time

GITIGNORE = """# byg-kontrol: genererede filer og låse (kan genskabes fra modellerne)
*.laas
*.tmp
.basis/
*.ifc
**/bim/ud/
**/bim/**/*.png
**/fem/**/*.png
**/fem/**/*.html
**/kvalitet/**/*.png
"""
GIT_IDENTITY = ["-c", "user.name=byg-kontrol", "-c", "user.email=byg-kontrol@localhost", "-c", "commit.gpgsign=false"]
DIFF_MAX = 200_000
BUDGET_SEC = 12


class GitError(RuntimeError):
    pass


def active() -> bool:
    return os.environ.get("BYG_GIT", "1") != "0" and shutil.which("git") is not None


def root_for(path) -> pathlib.Path | None:
    """The byg-sager folder that the path lies in (or is)."""
    p = pathlib.Path(str(path)).expanduser().resolve()
    for q in [p, *p.parents]:
        if q.name == "byg-sager":
            if any((r / ".claude-plugin").is_dir() for r in q.parents):
                return None  # cases must never live inside a plugin repo
            return q
    return None


def _git(root: pathlib.Path, *args, deadline: float | None = None) -> subprocess.CompletedProcess:
    timeout = max(0.5, (deadline - time.monotonic()) if deadline else BUDGET_SEC)
    try:
        return subprocess.run(["git", "-C", str(root), *GIT_IDENTITY, *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        # Our own git process was killed mid-work: its index.lock would otherwise block every later commit.
        lock = root / ".git" / "index.lock"
        if lock.exists() and args and args[0] in ("add", "commit"):
            lock.unlink()
        raise GitError(f"git {args[0]} nåede ikke at blive færdig inden for tidsbudgettet ({BUDGET_SEC} s)")


def _init(root: pathlib.Path) -> None:
    if (root / ".git").exists():
        return
    r = _git(root, "init", "-q", "-b", "main")
    if r.returncode:
        raise GitError(f"git init: {r.stderr.strip()[:300]}")
    gi = root / ".gitignore"
    if not gi.exists():
        gi.write_text(GITIGNORE, encoding="utf-8")


def commit(root: pathlib.Path, message: str, paths=None) -> str | None:
    """Commits the paths (relative to root, pathspec patterns allowed) or everything. Returns the HEAD sha."""
    if not active() or root is None or not root.is_dir():
        return None
    deadline = time.monotonic() + BUDGET_SEC
    _init(root)
    with open(root / ".git" / "byg.laas", "a+") as lock:
        try:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
        except Exception:
            pass
        while (root / ".git" / "index.lock").exists():  # another git process (e.g. the user's own) is working
            if time.monotonic() > deadline - 2:
                raise GitError("index.lock holdes af en anden git-proces – commit springes over (næste hændelse tager det med)")
            time.sleep(0.2)
        # Only the hook stages in this repo, so what is staged is exactly what belongs in the commit.
        if paths:
            for s in paths:  # one pattern at a time: git rejects the whole call if one pattern does not match
                r = _git(root, "add", "-A", "--", f":(glob){s}", deadline=deadline)
                if r.returncode and "did not match any files" not in r.stderr:
                    raise GitError(f"git add {s}: {r.stderr.strip()[:300]}")
        else:
            r = _git(root, "add", "-A", deadline=deadline)
            if r.returncode:
                raise GitError(f"git add: {r.stderr.strip()[:300]}")
        if _git(root, "diff", "--cached", "--quiet", deadline=deadline).returncode != 0:
            r = _git(root, "commit", "-q", "--no-verify", "-m", message, deadline=deadline)
            if r.returncode:
                raise GitError(f"git commit: {(r.stderr or r.stdout).strip()[:300]}")
        r = _git(root, "rev-parse", "HEAD", deadline=deadline)
        return r.stdout.strip() if r.returncode == 0 else None


def diff(root: pathlib.Path, start: str, end: str, paths) -> str:
    """Text diff between two commits for the paths. If it is very large, only the summary is given."""
    if not active() or not root or not start or not end or start == end:
        return ""
    spec = ["--", *[f":(glob){s}" for s in paths]] if paths else []
    r = _git(root, "diff", "--no-color", start, end, *spec)
    if r.returncode != 0:
        return ""
    if len(r.stdout) > DIFF_MAX:
        st = _git(root, "diff", "--stat", start, end, *spec)
        return f"# Diff for stor ({len(r.stdout)} tegn) – kun oversigt:\n{st.stdout}"
    return r.stdout
