"""Main model and proposals: bim.py propose/merge (bim.py setup --test, then in the bim env: python -m pytest scripts/tests)."""
import pathlib
import shutil
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bimlib.merge import merge, create  # noqa: E402
from bimlib.spec import load  # noqa: E402

EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "assets" / "example" / "model.yaml"


def _main(tmp_path):
    h = tmp_path / "model.yaml"
    shutil.copy(EXAMPLE, h)
    return h


def _proposal(h, name, text):
    assert create(h, name) == 0
    f = h.parent / "proposals" / f"{name}.yaml"
    f.write_text(f.read_text(encoding="utf-8") + text, encoding="utf-8")
    return f


def test_merge_gives_same_model_as_proposal(tmp_path):
    h = _main(tmp_path)
    f = _proposal(h, "rad", "vaegge:\n  - {id: S-IV2, usikkerhed: null, kilde: B}\n"
                           "  - {id: S-IV3, etage: S, type: IV-let, punkter: [[5000, 6000], [9700, 6000]]}\n"
                           "nedrives: [K-IV1]\n")
    expected = load(f)
    lines_before = h.read_text(encoding="utf-8").splitlines()
    assert merge(f) == 0
    after = load(h)
    expected.pop("_sti"), after.pop("_sti")
    assert after == expected
    # only the affected lines changed (+ one merge line in the header)
    lines_after = h.read_text(encoding="utf-8").splitlines()
    assert len(set(lines_after) - set(lines_before)) == 4
    assert not f.exists() and (tmp_path / "history" / "merge-log.md").exists()


def test_dry_run_writes_nothing(tmp_path):
    h = _main(tmp_path)
    before = h.read_bytes()
    f = _proposal(h, "p", "vaegge:\n  - {id: S-IV2, kilde: B}\n")
    assert merge(f, dry_run=True) == 0
    assert h.read_bytes() == before and f.exists()


def test_conflict_on_same_element_stops(tmp_path):
    h = _main(tmp_path)
    a = _proposal(h, "a", "vaegge:\n  - {id: S-IV2, usikkerhed: 5}\n")
    b = _proposal(h, "b", "vaegge:\n  - {id: S-IV2, usikkerhed: 9}\n")
    c = _proposal(h, "c", "vaegge:\n  - {id: S-IV1, kilde: B}\n")
    assert merge(a) == 0
    before = h.read_bytes()
    assert merge(b) == 1 and h.read_bytes() == before
    assert merge(c) == 0
    d = yaml.safe_load(h.read_text(encoding="utf-8"))
    iv = {e["id"]: e for e in d["vaegge"]}
    assert iv["S-IV2"]["usikkerhed"] == 5 and iv["S-IV1"]["kilde"] == "B"


def test_delete_with_dangling_reference_stops(tmp_path):
    h = _main(tmp_path)
    before = h.read_bytes()
    f = _proposal(h, "s", "slet: [S-IV2]\n")      # S-D2 sits in S-IV2
    assert merge(f) == 1 and h.read_bytes() == before


def test_new_section_and_edited_subsection_keep_proposal_comments(tmp_path):
    h = _main(tmp_path)
    f = _proposal(h, "vvs", "vvs:\n  # produktdata (kilde V)\n  produkter:\n    vvb: {navn: VVB 160, vaegt: 60}\n\n"
                           "    # pumpe – skøn\n    pumpe: {navn: P1}\n  valg: {ror: pex}\n")
    assert merge(f) == 0
    t = h.read_text(encoding="utf-8")
    assert "  # produktdata (kilde V)" in t and "    # pumpe – skøn" in t
    g = _proposal(h, "pumpe", "vvs:\n  produkter:\n    vvb: {navn: VVB 160, vaegt: 60}\n\n"
                             "    # pumpe – målt\n    pumpe: {navn: P2}\n")
    assert merge(g) == 0
    t = h.read_text(encoding="utf-8")
    assert "    # pumpe – målt" in t and "  valg: {ror: pex}" in t and "skøn" not in t
    assert yaml.safe_load(t)["vvs"]["produkter"]["pumpe"] == {"navn": "P2"}


def test_deep_mapping_changes_only_named_key(tmp_path):
    h = _main(tmp_path)
    f = _proposal(h, "vvs", "vvs:\n  produkter:\n    # VVB (kilde V)\n    vvb: {navn: VVB 160, vaegt: 60}\n"
                           "    pumpe: {navn: P1}\n  valg: {ror: pex}\n")
    assert merge(f) == 0
    g = _proposal(h, "vaegt", "vvs:\n  produkter:\n    vvb: {vaegt: 65}\n")
    assert merge(g) == 0
    t = h.read_text(encoding="utf-8")
    d = yaml.safe_load(t)["vvs"]
    assert d == {"produkter": {"vvb": {"navn": "VVB 160", "vaegt": 65}, "pumpe": {"navn": "P1"}}, "valg": {"ror": "pex"}}
    assert "    # VVB (kilde V)\n    vvb: {navn: VVB 160, vaegt: 65}" in t


def test_proposal_in_branch_dir_merges_into_main_case(tmp_path):
    # hovedsag/bim/model.yaml + branch case hovedsag--plumbing/bim/proposals (sibling dir, like a git branch)
    hb = tmp_path / "hovedsag" / "bim"
    hb.mkdir(parents=True)
    h = _main(hb)
    out = tmp_path / "hovedsag--plumbing" / "bim" / "proposals"
    assert create(h, "plumbing-1", out=out) == 0
    f = out / "plumbing-1.yaml"
    assert yaml.safe_load(f.read_text(encoding="utf-8"))["basis"] == "../../../hovedsag/bim/model.yaml"
    assert not (hb / "proposals" / "plumbing-1.yaml").exists()
    f.write_text(f.read_text(encoding="utf-8") + "vaegge:\n  - {id: S-IV2, kilde: B}\n", encoding="utf-8")
    expected = load(f)
    assert merge(f) == 0
    after = load(h)
    expected.pop("_sti"), after.pop("_sti")
    assert after == expected
    assert not f.exists() and (hb / "history" / "merge-log.md").exists()
