"""Main model and proposals: one source of truth (the main model); changes are made in a proposal file on top of it
and merged in only once the proposal is approved.

  forslag <hoved.yaml> <navn>   → <main dir>/forslag/<navn>.yaml with basis and basis_sha256
  flet <forslag.yaml> [--proev] → the proposal is merged into the main model; only the affected elements are rewritten,
                                  all other lines and comments are left untouched. The main model before and after
                                  is saved in historik/, the proposal is moved to historik/forslag/, and the merge
                                  is logged in historik/flettelog.md.

Safety: the result is read back and must give exactly the same model as the proposal gave on top of the main model
(what the review approved). If the main model has changed since the proposal was created, it is compared with the
version the proposal was based on (historik/), and the merge is stopped if the same elements changed in both places.
"""
import datetime
import hashlib
import os
import pathlib
import re
import shutil

import yaml

from .spec import PROPOSAL_FIELDS, ID_LISTS, SpecError, _merge, _read, load

LISTS = ID_LISTS


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _history_dir(main: pathlib.Path) -> pathlib.Path:
    return main.parent / "historik"


def _save_version(main: pathlib.Path) -> pathlib.Path:
    h = _history_dir(main)
    h.mkdir(exist_ok=True)
    target = h / f"{main.stem}.{_sha(main)[:12]}.yaml"
    if not target.exists():
        shutil.copy2(main, target)
    return target


def _flow(v) -> str:
    return yaml.safe_dump(v, default_flow_style=True, allow_unicode=True, sort_keys=False, width=10**9).removesuffix("\n...\n").strip()


# ------------------------------------------------------------------ text blocks in the main model
def _section(lines, name):
    """(start, end) of the lines under the top-level key `name:` (end exclusive), or None."""
    start = next((i for i, l in enumerate(lines) if re.match(rf"{re.escape(name)}:(\s|$)", l)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"[^\s#]", lines[i])), len(lines))
    return start, end


def _blocks(lines, start, end, is_list: bool, indent: int = 2):
    """Element blocks in a section: [(begin, stop)] in file order. An element is a line at indentation `indent`
    ('- ' or 'key:') plus continuation lines with deeper indentation. Blank lines and comments inside
    an element belong to it; blank lines and comments just before the next element do not."""
    pattern = re.compile(" " * indent + (r"- " if is_list else r"[^\s#-][^:]*:"))
    out, i = [], start + 1
    while i < end:
        if pattern.match(lines[i]):
            j = i + 1
            while j < end and (not lines[j].strip() or lines[j].lstrip().startswith("#")
                                or len(lines[j]) - len(lines[j].lstrip()) > indent):
                j += 1
            while j > i + 1 and (not lines[j - 1].strip() or lines[j - 1].lstrip().startswith("#")):
                j -= 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def _dict_text(lines, begin, stop, indent, g, n, replace, insert, path, ptext):
    """Rewrite only the changed keys in a mapping. A sub-mapping in block style is rewritten key by key.
    If the key appears in the proposal with the same value, the proposal's text is used verbatim – and if it has comments
    directly above it, they replace the main model's comments above the key. Otherwise the value is written on one line
    and the comments stay."""
    bl = _blocks(lines, begin, stop, False, indent)
    if len(bl) != len(g):
        raise SpecError([f"flet: kan ikke afgrænse nøglerne i '{'.'.join(path)}' ({len(bl)} blokke, {len(g)} nøgler)"
                        f" – skriv hver nøgle på sin egen linje med {indent} mellemrums indrykning"])

    def new_text(key, value):
        f = ptext.key([*path, key], value)
        if f:
            return f[0] and [" " * indent + x for x in f[0]], [" " * indent + x if x.strip() else x for x in f[1]]
        return None, [" " * indent + f"{key}: {_flow(value)}"]

    prev = begin + 1
    for key, (a, b) in zip(list(g), bl):
        lead = a
        while lead > prev and lines[lead - 1].lstrip().startswith("#"):
            lead -= 1
        prev = b
        if key not in n:
            replace[lead] = (b, [])
        elif n[key] != g[key]:
            block_form = re.match(rf"\s*{re.escape(str(key))}:\s*(#.*)?$", lines[a])
            child_indent = next((len(x) - len(x.lstrip()) for x in lines[a + 1:b] if x.strip() and not x.lstrip().startswith("#")),
                        None)
            if isinstance(g[key], dict) and isinstance(n[key], dict) and block_form and child_indent and child_indent > indent:
                _dict_text(lines, a, b, child_indent, g[key], n[key], replace, insert, [*path, key], ptext)
            else:
                comments, text = new_text(key, n[key])
                replace[lead if comments else a] = (b, (comments or []) + text)
    added = [x for x in n if x not in g]
    if added:
        last = bl[-1][1] if bl else begin + 1
        for x in added:
            comments, text = new_text(x, n[x])
            insert.setdefault(last, []).extend((comments or []) + text)


