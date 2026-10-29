"""Revisionsstyring af sagerne: byg-sager/ er et lokalt git-repo, som hooken committer til.

- Oprettes automatisk første gang (kun i en mappe, der hedder byg-sager, og aldrig inde i et plugin-repo).
- Pushes aldrig og har intet remote: sagerne er brugerdata (ARKITEKTUR.md, "Dataseparation").
- Commits: fagaflevering (kun fagets egne stier), kontroldom og fletning (kvalitet/ og forslag/ og målfilerne)
  og ved afslutning af hovedtrådens tur (alt i byg-sager/). Beskeden starter med leverance-ID'et.
- Slås fra med miljøvariablen BYG_GIT=0. Fejl blokerer aldrig – de logges af review_gate.py.
- Hvert commit har et samlet tidsbudget (BUDGET_SEK), så hooken altid når at svare inden for sin timeout. Dræbes
  en git-proces ved timeout, fjernes dens index.lock, så næste commit ikke fejler.
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
NAVN = ["-c", "user.name=byg-kontrol", "-c", "user.email=byg-kontrol@localhost", "-c", "commit.gpgsign=false"]
DIFF_MAKS = 200_000
BUDGET_SEK = 12


class GitFejl(RuntimeError):
    pass


def aktiv() -> bool:
    return os.environ.get("BYG_GIT", "1") != "0" and shutil.which("git") is not None


def rod_for(sti) -> pathlib.Path | None:
    """byg-sager-mappen, som stien ligger i (eller er)."""
    p = pathlib.Path(str(sti)).expanduser().resolve()
    for q in [p, *p.parents]:
        if q.name == "byg-sager":
            if any((r / ".claude-plugin").is_dir() for r in q.parents):
                return None  # sager må aldrig ligge i et plugin-repo
            return q
    return None


def _git(rod: pathlib.Path, *args, frist: float | None = None) -> subprocess.CompletedProcess:
    tid = max(0.5, (frist - time.monotonic()) if frist else BUDGET_SEK)
    try:
        return subprocess.run(["git", "-C", str(rod), *NAVN, *args], capture_output=True, text=True, timeout=tid)
    except subprocess.TimeoutExpired:
        # Vores egen git-proces er dræbt midt i arbejdet: dens index.lock ville ellers blokere alle senere commits.
        laas = rod / ".git" / "index.lock"
        if laas.exists() and args and args[0] in ("add", "commit"):
            laas.unlink()
        raise GitFejl(f"git {args[0]} nåede ikke at blive færdig inden for tidsbudgettet ({BUDGET_SEK} s)")


def _init(rod: pathlib.Path) -> None:
    if (rod / ".git").exists():
        return
    r = _git(rod, "init", "-q", "-b", "main")
    if r.returncode:
        raise GitFejl(f"git init: {r.stderr.strip()[:300]}")
    gi = rod / ".gitignore"
    if not gi.exists():
        gi.write_text(GITIGNORE, encoding="utf-8")


def commit(rod: pathlib.Path, besked: str, stier=None) -> str | None:
    """Committer stierne (relative til rod, pathspec-mønstre tilladt) eller alt. Returnerer HEAD-sha."""
    if not aktiv() or rod is None or not rod.is_dir():
        return None
    frist = time.monotonic() + BUDGET_SEK
    _init(rod)
    with open(rod / ".git" / "byg.laas", "a+") as laas:
        try:
            import fcntl
            fcntl.flock(laas, fcntl.LOCK_EX)
        except Exception:
            pass
        while (rod / ".git" / "index.lock").exists():  # en anden git-proces (fx brugerens egen) arbejder
            if time.monotonic() > frist - 2:
                raise GitFejl("index.lock holdes af en anden git-proces – commit springes over (næste hændelse tager det med)")
            time.sleep(0.2)
        # Kun hooken stager i dette repo, så det stagede er præcis det, der skal med i commit'et.
        if stier:
            for s in stier:  # ét mønster ad gangen: git afviser hele kaldet, hvis ét mønster ikke matcher
                r = _git(rod, "add", "-A", "--", f":(glob){s}", frist=frist)
                if r.returncode and "did not match any files" not in r.stderr:
                    raise GitFejl(f"git add {s}: {r.stderr.strip()[:300]}")
        else:
            r = _git(rod, "add", "-A", frist=frist)
            if r.returncode:
                raise GitFejl(f"git add: {r.stderr.strip()[:300]}")
        if _git(rod, "diff", "--cached", "--quiet", frist=frist).returncode != 0:
            r = _git(rod, "commit", "-q", "--no-verify", "-m", besked, frist=frist)
            if r.returncode:
                raise GitFejl(f"git commit: {(r.stderr or r.stdout).strip()[:300]}")
        r = _git(rod, "rev-parse", "HEAD", frist=frist)
        return r.stdout.strip() if r.returncode == 0 else None


def diff(rod: pathlib.Path, fra: str, til: str, stier) -> str:
    """Tekstdiff mellem to commits for stierne. Er den meget stor, gives kun oversigten."""
    if not aktiv() or not rod or not fra or not til or fra == til:
        return ""
    spec = ["--", *[f":(glob){s}" for s in stier]] if stier else []
    r = _git(rod, "diff", "--no-color", fra, til, *spec)
    if r.returncode != 0:
        return ""
    if len(r.stdout) > DIFF_MAKS:
        st = _git(rod, "diff", "--stat", fra, til, *spec)
        return f"# Diff for stor ({len(r.stdout)} tegn) – kun oversigt:\n{st.stdout}"
    return r.stdout
