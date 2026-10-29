#!/usr/bin/env python3
"""Measures the byg agents' token and time usage from Claude Code's local transcripts.

Usage:  python3 scripts/usage.py [project dir] [--siden YYYY-MM-DD] [--til YYYY-MM-DD]
        project dir: ~/.claude/projects/<encoded working dir> (default: the current working dir)
        --til is exclusive: before/after a release is compared with --til <date> and --siden <date>.

Shows:
- weighted usage per part (main thread, trade agents, review agents, others)
- the main thread's context per call (median and max)
- share of trade and review tokens in attempts 2–3 (retry)
- usage per agent type (runs, weighted total and per run)
- image and PDF reads and Edit rounds (API calls with only Edits) per run (median, p90 and runs over the protocol cap)
- page fetches repeated within a run and across runs, and status calls in the main thread
- answer length: final answer (the main thread's answer to the user, the subagents' report) and text between tool calls

Weighting relative to plain input tokens: cache read 0.1 ×, cache write 1.25 × and output 5 ×.
The script only reads local files and writes nothing. Output may contain case IDs; do not put it in the repo.
"""
import collections
import json
import os
import pathlib
import re
import statistics
import sys

WEIGHTS = {"input_tokens": 1.0, "cache_read_input_tokens": 0.1, "cache_creation_input_tokens": 1.25, "output_tokens": 5.0}
CONTEXT_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
ATTEMPT_RE = re.compile(r"Fors(?:ø|o)g:\s*(\d)")
DELIVERABLE_RE = re.compile(r"LEVERANCE:\s*(\S+)")
TARGET_TEXT = "hovedtråd og fagagenter under ca. 800, kontrolagenter under ca. 1.500"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp")
IMAGE_CAP, EDIT_CAP = 10, 5   # faelles/protokol.md: at most 10 images per call, about 5 Edit rounds


def read_transcript(path: pathlib.Path) -> dict:
    """Usage per API call (max per message id, since streaming repeats the message), first prompt and tool calls."""
    per_message, first_prompt, tools, start = {}, "", [], None
    text_len = {}                     # message id -> [chars, has tool call]; streaming splits a message over several lines
    tool_names = collections.defaultdict(list)   # message id -> tool names; parallel Edits in one message are one call
    final_answers, last_id = [], None  # last message id without tool calls before a user message or the end
    for line in path.open(encoding="utf-8"):
        try:
            o = json.loads(line)
        except Exception:
            continue
        start = start or o.get("timestamp")
        msg = o.get("message") or {}
        if not first_prompt and o.get("type") == "user":
            c = msg.get("content")
            first_prompt = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c or [] if isinstance(x, dict))
        if o.get("type") == "user" and not o.get("isMeta"):
            c = msg.get("content")
            if isinstance(c, str) or any(isinstance(x, dict) and x.get("type") == "text" for x in c or []):
                if last_id and text_len[last_id][0]:
                    final_answers.append(text_len[last_id][0])
                last_id = None
        if o.get("type") != "assistant":
            continue
        t = text_len.setdefault(msg.get("id"), [0, False])
        for c in msg.get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                tools.append((c.get("name"), c.get("input") or {}))
                tool_names[msg.get("id")].append(c.get("name"))
                t[1] = True
            elif isinstance(c, dict) and c.get("type") == "text":
                t[0] += len(c.get("text", ""))
        last_id = None if t[1] else msg.get("id")
        u = per_message.setdefault(msg.get("id"), collections.Counter())
        for k in WEIGHTS:
            u[k] = max(u[k], int((msg.get("usage") or {}).get(k) or 0))
    if last_id and text_len[last_id][0]:
        final_answers.append(text_len[last_id][0])
    between = sum(n for n, _ in text_len.values()) - sum(final_answers)   # all other text: interim answers along the way
    return {"calls": list(per_message.values()), "first_prompt": first_prompt, "tools": tools, "start": start or "",
            "final_answers": final_answers, "between_text": between,
            "edit_rounds": sum(1 for n in tool_names.values() if all(x in ("Edit", "MultiEdit") for x in n))}


def weighted(calls) -> float:
    return sum(u[k] * v for u in calls for k, v in WEIGHTS.items())


def reads(r) -> tuple:
    """Number of images and PDFs the run has read, and number of Edit rounds."""
    files = [str(i.get("file_path", "")).lower() for n, i in r["tools"] if n == "Read"]
    return (sum(f.endswith(IMAGE_EXTS) for f in files), sum(f.endswith(".pdf") for f in files),
            r["edit_rounds"])