def _changes(old: dict, new: dict) -> set:
    """IDs (and top-level keys) that differ between two raw models."""
    out = set()
    for k in set(old) | set(new):
        if k in LISTS:
            g = {str(e.get("id")): e for e in old.get(k) or []}
            n = {str(e.get("id")): e for e in new.get(k) or []}
            out |= {i for i in set(g) | set(n) if g.get(i) != n.get(i)}
        elif isinstance(old.get(k), dict) and isinstance(new.get(k), dict):
            out |= {f"{k}.{f}" for f in set(old[k]) | set(new[k]) if old[k].get(f) != new[k].get(f)}
        elif old.get(k) != new.get(k):
            out.add(k)
    return out


def _touched(proposal: dict) -> set:
    out = {str(x) for x in (proposal.get("nedrives") or []) + (proposal.get("slet") or [])}
    for k, v in proposal.items():
        if k in PROPOSAL_FIELDS:
            continue
        if k in LISTS:
            out |= {str(e.get("id")) for e in v or []}
        elif isinstance(v, dict):
            out |= {f"{k}.{f}" for f in v}
        else:
            out.add(k)
    return out


class _ProposalText:
    """The proposal's own text for a section or an element – used verbatim (with comments) when it gives
    exactly the merged value; otherwise the element is written on one line."""

    def __init__(self, text):
        self.lines = (text or "").split("\n")

    def section(self, k, value):
        sec = _section(self.lines, k)
        if sec is None:
            return None
        chunk = self.lines[sec[0]:sec[1]]
        while chunk and (not chunk[-1].strip() or chunk[-1].startswith("#")):
            chunk.pop()
        return chunk if _parse_text(chunk) == {k: value} else None

    def key(self, path, value):
        """(leading comments, lines) for the key path[-1] in the mapping path[:-1] – only if they give `value`."""
        sec = _section(self.lines, path[0])
        if sec is None:
            return None
        begin, stop, indent = sec[0], sec[1], 2
        for i, k in enumerate(path[1:]):
            bl = [(a, b) for a, b in _blocks(self.lines, begin, stop, False, indent)
                  if re.match(rf"\s*{re.escape(str(k))}:(\s|$)", self.lines[a])]
            if not bl:
                return None
            a, b = bl[0]
            if i == len(path) - 2:
                chunk = [x[indent:] for x in self.lines[a:b]]
                if _parse_text(chunk) != {k: value}:
                    return None
                lead = a
                while lead > begin + 1 and self.lines[lead - 1].lstrip().startswith("#"):
                    lead -= 1
                return [x[indent:] for x in self.lines[lead:a]], chunk
            indent = next((len(x) - len(x.lstrip()) for x in self.lines[a + 1:b]
                        if x.strip() and not x.lstrip().startswith("#")), None)
            if indent is None:
                return None
            begin, stop = a, b
        return None

    def element(self, k, key, value, is_list):
        sec = _section(self.lines, k)
        if sec is None:
            return None
        for begin, stop in _blocks(self.lines, *sec, is_list):
            chunk = self.lines[begin:stop]
            v = _parse_text([f"{k}:"] + chunk)
            v = (v or {}).get(k)
            if is_list and isinstance(v, list) and len(v) == 1 and v[0] == value:
                return chunk
            if not is_list and isinstance(v, dict) and v == {key: value}:
                return chunk
        return None


def _parse_text(lines):
    try:
        return yaml.safe_load("\n".join(lines))
    except yaml.YAMLError:
        return None


