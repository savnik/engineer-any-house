"""Proposals and merging: trade agents contribute to shared case files without writing to them.

One writer per file: the shared case files (interfaces.md, risks.md, review-plan.md and the property card) are owned by
the project manager. A trade agent that wants to change or add rows writes a proposal:

    <case_dir>/proposals/<trade>-<no>__<target>.md        e.g. proposals/plumbing-03__interfaces.md

with the rows to change or add, in tables under the same ## heading as in the target file. Rows are matched on
the first column (ID). Same ID = the row is replaced, new ID = the row is appended to the end of the section's table.
Text outside the tables is ignored (the rationale belongs in the trade note).

The hook saves the target files as base (proposals/.base/<proposal>) when the trade call starts – what the trade agent reads –
and merges the proposal
when the deliverable is approved. Conflict: a row has changed in the target file since the base, and the proposal changes it
differently – then nothing is written, and the proposal stays for the project manager. If a value in the property card changes,
the old value is moved to "Erstattede oplysninger" (case-dir.md: corrections are never deleted). A column whose header starts
with "Ejer" is never changed by a proposal – the project manager decides who owns an interface (coordination.md).
"""
import os
import pathlib
import re
import shutil
import time

TARGETS = ("interfaces", "risks", "review-plan", "property-card")
PROPOSAL_RE = re.compile(r"^(?P<praefiks>[a-z0-9æøå-]+-[A-Za-z0-9._-]+)__(?P<maal>[a-z-]+)\.md$")
SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}")
GENERATED = ("<!-- GENERATED",)


def proposal_prefix(deliverable: str) -> str:
    """'<case>/plumbing/03' → 'plumbing-03' (the file name prefix for the deliverable's proposals)."""
    return deliverable.split("/", 1)[1].replace("/", "-") if "/" in deliverable else deliverable


def cells(line: str) -> list:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def norm(line) -> str:
    return "|".join(cells(line)) if line else ""


def is_row(line: str) -> bool:
    return line.lstrip().startswith("|")


def tables(lines: list) -> list:
    """[{section, header, start, end, rows: [(idx, id)]}] – start/end are indices of the data rows (end exclusive)."""
    out, section, i = [], "", 0
    while i < len(lines):
        l = lines[i]
        if re.match(r"^#{2,6}\s", l):
            section = l.lstrip("#").strip()
        if is_row(l) and i + 1 < len(lines) and is_row(lines[i + 1]) and SEP_RE.match(lines[i + 1]):
            t = {"section": section, "header": cells(l), "start": i + 2, "rows": []}
            j = i + 2
            while j < len(lines) and is_row(lines[j]):
                rid = cells(lines[j])[0]
                if rid:
                    t["rows"].append((j, rid))
                j += 1
            t["end"] = j
            out.append(t)
            i = j
            continue
        i += 1
    return out


HISTORY = "erstattede oplysninger"


def live(tabs: list) -> list:
    """Tables whose rows are matched on ID – the history table repeats the IDs and is append-only."""
    return [t for t in tabs if HISTORY not in t["section"].lower()]


def rows_by_id(lines: list) -> dict:
    return {rid: lines[idx] for t in live(tables(lines)) for idx, rid in t["rows"]}


def find_property_card(case_dir: pathlib.Path):
    for name in ("project-basis.md", "status.md"):
        f = case_dir / name
        if not f.is_file():
            continue
        m = re.search(r"\*\*Ejendom(?:skort)?:\*\*\s*`?([^\s`·]+\.md)", f.read_text(encoding="utf-8", errors="replace"))
        if m:
            p = pathlib.Path(m.group(1)).expanduser()
            for cand in ([p] if p.is_absolute() else [case_dir.parent.parent / p, case_dir / p, case_dir.parent / p]):
                if cand.is_file():
                    return cand.resolve()
    cards = sorted((case_dir.parent / "properties").glob("*.md"))
    return cards[0] if len(cards) == 1 else None


def target_for(proposal: pathlib.Path, case_dir: pathlib.Path):
    m = PROPOSAL_RE.match(proposal.name)
    if not m or m.group("maal") not in TARGETS:
        return None
    if m.group("maal") == "property-card":
        return find_property_card(case_dir)
    return case_dir / f"{m.group('maal')}.md"


def base_path(proposal: pathlib.Path) -> pathlib.Path:
    return proposal.parent / ".base" / proposal.name


def save_base_for_deliverable(case_dir: pathlib.Path, deliverable: str) -> None:
    """Called when the trade call starts: the target files the trade agent reads are the base for the conflict check.
    An existing base (from an earlier attempt) is kept – the oldest base never misses a conflict."""
    for t in TARGETS:
        save_base(case_dir / "proposals" / f"{proposal_prefix(deliverable)}__{t}.md", case_dir)


def clear_base(case_dir: pathlib.Path, deliverable: str) -> None:
    for b in (case_dir / "proposals" / ".base").glob(f"{proposal_prefix(deliverable)}__*.md"):
        b.unlink()


def save_base(proposal: pathlib.Path, case_dir: pathlib.Path) -> None:
    """Saves the target file as base unless one already exists (normally from the start of the trade call)."""
    b = base_path(proposal)
    target = target_for(proposal, case_dir)
    if b.exists() or not target or not target.is_file():
        return
    b.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(target, b)


class _Lock:
    def __init__(self, case_dir: pathlib.Path):
        self.path = case_dir / ".byg-merge.lock"

    def __enter__(self):
        self.fh = open(self.path, "a+")
        try:
            import fcntl
            fcntl.flock(self.fh, fcntl.LOCK_EX)
        except Exception:
            pass
        return self

    def __exit__(self, *_):
        self.fh.close()