def p90(xs) -> int:
    xs = sorted(xs)
    return xs[int(0.9 * (len(xs) - 1))] if xs else 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    since = sys.argv[sys.argv.index("--siden") + 1] if "--siden" in sys.argv else ""
    until = sys.argv[sys.argv.index("--til") + 1] if "--til" in sys.argv else ""
    args = [a for a in args if a not in (since, until)]
    folder = pathlib.Path(args[0]).expanduser() if args else \
        pathlib.Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", os.getcwd())
    if not folder.is_dir():
        print(f"Findes ikke: {folder}")
        return 1

    parts = collections.defaultdict(list)          # part -> list of runs
    main_context, status_calls, fetches, repeated_in_run = [], 0, collections.Counter(), 0
    retries = collections.defaultdict(lambda: [0.0, 0.0])  # part -> [attempt 1, attempts 2–3]
    deliverables = collections.defaultdict(float)
    for main_file in sorted(folder.glob("*.jsonl")):
        h = read_transcript(main_file)
        if not h["calls"] or h["start"][:10] < since or (until and h["start"][:10] >= until):
            continue
        subs = []
        for sub in sorted((folder / main_file.stem / "subagents").glob("*.jsonl")):
            meta = sub.with_suffix(".meta.json")
            agent_type = json.loads(meta.read_text(encoding="utf-8")).get("agentType", "") if meta.exists() else ""
            subs.append((agent_type, sub))
        if not any(agent_type.startswith("byg") for agent_type, _ in subs):
            continue  # only sessions where the byg agents were used
        parts["hovedtråd"].append(h)
        main_context += [sum(u[k] for k in CONTEXT_KEYS) for u in h["calls"]]
        status_calls += sum(1 for n, i in h["tools"] if n == "Bash" and "review_gate.py" in str(i.get("command"))
                          and " status" in str(i.get("command")))
        for agent_type, sub in subs:
            r = read_transcript(sub)
            if not r["calls"]:
                continue
            part = "kontrolagenter" if "-kontrol" in agent_type else "fagagenter" if agent_type.startswith("byg") else "øvrige"
            r["type"] = agent_type.split(":")[-1] or "ukendt"
            parts[part].append(r)
            urls = [i.get("url") for n, i in r["tools"] if n == "WebFetch"]
            repeated_in_run += len(urls) - len(set(urls))
            fetches.update(set(urls))
            if part in ("fagagenter", "kontrolagenter"):
                m = ATTEMPT_RE.search(r["first_prompt"])
                retries[part][1 if m and int(m.group(1)) > 1 else 0] += weighted(r["calls"])
                deliverable = DELIVERABLE_RE.search(r["first_prompt"])
                if deliverable:
                    deliverables[deliverable.group(1)] += weighted(r["calls"])

    total = sum(weighted(r["calls"]) for runs in parts.values() for r in runs)
    if not total:
        print("Ingen sessioner i perioden.")
        return 0
    print(f"Mappe: {folder}" + (f" · siden {since}" if since else "") + (f" · før {until}" if until else ""))
    print(f"Sessioner: {len(parts['hovedtråd'])} · vægtet forbrug i alt: {total / 1e6:.1f}M\n")
    print(f"{'Del':16} {'kørsler':>7} {'vægtet':>9} {'andel':>6}")
    for part in ("hovedtråd", "fagagenter", "kontrolagenter", "øvrige"):
        v = sum(weighted(r["calls"]) for r in parts[part])
        print(f"{part:16} {len(parts[part]):7} {v / 1e6:8.1f}M {100 * v / total:5.0f} %")
    if main_context:
        print(f"\nHovedtråd: median-kontekst {statistics.median(main_context) / 1e3:.0f}k · maks. "
              f"{max(main_context) / 1e3:.0f}k · kald over 200k: {sum(n > 200_000 for n in main_context)} af "
              f"{len(main_context)} · statuskald: {status_calls}")
    for part, (f1, f23) in retries.items():
        if f1 + f23:
            print(f"{part.capitalize()}: {100 * f23 / (f1 + f23):.0f} % af forbruget i forsøg 2–3 (retur)")
    if fetches:
        n = sum(fetches.values()) + repeated_in_run
        across = sum(fetches.values()) - len(fetches)
        print(f"Sidehentninger: {n}, heraf gentaget i samme kørsel: {repeated_in_run} · "
              f"på tværs af kørsler: {across} ({100 * across / n:.0f} %)")

    types = collections.defaultdict(list)
    for part in ("fagagenter", "kontrolagenter", "øvrige"):
        for r in parts[part]:
            types[r["type"]].append(r)
    print(f"\n{'Agenttype':22} {'kørsler':>7} {'vægtet':>8} {'andel':>6} {'pr. kørsel':>10}")
    for agent_type, rs in sorted(types.items(), key=lambda x: -sum(weighted(r["calls"]) for r in x[1])):
        v = sum(weighted(r["calls"]) for r in rs)
        print(f"{agent_type:22} {len(rs):7} {v / 1e6:7.1f}M {100 * v / total:5.0f} % {v / len(rs) / 1e6:9.2f}M")

    print(f"\nLæsninger pr. kørsel (median / p90 / kørsler over loftet; loft: {IMAGE_CAP} billeder, "
          f"ca. {EDIT_CAP} Edit-runder)")
    print(f"{'Del':16} {'billeder':>14} {'PDF':>9} {'Edit-runder':>14}")
    for part in ("fagagenter", "kontrolagenter", "øvrige"):
        if parts[part]:
            b, pdf, e = zip(*(reads(r) for r in parts[part]))
            print(f"{part:16} {statistics.median(b):3.0f} / {p90(b):3} / {sum(x > IMAGE_CAP for x in b):2} "
                  f"{statistics.median(pdf):3.0f} / {p90(pdf):3} "
                  f"{statistics.median(e):3.0f} / {p90(e):3} / {sum(x > EDIT_CAP for x in e):2}")
    print(f"\nSvarlængde i tegn (mål for median: {TARGET_TEXT})")
    print(f"{'Del':16} {'slutsvar':>8} {'median':>7} {'p90':>7} {'mellemtekst/kørsel':>19}")
    for part in ("hovedtråd", "fagagenter", "kontrolagenter", "øvrige"):
        answers = sorted(n for r in parts[part] for n in r["final_answers"])
        if answers:
            between = sum(r["between_text"] for r in parts[part]) / len(parts[part])
            print(f"{part:16} {len(answers):8} {statistics.median(answers):7.0f} {answers[int(0.9 * (len(answers) - 1))]:7} {between:19.0f}")
    if deliverables:
        print(f"Leverancer: {len(deliverables)} · median vægtet forbrug pr. leverance: "
              f"{statistics.median(deliverables.values()) / 1e6:.2f}M")
    return 0


if __name__ == "__main__":
    sys.exit(main())