def _write_text(text: str, old: dict, new: dict, proposal_text: str = None) -> str:
    """Rewrite only the changed elements in the main model's text."""
    ptext = _ProposalText(proposal_text)
    lines = text.split("\n")
    replace = {}   # line index (begin) -> (stop, new lines)
    insert = {}   # line index -> new lines (inserted before)
    new_sections = []
    for k in new:
        if k in PROPOSAL_FIELDS:
            continue
        g, n = old.get(k), new.get(k)
        if g == n:
            continue
        sec = _section(lines, k)
        is_list = k in LISTS
        if sec is None or not isinstance(n, (list, dict)) or (is_list and not isinstance(g, list)) \
                or (not is_list and not isinstance(g, dict)):
            if sec is not None:
                replace[sec[0]] = (sec[1], [f"{k}: {_flow(n)}" if not isinstance(n, (list, dict))
                                           else f"{k}:"] + _render(n, is_list))
            else:
                new_sections += ptext.section(k, n) or ([f"{k}:"] + _render(n, is_list) if isinstance(n, (list, dict))
                                                     else [f"{k}: {_flow(n)}"])
                new_sections.append("")
            continue
        if not is_list:
            _dict_text(lines, *sec, 2, g, n, replace, insert, [k], ptext)
            continue
        bl = _blocks(lines, *sec, is_list)
        keys = [str(e.get("id")) for e in g] if is_list else list(g)
        if len(bl) != len(keys):
            raise SpecError([f"flet: kan ikke afgrænse elementerne i '{k}' ({len(bl)} blokke, {len(keys)} elementer)"
                            " – skriv hvert element på sin egen linje ('  - {id: …}' / '  nøgle: …')"])
        gpos = dict(zip(keys, bl))
        nmap = {str(e.get("id")): e for e in n} if is_list else n
        gmap = {str(e.get("id")): e for e in g} if is_list else g
        for key, (begin, stop) in gpos.items():
            if key not in nmap:
                replace[begin] = (stop, [])
            elif nmap[key] != gmap[key]:
                replace[begin] = (stop, ptext.element(k, key, nmap[key], is_list)
                               or _render({key: nmap[key]} if not is_list else [nmap[key]], is_list))
        added = [x for x in nmap if x not in gpos]
        if added:
            last = bl[-1][1] if bl else sec[0] + 1
            for x in added:
                insert.setdefault(last, []).extend(ptext.element(k, x, nmap[x], is_list)
                                                     or _render([nmap[x]] if is_list else {x: nmap[x]}, is_list))
    out = []
    i = 0
    while i < len(lines):
        if i in insert:
            out += insert.pop(i)
        if i in replace:
            stop, added = replace.pop(i)
            out += added
            i = stop
            continue
        out.append(lines[i])
        i += 1
    for x in insert.values():
        out += x
    if new_sections:
        while out and out[-1] == "":
            out.pop()
        out += [""] + new_sections
    return "\n".join(out)


def _render(v, is_list: bool):
    if is_list:
        return [f"  - {_flow(e)}" for e in v]
    return [f"  {k}: {_flow(x)}" for k, x in v.items()]


# ------------------------------------------------------------------ commands
def create(main, name, note=None, out=None) -> int:
    main = pathlib.Path(main).resolve()
    if not main.exists():
        print(f"Hovedmodellen findes ikke: {main}")
        return 1
    if _read(main).get("basis"):
        print(f"{main.name} har selv en basis – et forslag skal bygge direkte på hovedmodellen")
        return 1
    # out: a branch case's own proposal dir (e.g. <main case>--vvs/bim/forslag); basis then points relatively to the main model
    out_dir = pathlib.Path(out).resolve() if out else main.parent / "forslag"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.yaml"
    if path.exists():
        print(f"Findes allerede: {path}")
        return 1
    _save_version(main)
    rel = pathlib.Path(os.path.relpath(main, out_dir))
    path.write_text(
        f"# Forslag '{name}' oven på hovedmodellen {main.name} ({datetime.date.today()}). Ret KUN her – aldrig i {main.name}.\n"
        + (f"# {note}\n" if note else "")
        + "# Skriv kun det, der ændres: elementer med samme id overskriver felterne (null fjerner et felt), nye id'er\n"
          "# tilføjes, 'nedrives: [id, …]' = renovering, 'slet: [id, …]' = modelrettelse. Byg/kontrollér forslaget med\n"
          f"#   bim.py byg {path.name}   ·   flet først ind efter godkendelse: bim.py flet {path.name}\n"
        f"basis: {rel.as_posix()}\n"
        f"basis_sha256: {_sha(main)}\n",
        encoding="utf-8")
    print(f"OPRETTET {path}")
    print(f"  basis {main.name} ({_sha(main)[:12]}); version gemt i historik/")
    return 0