def merge(proposal: pathlib.Path, case_dir: pathlib.Path, deliverable: str = "", dry_run: bool = False,
          force: bool = False) -> dict:
    """Merges the proposal into the target file. Returns {ok, besked, maal, aendret, nye, konflikter}."""
    res = {"ok": False, "maal": None, "aendret": [], "nye": [], "konflikter": []}
    target = target_for(proposal, case_dir)
    if target is None:
        res["besked"] = (f"{proposal.name}: ukendt mål – navnet skal være <fag>-<nr>__<mål>.md med mål "
                         f"{', '.join(TARGETS)} (ejendomskortet kræver '**Ejendom:** <sti>' i project-basis.md).")
        return res
    res["maal"] = str(target)
    if not target.is_file():
        res["besked"] = f"Målfilen {target} findes ikke – projektlederen opretter den, før forslag kan flettes."
        return res
    with _Lock(case_dir):
        text = target.read_text(encoding="utf-8")
        if any(g in text.split("\n", 1)[0] for g in GENERATED):
            res["besked"] = (f"{target.name} er genereret (fx fra BIM-hovedmodellen) og rettes ikke her – lav et "
                             "BIM-forslag og flet det med bim.py merge.")
            return res
        lines = text.split("\n")
        b = base_path(proposal)
        base = rows_by_id(b.read_text(encoding="utf-8").split("\n")) if b.is_file() else None
        p_lines = proposal.read_text(encoding="utf-8").split("\n")
        p_rows = [(t["section"], rid, p_lines[idx], len(t["header"])) for t in tables(p_lines) for idx, rid in t["rows"]]
        if not p_rows:
            res["besked"] = f"{proposal.name}: ingen tabelrækker (husk overskriftsrækken og |---|-linjen)."
            return res
        tabs = tables(lines)
        current_rows, errors = {}, []
        for t in live(tabs):
            for idx, rid in t["rows"]:
                if rid in current_rows:
                    errors.append(f"{rid}: står flere gange i {target.name} – projektlederen retter dubletten først")
                current_rows[rid] = (idx, t)
        replace, append = {}, {}
        for section, rid, line, ncol in p_rows:
            cur = current_rows.get(rid)
            cur_line = lines[cur[0]] if cur else None
            if base is not None and not force and norm(cur_line) != norm(base.get(rid)) and norm(line) != norm(cur_line):
                res["konflikter"].append(rid)
                continue
            if cur:
                owner = [i for i, h in enumerate(cur[1]["header"]) if h.strip("* ").lower().startswith("ejer")]
                if ncol != len(cur[1]["header"]):
                    errors.append(f"{rid}: {ncol} kolonner i forslaget, {len(cur[1]['header'])} i {target.name}")
                elif any(i < ncol and cells(line)[i] != cells(cur_line)[i] for i in owner):
                    errors.append(f"{rid}: ejeren ændres kun af projektlederen (meld afvigelsen i notatet)")
                elif norm(line) != norm(cur_line):
                    replace[cur[0]] = (rid, line, cur[1])
                continue
            t = next((t for t in tabs if t["section"].lower() == section.lower()), None)
            if t is None:
                errors.append(f"{rid}: afsnittet '{section}' har ingen tabel i {target.name}")
            elif ncol != len(t["header"]):
                errors.append(f"{rid}: {ncol} kolonner i forslaget, {len(t['header'])} i afsnittet '{section}'")
            else:
                append.setdefault(t["end"], []).append(line)
                res["nye"].append(rid)
        if res["konflikter"] or errors:
            parts = []
            if res["konflikter"]:
                parts.append(f"konflikt i {', '.join(res['konflikter'])} (ændret i {target.name}, siden forslaget blev skrevet)")
            parts += errors
            res["besked"] = f"{proposal.name} → {target.name}: intet flettet – " + "; ".join(parts)
            return res
        date = time.strftime("%Y-%m-%d")
        history = next((t for t in tabs if HISTORY in t["section"].lower()), None)
        for idx, (rid, line, t) in replace.items():
            res["aendret"].append(rid)
            vk = next((i for i, h in enumerate(t["header"]) if h.lower() == "værdi"), None)
            if history is not None and vk is not None:
                old, new = cells(lines[idx]), cells(line)
                if vk < len(old) and vk < len(new) and old[vk] != new[vk]:
                    row = ([rid, old[vk], date, f"forslag {deliverable or proposal.stem}"] + [""] * 10)[:len(history["header"])]
                    append.setdefault(history["end"], []).append("| " + " | ".join(row) + " |")
            lines[idx] = line
        for pos in sorted(append, reverse=True):
            lines[pos:pos] = append[pos]
        res["ok"] = True
        res["besked"] = (f"{proposal.name} → {target.name}: {len(res['aendret'])} ændret, {len(res['nye'])} nye"
                         + ("" if base is not None else " (uden basis – ingen konfliktkontrol)"))
        if dry_run:
            return res
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text("\n".join(lines), encoding="utf-8")
        os.replace(tmp, target)
        merged = proposal.parent / "merged"
        merged.mkdir(exist_ok=True)
        shutil.move(str(proposal), str(merged / proposal.name))
        if b.is_file():
            b.unlink()
        log = proposal.parent / "merge-log.md"
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(f"{date} · {deliverable or '-'} · {proposal.name} → {target.name} · ændret: {', '.join(res['aendret']) or '-'} · "
                     f"nye: {', '.join(res['nye']) or '-'}\n")
    return res


def deliverable_proposals(case_dir: pathlib.Path, deliverable: str) -> list:
    d = case_dir / "proposals"
    return sorted(d.glob(f"{proposal_prefix(deliverable)}__*.md")) if d.is_dir() else []