def merge(proposal, dry_run=False, force=False, note=None) -> int:
    ppath = pathlib.Path(proposal).resolve()
    prop = _read(ppath)
    if not prop.get("basis"):
        print("Forslaget har ingen 'basis:' – det er ikke et forslag oven på en hovedmodel")
        return 1
    main = (ppath.parent / prop["basis"]).resolve()
    if not main.exists():
        print(f"Hovedmodellen findes ikke: {main}")
        return 1
    text = main.read_text(encoding="utf-8")
    old = _read(main)
    if old.get("basis"):
        print(f"{main.name} har selv en basis – flet kun ind i en hovedmodel")
        return 1

    # Has the main model changed since the proposal was created?
    sha_now = _sha(main)
    sha_prop = str(prop.get("basis_sha256") or "")
    conflicts = set()
    if sha_prop and sha_prop != sha_now:
        before = _history_dir(main) / f"{main.stem}.{sha_prop[:12]}.yaml"
        if not before.exists():
            print(f"STOP: {main.name} er ændret siden forslaget, og versionen {sha_prop[:12]} findes ikke i historik/.")
            if not force:
                return 1
        else:
            conflicts = _changes(_read(before), old) & _touched(prop)
            if conflicts:
                print(f"KONFLIKT: {main.name} er ændret siden forslaget, og de samme elementer er ændret begge steder:")
                for x in sorted(conflicts):
                    print("  - " + x)
                print("  Opdatér forslaget mod den nuværende hovedmodel (og kontrollér igen), eller brug --tving.")
                if not force:
                    return 1
            else:
                print(f"  Hovedmodellen er ændret siden forslaget ({sha_prop[:12]} → {sha_now[:12]}), men ikke i de samme elementer.")

    new = _merge(old, prop)
    errors = new.pop("_fejl", [])
    if errors:
        print(f"FLET-FEJL ({len(errors)}):")
        for x in errors:
            print("  - " + x)
        return 1
    new_text = _write_text(text, old, new, ppath.read_text(encoding="utf-8"))
    changed = _changes(old, new)
    if not changed:
        print("Forslaget ændrer intet i hovedmodellen.")
        return 0

    # Check 1: the text gives exactly the merged model. Check 2: it validates as a spec.
    if yaml.safe_load(new_text) != new:
        print("STOP: den omskrevne tekst giver ikke den forventede model (fejl i flet) – intet er skrevet.")
        return 1
    tmp = main.with_name(f".{main.stem}.flet-tjek.yaml")
    tmp.write_text(new_text, encoding="utf-8")
    try:
        load(tmp)
    except SpecError as e:
        print(f"SPEC-FEJL efter fletning ({len(e.errors)}) – intet er skrevet:")
        for x in e.errors[:40]:
            print("  - " + x)
        return 1
    finally:
        tmp.unlink(missing_ok=True)

    g_ids = {str(e.get("id")) for k in LISTS for e in old.get(k) or []}
    n_ids = {str(e.get("id")) for k in LISTS for e in new.get(k) or []}
    added, deleted = sorted(n_ids - g_ids), sorted(g_ids - n_ids)
    modified = sorted(changed - set(added) - set(deleted))
    print(f"{'PRØVE – intet skrevet' if dry_run else 'FLETTET'}: {ppath.name} → {main.name}")
    print(f"  rettet {len(modified)}: {', '.join(modified[:30])}{' …' if len(modified) > 30 else ''}")
    print(f"  nye {len(added)}: {', '.join(added[:30])}{' …' if len(added) > 30 else ''}")
    if deleted:
        print(f"  slettet {len(deleted)}: {', '.join(deleted)}")
    if dry_run:
        return 0

    date_str = datetime.date.today().isoformat()
    _save_version(main)
    lines = new_text.split("\n")
    pos = next((i for i, l in enumerate(lines) if not l.startswith("#")), 0)
    lines.insert(pos, f"# Flettet {date_str}: {ppath.name}{' – ' + note if note else ''} (rettet {len(modified)}, nye {len(added)}, slettet {len(deleted)}).")
    main.write_text("\n".join(lines), encoding="utf-8")
    after = _save_version(main)
    h = _history_dir(main)
    (h / "forslag").mkdir(exist_ok=True)
    archive = h / "forslag" / f"{ppath.stem}.{date_str}.yaml"
    n = 2
    while archive.exists():
        archive = h / "forslag" / f"{ppath.stem}.{date_str}-{n}.yaml"
        n += 1
    shutil.move(str(ppath), archive)
    log = h / "flettelog.md"
    if not log.exists():
        log.write_text(f"# Flettelog – {main.name}\n| Dato | Forslag | Før | Efter | Rettet | Nye | Slettet | Note |\n|---|---|---|---|---|---|---|---|\n",
                       encoding="utf-8")
    with log.open("a", encoding="utf-8") as f:
        f.write(f"| {date_str} | {ppath.name} | {sha_now[:12]} | {after.stem.split('.')[-1]} | {', '.join(modified)} | "
                f"{', '.join(added)} | {', '.join(deleted)} | {note or ''} |\n")
    print(f"  før/efter gemt i historik/, forslaget flyttet til {archive.relative_to(main.parent)}")
    if (yaml.safe_load(new_text).get("ejendomskort") or {}).get("fil"):
        from .property_card import generate
        generate(main)
    print(f"  næste: bim.py byg {main.name} og tjek – IFC'en er ikke bygget om")
    return 0
